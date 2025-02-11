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

__all__ = ["MoncsStatus"]

import logging

import numpy as np
from lsst.ts.xml.enums.MTDome import MotionState

from ..constants import MON_NUM_SENSORS
from .base_mock_llc import BaseMockStatus


class MoncsStatus(BaseMockStatus):
    """Represents the status of the Monitor Control System in simulation
    mode.
    """

    def __init__(self) -> None:
        super().__init__()
        self.log = logging.getLogger("MockMoncsStatus")
        self.status = MotionState.CLOSED.name
        self.messages = [{"code": 0, "description": "No Errors"}]
        self.data = np.zeros(MON_NUM_SENSORS, dtype=float)

    async def determine_status(self, current_tai: float) -> None:
        """Determine the status of the Lower Level Component and store it in
        the llc_status `dict`.
        """
        time_diff = current_tai - self.command_time_tai
        self.log.debug(
            f"current_tai = {current_tai}, self.command_time_tai = {self.command_time_tai}, "
            f"time_diff = {time_diff}"
        )
        self.llc_status = {
            "status": {
                "messages": self.messages,
                "status": self.status,
                "operationalMode": self.operational_mode.name,
            },
            "data": self.data.tolist(),
            "timestampUTC": current_tai,
        }
        self.log.debug(f"moncs_state = {self.llc_status}")
