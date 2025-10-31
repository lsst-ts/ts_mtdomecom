# This file is part of ts_mtdomecom.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import contextlib
import logging
import math
import pathlib
import types
import typing
import unittest
from unittest.mock import patch

import pytest
import yaml
from lsst.ts import mtdomecom, utils
from lsst.ts.xml.enums.MTDome import (
    MotionState,
    OnOff,
    OpenClose,
    OperationalMode,
    PowerManagementMode,
    SubSystemId,
)


CONFIG_DIR = pathlib.Path(__file__).parent / "data"


class MTDomeComTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.command_id = -1
        self.data: dict | None = None
        self.log = logging.getLogger("MTDomeComTestCase")

    @contextlib.asynccontextmanager
    async def create_mtdomecom(self) -> typing.AsyncGenerator[None, None]:
        async with mtdomecom.MTDomeCom(
            log=self.log,
            config=types.SimpleNamespace(),
            config_dir=CONFIG_DIR,
            simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
        ) as self.mtdomecom_com:
            assert len(self.mtdomecom_com.telemetry_callbacks) == 0

            with open(CONFIG_DIR / "louvers_enabled.yaml") as config_file:  # type: ignore
                config_data = yaml.safe_load(config_file)
                assert len(config_data["louvers_enabled"]) == len(self.mtdomecom_com.louvers_enabled)

            yield

    async def asyncTearDown(self) -> None:
        assert await self.mtdomecom_com.has_non_status_command() is False

    async def test_update_status_of_non_status_command(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.update_status_of_non_status_command(True)
            assert await self.mtdomecom_com.has_non_status_command() is True

            await self.mtdomecom_com.update_status_of_non_status_command(False)
            assert await self.mtdomecom_com.has_non_status_command() is False

    async def test_move_az(self) -> None:
        async with self.create_mtdomecom():
            exp_position = 329.0
            exp_velocity = 0.5
            await self.mtdomecom_com.move_az(position=exp_position, velocity=exp_velocity)
            assert math.isclose(
                self.mtdomecom_com.mock_ctrl.amcs.position_commanded,
                math.radians(
                    utils.angle_wrap_nonnegative(exp_position + mtdomecom.DOME_AZIMUTH_OFFSET).degree
                ),
            )
            assert math.isclose(
                self.mtdomecom_com.mock_ctrl.amcs.crawl_velocity,
                math.radians(exp_velocity),
            )

    async def test_move_el(self) -> None:
        async with self.create_mtdomecom():
            exp_position = 29.0
            await self.mtdomecom_com.move_el(position=exp_position)
            assert math.isclose(
                self.mtdomecom_com.mock_ctrl.lwscs.position_commanded,
                math.radians(exp_position),
            )

    async def test_stop_az(self) -> None:
        async with self.create_mtdomecom():
            assert self.mtdomecom_com.mock_ctrl.amcs.start_state != MotionState.GO_STATIONARY.name
            assert self.mtdomecom_com.mock_ctrl.amcs.target_state != MotionState.STOPPED.name
            await self.mtdomecom_com.stop_az(engage_brakes=False)
            assert self.mtdomecom_com.mock_ctrl.amcs.start_state != MotionState.GO_STATIONARY.name
            assert self.mtdomecom_com.mock_ctrl.amcs.target_state == MotionState.STOPPED.name
            await self.mtdomecom_com.stop_az(engage_brakes=True)
            assert self.mtdomecom_com.mock_ctrl.amcs.start_state == MotionState.GO_STATIONARY.name
            assert self.mtdomecom_com.mock_ctrl.amcs.target_state == MotionState.STOPPED.name

    async def test_stop_el(self) -> None:
        async with self.create_mtdomecom():
            assert self.mtdomecom_com.mock_ctrl.lwscs.target_state != MotionState.STOPPED.name
            await self.mtdomecom_com.stop_el(engage_brakes=False)
            assert self.mtdomecom_com.mock_ctrl.lwscs.target_state == MotionState.STOPPED.name
            await self.mtdomecom_com.stop_el(engage_brakes=True)
            assert (
                self.mtdomecom_com.mock_ctrl.lwscs.target_state
                == mtdomecom.InternalMotionState.STATIONARY.name
            )

    async def test_stop_louvers(self) -> None:
        async with self.create_mtdomecom():
            for i in range(mtdomecom.LCS_NUM_LOUVERS):
                assert self.mtdomecom_com.mock_ctrl.lcs.target_state[i] != MotionState.STOPPED.name
            await self.mtdomecom_com.stop_louvers(engage_brakes=False)
            for i in range(mtdomecom.LCS_NUM_LOUVERS):
                assert self.mtdomecom_com.mock_ctrl.lcs.target_state[i] == MotionState.STOPPED.name
            await self.mtdomecom_com.stop_louvers(engage_brakes=True)
            for i in range(mtdomecom.LCS_NUM_LOUVERS):
                assert (
                    self.mtdomecom_com.mock_ctrl.lcs.target_state[i]
                    == mtdomecom.InternalMotionState.STATIONARY.name
                )

    async def test_crawl_az(self) -> None:
        async with self.create_mtdomecom():
            exp_velocity = 0.5
            await self.mtdomecom_com.crawl_az(velocity=exp_velocity)
            assert math.isclose(
                self.mtdomecom_com.mock_ctrl.amcs.crawl_velocity,
                math.radians(exp_velocity),
            )

    async def test_crawl_el(self) -> None:
        async with self.create_mtdomecom():
            exp_velocity = 0.5
            await self.mtdomecom_com.crawl_el(velocity=exp_velocity)
            assert math.isclose(
                self.mtdomecom_com.mock_ctrl.lwscs.crawl_velocity,
                math.radians(exp_velocity),
            )

    async def test_set_louvers(self) -> None:
        async with self.create_mtdomecom():
            exp_position = [10.0, 12.0] + [math.nan] * (mtdomecom.LCS_NUM_LOUVERS - 2)
            await self.mtdomecom_com.set_louvers(position=exp_position)
            for i in range(2):
                assert math.isclose(
                    self.mtdomecom_com.mock_ctrl.lcs.position_commanded[i],
                    exp_position[i],
                )
            for i in range(mtdomecom.LCS_NUM_LOUVERS - 2):
                assert math.isclose(self.mtdomecom_com.mock_ctrl.lcs.position_commanded[i + 2], 0.0)

    async def test_close_louvers(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.lcs.position_actual = [10.0, 12.0] + [0.0] * (
                mtdomecom.LCS_NUM_LOUVERS - 2
            )
            for i in range(mtdomecom.LCS_NUM_LOUVERS):
                assert (
                    self.mtdomecom_com.mock_ctrl.lcs.start_state[i]
                    == mtdomecom.InternalMotionState.STATIONARY.name
                )
            await self.mtdomecom_com.close_louvers()
            for i in range(2):
                assert self.mtdomecom_com.mock_ctrl.lcs.start_state[i] == MotionState.CLOSING.name
            for i in range(mtdomecom.LCS_NUM_LOUVERS - 2):
                assert (
                    self.mtdomecom_com.mock_ctrl.lcs.start_state[i + 2]
                    == mtdomecom.InternalMotionState.STATIONARY.name
                )

    async def test_open_shutter(self) -> None:
        async with self.create_mtdomecom():
            for i in range(mtdomecom.APSCS_NUM_SHUTTERS):
                assert self.mtdomecom_com.mock_ctrl.apscs.target_state[i] == MotionState.CLOSED.name
            await self.mtdomecom_com.open_shutter()
            assert (
                self.mtdomecom_com.mock_ctrl.apscs.target_state
                == [MotionState.OPEN.name] * mtdomecom.APSCS_NUM_SHUTTERS
            )

    async def test_close_shutter(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.apscs.position_actual = [100.0] * mtdomecom.APSCS_NUM_SHUTTERS
            await self.mtdomecom_com.close_shutter()
            assert (
                self.mtdomecom_com.mock_ctrl.apscs.target_state
                == [MotionState.CLOSED.name] * mtdomecom.APSCS_NUM_SHUTTERS
            )

    async def test_park(self) -> None:
        async with self.create_mtdomecom():
            assert self.mtdomecom_com.mock_ctrl.amcs.start_state == MotionState.PARKED.name
            await self.mtdomecom_com.park()
            assert self.mtdomecom_com.mock_ctrl.amcs.start_state == MotionState.PARKING.name

    async def test_set_temperature(self) -> None:
        async with self.create_mtdomecom():
            assert math.isclose(self.mtdomecom_com.mock_ctrl.thcs.drive_temperature[0], 0.0)
            await self.mtdomecom_com.set_temperature(10.0)
            assert math.isclose(self.mtdomecom_com.mock_ctrl.thcs.drive_temperature[0], 10.0)

    async def test_exit_fault(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.amcs.drives_in_error_state[0] = True
            self.mtdomecom_com.mock_ctrl.amcs.current_state = MotionState.ERROR.name
            await self.mtdomecom_com.exit_fault(sub_system_ids=SubSystemId.AMCS)
            assert not self.mtdomecom_com.mock_ctrl.amcs.drives_in_error_state[0]
            assert (
                self.mtdomecom_com.mock_ctrl.amcs.current_state
                == mtdomecom.InternalMotionState.STATIONARY.name
            )

    async def test_set_operational_mode(self) -> None:
        async with self.create_mtdomecom():
            assert self.mtdomecom_com.mock_ctrl.amcs.operational_mode == OperationalMode.NORMAL
            await self.mtdomecom_com.set_operational_mode(
                OperationalMode.DEGRADED, sub_system_ids=SubSystemId.AMCS
            )
            assert self.mtdomecom_com.mock_ctrl.amcs.operational_mode == OperationalMode.DEGRADED

    async def test_reset_drives_az(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.amcs.drives_in_error_state[0] = True
            await self.mtdomecom_com.reset_drives_az(reset=[1, 1, 1, 1, 1])
            assert not self.mtdomecom_com.mock_ctrl.amcs.drives_in_error_state[0]

    async def test_reset_drives_shutter(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.apscs.drives_in_error_state[0][0] = True
            await self.mtdomecom_com.reset_drives_shutter(reset=[1, 1, 1, 1])
            assert not self.mtdomecom_com.mock_ctrl.apscs.drives_in_error_state[0][0]

    async def test_set_zero_az(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.amcs.start_position = 100.0
            await self.mtdomecom_com.set_zero_az()
            assert math.isclose(self.mtdomecom_com.mock_ctrl.amcs.start_position, 0.0)

    async def test_home(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.mock_ctrl.apscs.position_actual = [100.0] * mtdomecom.APSCS_NUM_SHUTTERS
            await self.mtdomecom_com.home(
                sub_system_ids=SubSystemId.APSCS,
                direction=[OpenClose.CLOSE, OpenClose.CLOSE],
            )
            assert (
                self.mtdomecom_com.mock_ctrl.apscs.target_state
                == [MotionState.CLOSED.name] * mtdomecom.APSCS_NUM_SHUTTERS
            )

    async def test_config_llcs(self) -> None:
        async with self.create_mtdomecom():
            assert math.isclose(
                self.mtdomecom_com.mock_ctrl.amcs.jmax,
                self.mtdomecom_com.mock_ctrl.amcs.amcs_limits.jmax,
            )
            system = mtdomecom.LlcName.AMCS
            settings = [
                {"target": "jmax", "setting": [1.0]},
                {"target": "amax", "setting": [0.5]},
                {"target": "vmax", "setting": [1.0]},
            ]
            await self.mtdomecom_com.config_llcs(system, settings)
            assert math.isclose(self.mtdomecom_com.mock_ctrl.amcs.jmax, math.radians(1.0))

    async def test_fans(self) -> None:
        async with self.create_mtdomecom():
            assert math.isclose(self.mtdomecom_com.mock_ctrl.amcs.fans_speed, 0.0)
            await self.mtdomecom_com.fans(speed=10.0)
            assert math.isclose(self.mtdomecom_com.mock_ctrl.amcs.fans_speed, 10.0)

    async def test_inflate(self) -> None:
        async with self.create_mtdomecom():
            assert self.mtdomecom_com.mock_ctrl.amcs.seal_inflated == OnOff.OFF
            await self.mtdomecom_com.inflate(action=OnOff.ON)
            assert self.mtdomecom_com.mock_ctrl.amcs.seal_inflated == OnOff.ON

    async def test_set_power_management_mode(self) -> None:
        async with self.create_mtdomecom():
            assert self.mtdomecom_com.power_management_mode == PowerManagementMode.NO_POWER_MANAGEMENT
            await self.mtdomecom_com.set_power_management_mode(PowerManagementMode.EMERGENCY)
            assert self.mtdomecom_com.power_management_mode == PowerManagementMode.EMERGENCY

    async def test_all_periodic_tasks(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.disconnect()
            telemetry_callbacks = {
                mtdomecom.LlcName.AMCS: self.handle_llc_status,
                mtdomecom.LlcName.APSCS: self.handle_llc_status,
                mtdomecom.LlcName.CBCS: self.handle_llc_status,
                mtdomecom.LlcName.CSCS: self.handle_llc_status,
                mtdomecom.LlcName.LCS: self.handle_llc_status,
                mtdomecom.LlcName.LWSCS: self.handle_llc_status,
                mtdomecom.LlcName.MONCS: self.handle_llc_status,
                mtdomecom.LlcName.RAD: self.handle_llc_status,
                mtdomecom.LlcName.THCS: self.handle_llc_status,
            }
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
            )
            await self.mtdomecom_com.connect()
            # OBC statuses are not reported yet.
            while len(self.mtdomecom_com.lower_level_status) < len(mtdomecom.LlcName) - 1:
                await asyncio.sleep(0.1)
            assert len(self.mtdomecom_com.lower_level_status) == len(mtdomecom.LlcName) - 1

    async def test_request_llc_status(self) -> None:
        async with self.create_mtdomecom():
            self.mtdomecom_com.telemetry_callbacks = {mtdomecom.LlcName.AMCS: self.handle_llc_status}
            await self.mtdomecom_com.request_llc_status(mtdomecom.LlcName.AMCS)
            assert self.llc_status is not None
            assert (
                self.llc_status["positionActual"]
                == utils.angle_wrap_nonnegative(
                    mtdomecom.AMCS_PARK_POSITION - mtdomecom.DOME_AZIMUTH_OFFSET
                ).degree
            )

    async def test_llc_status(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.disconnect()
            telemetry_callbacks = {
                mtdomecom.LlcName.AMCS: self.handle_llc_status,
                mtdomecom.LlcName.APSCS: self.handle_llc_status,
                mtdomecom.LlcName.CBCS: self.handle_llc_status,
                mtdomecom.LlcName.CSCS: self.handle_llc_status,
                mtdomecom.LlcName.LCS: self.handle_llc_status,
                mtdomecom.LlcName.LWSCS: self.handle_llc_status,
                mtdomecom.LlcName.MONCS: self.handle_llc_status,
                mtdomecom.LlcName.RAD: self.handle_llc_status,
                mtdomecom.LlcName.THCS: self.handle_llc_status,
            }
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
                start_periodic_tasks=False,
            )

            await self.mtdomecom_com.connect()
            assert len(self.mtdomecom_com.telemetry_callbacks) == len(telemetry_callbacks)

            await self.mtdomecom_com.status_amcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.AMCS]

            await self.mtdomecom_com.status_apscs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.APSCS]

            await self.mtdomecom_com.status_cbcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.CBCS]

            await self.mtdomecom_com.status_cscs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.CSCS]

            await self.mtdomecom_com.status_lcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.LCS]

            await self.mtdomecom_com.status_lwscs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.LWSCS]

            await self.mtdomecom_com.status_moncs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.MONCS]

            await self.mtdomecom_com.status_rad()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.RAD]

            await self.mtdomecom_com.status_thcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.THCS]

    async def test_rotating_communication_error(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.disconnect()
            telemetry_callbacks = {
                mtdomecom.LlcName.AMCS: self.handle_llc_status,
                mtdomecom.LlcName.APSCS: self.handle_llc_status,
                mtdomecom.LlcName.CBCS: self.handle_llc_status,
                mtdomecom.LlcName.CSCS: self.handle_llc_status,
                mtdomecom.LlcName.LCS: self.handle_llc_status,
                mtdomecom.LlcName.LWSCS: self.handle_llc_status,
                mtdomecom.LlcName.MONCS: self.handle_llc_status,
                mtdomecom.LlcName.RAD: self.handle_llc_status,
                mtdomecom.LlcName.THCS: self.handle_llc_status,
            }
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
                start_periodic_tasks=False,
                communication_error=True,
            )

            await self.mtdomecom_com.connect()
            assert len(self.mtdomecom_com.telemetry_callbacks) == len(telemetry_callbacks)

            # Not on the rotating part so should work.
            await self.mtdomecom_com.status_amcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.AMCS]

            # On the rotating part so should not work.
            await self.mtdomecom_com.status_apscs()
            assert mtdomecom.LlcName.APSCS not in self.mtdomecom_com.lower_level_status
            assert "command_name" in self.llc_status
            assert "exception" in self.llc_status
            assert "response_code" in self.llc_status
            assert self.llc_status["command_name"] == mtdomecom.CommandName.STATUS_APSCS
            assert self.llc_status["response_code"] == mtdomecom.ResponseCode.ROTATING_PART_NOT_RECEIVED

            with pytest.raises(ValueError) as ve:
                await self.mtdomecom_com.open_shutter()
            assert "was not received by the rotating part" in str(ve.value)

    async def test_fixed_communication_error(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.disconnect()
            telemetry_callbacks = {mtdomecom.LlcName.AMCS: self.handle_llc_status}
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
                start_periodic_tasks=False,
                communication_error=False,
            )

            # No communication error so should work.
            await self.mtdomecom_com.connect()
            await self.mtdomecom_com.status_amcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.AMCS]

            # Communication error so should not work.
            self.mtdomecom_com.client.write_json = self.write_json

            await self.mtdomecom_com.status_amcs()

            assert "command_name" in self.llc_status
            assert "exception" in self.llc_status
            assert "response_code" in self.llc_status
            assert self.llc_status["command_name"] == mtdomecom.CommandName.STATUS_AMCS
            assert self.llc_status["response_code"] == mtdomecom.ResponseCode.NOT_CONNECTED

    async def write_json(self, data: typing.Any) -> None:
        """Method to mock a connection error."""
        raise ConnectionError()

    async def test_communication_error_fixed_part(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.disconnect()
            telemetry_callbacks = {mtdomecom.LlcName.AMCS: self.handle_llc_status}
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
                start_periodic_tasks=False,
            )

            await self.mtdomecom_com.connect()
            assert len(self.mtdomecom_com.telemetry_callbacks) == len(telemetry_callbacks)

            # No communication error so should work.
            await self.mtdomecom_com.status_amcs()
            assert self.llc_status == self.mtdomecom_com.lower_level_status[mtdomecom.LlcName.AMCS]

            await self.mtdomecom_com.mock_ctrl.close()

            # Communication error so should not work.
            await self.mtdomecom_com.status_amcs()
            assert "exception" in self.llc_status

    @patch("lsst.ts.mtdomecom.mtdome_com._TIMEOUT", 3.0)
    async def test_timeout_error(self) -> None:
        async with self.create_mtdomecom():
            await self.mtdomecom_com.disconnect()
            telemetry_callbacks = {
                mtdomecom.LlcName.AMCS: self.handle_llc_status,
                mtdomecom.LlcName.APSCS: self.handle_llc_status,
                mtdomecom.LlcName.CBCS: self.handle_llc_status,
                mtdomecom.LlcName.CSCS: self.handle_llc_status,
                mtdomecom.LlcName.LCS: self.handle_llc_status,
                mtdomecom.LlcName.LWSCS: self.handle_llc_status,
                mtdomecom.LlcName.MONCS: self.handle_llc_status,
                mtdomecom.LlcName.RAD: self.handle_llc_status,
                mtdomecom.LlcName.THCS: self.handle_llc_status,
            }
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
                start_periodic_tasks=False,
            )

            await self.mtdomecom_com.connect()
            self.mtdomecom_com.mock_ctrl.timeout_error = True
            assert len(self.mtdomecom_com.telemetry_callbacks) == len(telemetry_callbacks)

            await self.mtdomecom_com.status_amcs()
            assert "exception" in self.llc_status

            with pytest.raises(TimeoutError):
                await self.mtdomecom_com.park()

    async def test_thermal_schema(self) -> None:
        async with self.create_mtdomecom():
            telemetry_callbacks = {
                mtdomecom.LlcName.AMCS: self.handle_llc_status,
                mtdomecom.LlcName.THCS: self.handle_llc_status,
            }
            self.mtdomecom_com = mtdomecom.MTDomeCom(
                log=self.log,
                config=types.SimpleNamespace(),
                config_dir=CONFIG_DIR,
                simulation_mode=mtdomecom.ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER,
                telemetry_callbacks=telemetry_callbacks,
                start_periodic_tasks=False,
            )
            await self.mtdomecom_com.connect()

            await self.mtdomecom_com.status_amcs()
            amcs_status = self.llc_status
            await self.mtdomecom_com.status_thcs()
            thcs_status = self.llc_status
            assert "driveTemperature" not in amcs_status
            assert "temperature" not in thcs_status
            assert "driveTemperature" in thcs_status
            assert "motorCoilTemperature" in thcs_status
            assert "cabinetTemperature" in thcs_status

    async def handle_llc_status(self, status: dict[str, typing.Any]) -> None:
        self.llc_status = status
