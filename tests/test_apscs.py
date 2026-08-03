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

import unittest

import numpy as np
import pytest

from lsst.ts import mtdomecom
from lsst.ts.mtdomecom.power_management.power_draw_constants import APS_POWER_DRAW
from lsst.ts.xml.enums.MTDome import MotionState, OnOff

START_TAI = 10001.0


class ApscsTestCase(unittest.IsolatedAsyncioTestCase):
    async def prepare_apscs(
        self, start_position: float, start_tai: float, start_state: MotionState, current_state: MotionState
    ) -> None:
        """Prepare the ApSCS for future commands.

        Parameters
        ----------
        start_position : `float`
            The start position of the azimuth motion.
        start_tai : `float`
            The start TAI time.
        start_state : `MotionState`
            The start MotionState.
        current_state : `MotionState`
            The current MotionState.
        """
        self.apscs = mtdomecom.mock_llc.ApscsStatus(start_tai=start_tai)
        self.apscs.position_actual = np.asarray([start_position, start_position])
        self.apscs.start_state = [start_state] * mtdomecom.APSCS_NUM_SHUTTERS
        self.apscs.current_state = [current_state] * mtdomecom.APSCS_NUM_SHUTTERS
        if current_state == MotionState.OPEN.name:
            self.apscs.open_limit_switches_engaged = [True, True]

    async def verify_apscs(
        self,
        tai: float,
        expected_position: float,
        expected_motion_state: MotionState,
    ) -> None:
        """Verify the position of the ApSCS at the given TAI time.

        Parameters
        ----------
        tai: `float`
            The TAI time to compute the position for.
        expected_position: `float`
            The expected position at the given TAI time.
        expected_motion_state: `float`
            The expected motion state at the given TAI time.
        """
        await self.apscs.determine_status(current_tai=tai)
        assert [expected_position] * mtdomecom.APSCS_NUM_SHUTTERS == pytest.approx(
            self.apscs.llc_status["positionActual"], abs=0.001
        )
        assert [expected_motion_state.name] * mtdomecom.APSCS_NUM_SHUTTERS == self.apscs.llc_status["status"][
            "status"
        ]
        expected_drive_current: list[float] = (
            [0.0] * mtdomecom.APSCS_NUM_SHUTTERS * mtdomecom.APSCS_NUM_MOTORS_PER_SHUTTER
        )
        expected_power_draw = 0.0
        if self.apscs.motors_powered_off == [True, True]:
            expected_drive_current = (
                [0.0] * mtdomecom.APSCS_NUM_SHUTTERS * mtdomecom.APSCS_NUM_MOTORS_PER_SHUTTER
            )
            expected_power_draw = 0.0
        elif expected_motion_state in [MotionState.OPENING, MotionState.CLOSING]:
            expected_drive_current = (
                [mtdomecom.APSCS_CURRENT_PER_MOTOR]
                * mtdomecom.APSCS_NUM_SHUTTERS
                * mtdomecom.APSCS_NUM_MOTORS_PER_SHUTTER
            )
            expected_power_draw = APS_POWER_DRAW
        assert expected_drive_current == self.apscs.llc_status["driveCurrentActual"]
        assert expected_power_draw == self.apscs.llc_status["powerDraw"]

    async def test_stop_shutter(self) -> None:
        """Test stopping the shutter while moving, switch the power off and
        on, and then close the shutter."""
        start_position = mtdomecom.APSCS_CLOSED_POSITION
        target_position = mtdomecom.APSCS_OPEN_POSITION
        start_tai = START_TAI
        expected_duration = (target_position - start_position) / mtdomecom.APSCS_SHUTTER_SPEED

        for switch_motors_off in [False, True]:
            with self.subTest(switch_motors_off=switch_motors_off):
                await self.prepare_apscs(
                    start_position=start_position,
                    start_tai=start_tai,
                    start_state=MotionState.CLOSING.name,
                    current_state=MotionState.CLOSING.name,
                )
                duration = await self.apscs.openShutter(start_tai=start_tai)
                assert expected_duration == duration
                for i in range(6):
                    await self.verify_apscs(
                        tai=start_tai + i,
                        expected_position=mtdomecom.APSCS_SHUTTER_SPEED * i,
                        expected_motion_state=MotionState.CLOSING,
                    )

                start_tai = start_tai + 7.0
                assert self.apscs.was_stopped_command_issued == [False, False]
                await self.apscs.stopShutter(start_tai=start_tai)
                assert self.apscs.was_stopped_command_issued == [True, True]
                expected_stop_position = 70.0
                for i in range(2):
                    start_tai += 0.1
                    await self.verify_apscs(
                        tai=start_tai,
                        expected_position=expected_stop_position,
                        expected_motion_state=MotionState.STOPPED,
                    )
                    assert self.apscs.was_stopped_command_issued == [True, True]

                # Switch the power off so the shutter doors position is lost.
                self.apscs.motors_powered_off = [switch_motors_off, switch_motors_off]

                if switch_motors_off:
                    expected_start_position = mtdomecom.APSCS_CLOSED_POSITION
                    expected_end_position = -expected_stop_position
                else:
                    expected_start_position = expected_stop_position
                    expected_end_position = mtdomecom.APSCS_CLOSED_POSITION

                await self.apscs.determine_status(start_tai)

                # Now switch the power back on.
                self.apscs.motors_powered_off = [False, False]
                await self.apscs.closeShutter(start_tai=start_tai)
                assert self.apscs.was_stopped_command_issued == [True, True]
                for i in range(7):
                    await self.verify_apscs(
                        tai=start_tai + i,
                        expected_position=expected_start_position - mtdomecom.APSCS_SHUTTER_SPEED * i,
                        expected_motion_state=MotionState.CLOSING,
                    )
                tai = start_tai + 7.1
                await self.verify_apscs(
                    tai=tai,
                    expected_position=expected_end_position,
                    expected_motion_state=MotionState.PROXIMITY_CLOSED_LS_ENGAGED,
                )

    async def test_go_stationary_shutter(self) -> None:
        """Test setting the shutter to GO_STATIONARY while moving."""
        start_position = mtdomecom.APSCS_CLOSED_POSITION
        target_position = mtdomecom.APSCS_OPEN_POSITION
        start_tai = START_TAI
        expected_duration = (target_position - start_position) / mtdomecom.APSCS_SHUTTER_SPEED
        await self.prepare_apscs(
            start_position=start_position,
            start_tai=start_tai,
            start_state=MotionState.CLOSING.name,
            current_state=MotionState.CLOSING.name,
        )
        duration = await self.apscs.openShutter(start_tai=start_tai)
        assert expected_duration == duration
        for i in range(6):
            await self.verify_apscs(
                tai=start_tai + i,
                expected_position=mtdomecom.APSCS_SHUTTER_SPEED * i,
                expected_motion_state=MotionState.CLOSING,
            )

        await self.apscs.go_stationary(start_tai=start_tai + 7.0)
        await self.verify_apscs(
            tai=start_tai + 7.1,
            expected_position=70.0,
            expected_motion_state=MotionState.STOPPING,
        )
        await self.verify_apscs(
            tai=start_tai + 7.2,
            expected_position=70.0,
            expected_motion_state=MotionState.STOPPED,
        )
        await self.verify_apscs(
            tai=start_tai + 7.2,
            expected_position=70.0,
            expected_motion_state=MotionState.ENGAGING_BRAKES,
        )

    async def test_exit_fault(self) -> None:
        """Test going to and exiting from the ERROR state while moving."""
        start_position = mtdomecom.APSCS_CLOSED_POSITION
        target_position = mtdomecom.APSCS_OPEN_POSITION
        start_tai = START_TAI
        expected_duration = (target_position - start_position) / mtdomecom.APSCS_SHUTTER_SPEED
        await self.prepare_apscs(
            start_position=start_position,
            start_tai=start_tai,
            start_state=MotionState.CLOSING.name,
            current_state=MotionState.CLOSING.name,
        )
        duration = await self.apscs.openShutter(start_tai=start_tai)
        assert expected_duration == duration
        await self.verify_apscs(
            tai=START_TAI + 1.0,
            expected_position=10.0,
            expected_motion_state=MotionState.CLOSING,
        )

        # This sets the status of the state machine to ERROR.
        drives_in_error = [0, 1, 0, 1]
        expected_drive_error_state = [False, True]
        current_tai = START_TAI + 1.1
        await self.apscs.set_fault(current_tai, drives_in_error)
        for shutter_id in range(mtdomecom.APSCS_NUM_SHUTTERS):
            assert self.apscs.drives_in_error_state[shutter_id] == expected_drive_error_state
        await self.verify_apscs(
            tai=current_tai,
            expected_position=11.0,
            expected_motion_state=MotionState.ERROR,
        )

        current_tai = START_TAI + 2.0

        # Now call exit_fault. This will fail because there still are drives at
        # fault.
        with pytest.raises(RuntimeError):
            await self.apscs.exit_fault(current_tai)

        # Reset the drives.
        expected_drive_error_state = [False, False]
        reset = [0, 1, 0, 1]
        await self.apscs.reset_drives_shutter(current_tai, reset)
        for shutter_id in range(mtdomecom.APSCS_NUM_SHUTTERS):
            assert self.apscs.drives_in_error_state[shutter_id] == expected_drive_error_state

        # Now call "exit_fault" which will not fail because the drives have
        # been reset.
        await self.apscs.exit_fault(current_tai)
        await self.verify_apscs(
            tai=current_tai,
            expected_position=11.0,
            expected_motion_state=mtdomecom.InternalMotionState.STATIONARY,
        )
        for shutter_id in range(mtdomecom.APSCS_NUM_SHUTTERS):
            assert self.apscs.drives_in_error_state[shutter_id] == expected_drive_error_state

    async def test_open_and_close_shutter_with_and_without_power_off(self) -> None:
        """Test opening the shutter from a closed position, simulate a power
        off or not, and then close."""
        start_position = mtdomecom.APSCS_CLOSED_POSITION
        target_position = mtdomecom.APSCS_OPEN_POSITION
        expected_duration = (target_position - start_position) / mtdomecom.APSCS_SHUTTER_SPEED

        for switch_motors_off in [False, True]:
            with self.subTest(switch_motors_off=switch_motors_off):
                start_tai = START_TAI
                await self.prepare_apscs(
                    start_position=start_position,
                    start_tai=start_tai,
                    start_state=MotionState.CLOSED.name,
                    current_state=MotionState.CLOSED.name,
                )
                duration = await self.apscs.openShutter(start_tai=start_tai)
                assert expected_duration == duration

                for expected_state in [
                    MotionState.LP_DISENGAGING.name,
                    MotionState.LP_DISENGAGED.name,
                    MotionState.ENABLING_MOTOR_POWER.name,
                    MotionState.MOTOR_POWER_ON.name,
                    MotionState.GO_NORMAL.name,
                    MotionState.DISENGAGING_BRAKES.name,
                    MotionState.BRAKES_DISENGAGED.name,
                    MotionState.OPENING.name,
                ]:
                    await self.apscs.determine_status(current_tai=start_tai)
                    assert self.apscs.llc_status["status"]["status"] == [
                        expected_state,
                        expected_state,
                    ]
                    assert [start_position] * mtdomecom.APSCS_NUM_SHUTTERS == pytest.approx(
                        self.apscs.llc_status["positionActual"], abs=0.0001
                    )
                    assert self.apscs.open_limit_switches_engaged == [False, False]

                for i in range(10):
                    await self.verify_apscs(
                        tai=start_tai + i,
                        expected_position=mtdomecom.APSCS_SHUTTER_SPEED * i,
                        expected_motion_state=MotionState.OPENING,
                    )
                await self.verify_apscs(
                    tai=start_tai + 10,
                    expected_position=mtdomecom.APSCS_OPEN_POSITION,
                    expected_motion_state=MotionState.PROXIMITY_OPEN_LS_ENGAGED,
                )

                tai = start_tai + duration
                for expected_state in [
                    MotionState.FINAL_UP_OPEN_LS_ENGAGED.name,
                    MotionState.FINAL_LOW_OPEN_LS_ENGAGED.name,
                    MotionState.STOPPING.name,
                    MotionState.STOPPED.name,
                    MotionState.ENGAGING_BRAKES.name,
                    MotionState.BRAKES_ENGAGED.name,
                    MotionState.GO_STATIONARY.name,
                    MotionState.DISABLING_MOTOR_POWER.name,
                    MotionState.MOTOR_POWER_OFF.name,
                    MotionState.OPEN.name,
                ]:
                    await self.apscs.determine_status(current_tai=tai)
                    assert self.apscs.llc_status["status"]["status"] == [
                        expected_state,
                        expected_state,
                    ]
                    assert [target_position] * mtdomecom.APSCS_NUM_SHUTTERS == pytest.approx(
                        self.apscs.llc_status["positionActual"], abs=0.0001
                    )
                    if expected_state in [
                        MotionState.FINAL_UP_OPEN_LS_ENGAGED.name,
                        MotionState.FINAL_LOW_OPEN_LS_ENGAGED.name,
                    ]:
                        assert self.apscs.open_limit_switches_engaged == [False, False]
                    else:
                        assert self.apscs.open_limit_switches_engaged == [True, True]

                if switch_motors_off:
                    expected_start_position = mtdomecom.APSCS_CLOSED_POSITION
                    expected_target_position = -mtdomecom.APSCS_OPEN_POSITION
                else:
                    expected_start_position = mtdomecom.APSCS_OPEN_POSITION
                    expected_target_position = mtdomecom.APSCS_CLOSED_POSITION

                # Potentially switch the motor power off.
                self.apscs.motors_powered_off = [switch_motors_off, switch_motors_off]

                start_tai = tai
                duration = await self.apscs.closeShutter(start_tai=start_tai)
                assert expected_duration == pytest.approx(duration)

                for expected_state in [
                    MotionState.ENABLING_MOTOR_POWER.name,
                    MotionState.MOTOR_POWER_ON.name,
                    MotionState.GO_NORMAL.name,
                    MotionState.DISENGAGING_BRAKES.name,
                    MotionState.BRAKES_DISENGAGED.name,
                    MotionState.CLOSING.name,
                ]:
                    await self.apscs.determine_status(current_tai=start_tai)
                    assert self.apscs.llc_status["status"]["status"] == [
                        expected_state,
                        expected_state,
                    ]
                    assert [expected_start_position] * mtdomecom.APSCS_NUM_SHUTTERS == pytest.approx(
                        self.apscs.llc_status["positionActual"], abs=0.0001
                    )
                    assert self.apscs.open_limit_switches_engaged == [False, False]

                # At this point, the motors are always powered on, even if they
                # were powered off before.
                assert self.apscs.motors_powered_off == [False, False]
                for i in range(10):
                    await self.verify_apscs(
                        tai=start_tai + i,
                        expected_position=expected_start_position - mtdomecom.APSCS_SHUTTER_SPEED * i,
                        expected_motion_state=MotionState.CLOSING,
                    )
                tai = start_tai + duration
                await self.verify_apscs(
                    tai=tai,
                    expected_position=expected_target_position,
                    expected_motion_state=MotionState.PROXIMITY_CLOSED_LS_ENGAGED,
                )

                for expected_state in [
                    MotionState.FINAL_UP_CLOSE_LS_ENGAGED.name,
                    MotionState.FINAL_LOW_CLOSE_LS_ENGAGED.name,
                    MotionState.STOPPING.name,
                    MotionState.STOPPED.name,
                    MotionState.ENGAGING_BRAKES.name,
                    MotionState.BRAKES_ENGAGED.name,
                    MotionState.GO_STATIONARY.name,
                    MotionState.LP_ENGAGING.name,
                    MotionState.LP_ENGAGED.name,
                    MotionState.DISABLING_MOTOR_POWER.name,
                    MotionState.MOTOR_POWER_OFF.name,
                    MotionState.CLOSED.name,
                ]:
                    await self.apscs.determine_status(current_tai=tai)
                    assert self.apscs.llc_status["status"]["status"] == [
                        expected_state,
                        expected_state,
                    ]
                    assert [expected_target_position] * mtdomecom.APSCS_NUM_SHUTTERS == pytest.approx(
                        self.apscs.llc_status["positionActual"], abs=0.0001
                    )
                    assert self.apscs.open_limit_switches_engaged == [False, False]

    async def test_set_photocell(self) -> None:
        """Test switching off and on the photocell."""
        self.apscs = mtdomecom.mock_llc.ApscsStatus(start_tai=START_TAI)
        assert self.apscs.photocell_on == OnOff.ON
        await self.apscs.set_photocell_shutter(start_tai=START_TAI, action=False)
        assert self.apscs.photocell_on is OnOff.OFF
        await self.apscs.set_photocell_shutter(start_tai=START_TAI, action=True)
        assert self.apscs.photocell_on is OnOff.ON
