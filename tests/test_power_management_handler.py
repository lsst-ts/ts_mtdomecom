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

import logging
import unittest
from dataclasses import dataclass

from lsst.ts import mtdomecom
from lsst.ts.xml.enums.MTDome import OnOff, PowerManagementMode

CLOSE_SHUTTER = mtdomecom.ScheduledCommand(
    command=mtdomecom.CommandName.CLOSE_SHUTTER, params={}
)
FANS_ON = mtdomecom.ScheduledCommand(
    command=mtdomecom.CommandName.FANS, params={"action": OnOff.ON}
)
OPEN_SHUTTER = mtdomecom.ScheduledCommand(
    command=mtdomecom.CommandName.OPEN_SHUTTER, params={}
)
STOP_EL = mtdomecom.ScheduledCommand(command=mtdomecom.CommandName.STOP_EL, params={})
STOP_LOUVERS = mtdomecom.ScheduledCommand(
    command=mtdomecom.CommandName.STOP_LOUVERS, params={}
)


@dataclass
class PmTestData:
    command_to_schedule: mtdomecom.ScheduledCommand
    current_power_draw: dict[str, float]
    expected_command: mtdomecom.CommandName | None
    exp_cmd_in_queue: list[mtdomecom.CommandName]


ALL_PM_TEST_DATA: dict[PowerManagementMode, list[PmTestData]] = {
    PowerManagementMode.OPERATIONS: [
        PmTestData(
            command_to_schedule=FANS_ON,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: 0.0,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=FANS_ON,
            exp_cmd_in_queue=[],
        ),
        PmTestData(
            command_to_schedule=FANS_ON,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: mtdomecom.power_management.LOUVERS_POWER_DRAW,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=None,
            exp_cmd_in_queue=[FANS_ON],
        ),
        PmTestData(
            command_to_schedule=OPEN_SHUTTER,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: mtdomecom.power_management.LOUVERS_POWER_DRAW,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=None,
            exp_cmd_in_queue=[STOP_EL, STOP_LOUVERS, OPEN_SHUTTER],
        ),
        PmTestData(
            command_to_schedule=STOP_EL,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: mtdomecom.power_management.LOUVERS_POWER_DRAW,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=STOP_EL,
            exp_cmd_in_queue=[],
        ),
    ],
    PowerManagementMode.NO_POWER_MANAGEMENT: [
        PmTestData(
            command_to_schedule=OPEN_SHUTTER,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: 0.0,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=OPEN_SHUTTER,
            exp_cmd_in_queue=[],
        ),
    ],
    PowerManagementMode.MAINTENANCE: [
        PmTestData(
            command_to_schedule=OPEN_SHUTTER,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: 0.0,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=None,
            exp_cmd_in_queue=[],
        ),
    ],
    PowerManagementMode.EMERGENCY: [
        PmTestData(
            command_to_schedule=OPEN_SHUTTER,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: 0.0,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=None,
            exp_cmd_in_queue=[],
        ),
        PmTestData(
            command_to_schedule=CLOSE_SHUTTER,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: mtdomecom.power_management.LWS_POWER_DRAW,
                mtdomecom.LlcName.LCS: 0.0,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=None,
            exp_cmd_in_queue=[STOP_EL, CLOSE_SHUTTER],
        ),
        PmTestData(
            command_to_schedule=CLOSE_SHUTTER,
            current_power_draw={
                mtdomecom.LlcName.AMCS: 0.0,
                mtdomecom.LlcName.APSCS: 0.0,
                mtdomecom.LlcName.CSCS: 0.0,
                mtdomecom.LlcName.LWSCS: 0.0,
                mtdomecom.LlcName.LCS: 0.0,
                mtdomecom.LlcName.OBC: 0.0,
                mtdomecom.LlcName.RAD: 0.0,
            },
            expected_command=CLOSE_SHUTTER,
            exp_cmd_in_queue=[],
        ),
    ],
}


class PowerManagementHandlerTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.pmh = mtdomecom.power_management.PowerManagementHandler(
            log=self.log,
            command_priorities=mtdomecom.power_management.command_priorities,
        )
        self.current_power_draw: dict[str, float] = {}

    async def test_schedule_command(self) -> None:
        assert self.pmh.command_queue.empty()
        command_to_scedule = mtdomecom.ScheduledCommand(
            command=mtdomecom.CommandName.OPEN_SHUTTER, params={}
        )
        await self.pmh.schedule_command(command_to_scedule)
        assert self.pmh.command_queue.qsize() == 1
        _, scheduled_command = await self.pmh.command_queue.get()
        assert scheduled_command == command_to_scedule
        assert self.pmh.command_queue.empty()

    async def verify_next_command(
        self,
        expected_command: mtdomecom.CommandName | None,
        exp_cmd_in_queue: list[mtdomecom.CommandName],
    ) -> None:
        cmd = await self.pmh.get_next_command(self.current_power_draw)
        assert cmd == expected_command
        assert self.pmh.command_queue.qsize() == len(exp_cmd_in_queue)
        for i in range(len(exp_cmd_in_queue)):
            _, scheduled_command = self.pmh.command_queue.get_nowait()
            assert scheduled_command == exp_cmd_in_queue[i]

    async def test_get_next_command(self) -> None:
        for pmm in PowerManagementMode:
            self.pmh.power_management_mode = pmm
            pm_test_data = ALL_PM_TEST_DATA[self.pmh.power_management_mode]
            for data in pm_test_data:
                self.current_power_draw = data.current_power_draw
                await self.pmh.schedule_command(data.command_to_schedule)
                await self.verify_next_command(
                    expected_command=data.expected_command,
                    exp_cmd_in_queue=data.exp_cmd_in_queue,
                )
