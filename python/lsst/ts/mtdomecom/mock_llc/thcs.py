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

__all__ = ["ThcsStatus"]

import logging

import numpy as np
from lsst.ts.xml.enums.MTDome import MotionState

from ..constants import (
    THCS_NUM_CABINET_TEMPERATURES,
    THCS_NUM_MOTOR_COIL_TEMPERATURES,
    THCS_NUM_MOTOR_DRIVE_TEMPERATURES,
)
from ..enums import InternalMotionState
from .base_mock_llc import BaseMockStatus


class ThcsStatus(BaseMockStatus):
    """Represents the status of the Thermal Control System in simulation
    mode."""

    def __init__(self) -> None:
        super().__init__()
        self.log = logging.getLogger("MockThcsStatus")
        self.messages = [{"code": 0, "description": "No Errors"}]
        self.drive_temperature = np.zeros(THCS_NUM_MOTOR_DRIVE_TEMPERATURES, dtype=float)
        self.motor_coil_temperature = np.zeros(THCS_NUM_MOTOR_COIL_TEMPERATURES, dtype=float)
        self.cabinet_temperature = np.zeros(THCS_NUM_CABINET_TEMPERATURES, dtype=float)
        self.current_state = MotionState.DISABLED.name
        self.target_state = MotionState.DISABLED.name

    async def evaluate_state(self) -> None:
        """Evaluate the state and perform a state transition if necessary."""
        match self.target_state:
            case MotionState.ENABLED.name:
                if self.current_state == MotionState.DISABLED.name:
                    self.current_state = MotionState.ENABLING.name
                elif self.current_state == MotionState.ENABLING.name:
                    self.current_state = MotionState.ENABLED.name
            case MotionState.DISABLED.name:
                if self.current_state == MotionState.ENABLED.name:
                    self.current_state = MotionState.DISABLING.name
                elif self.current_state == MotionState.DISABLING.name:
                    self.current_state = MotionState.DISABLED.name
            case _:
                # Not a valid state, so empty.
                pass

    async def determine_status(self, current_tai: float) -> None:
        """Determine the status of the Lower Level Component and store it in
        the llc_status `dict`.
        """
        await self.evaluate_state()
        self.llc_status = {
            "status": {
                "messages": self.messages,
                "status": self.current_state,
                "operationalMode": self.operational_mode.name,
            },
            "timestampUTC": current_tai,
            "driveTemperature": self.drive_temperature.tolist(),
            "motorCoilTemperature": self.motor_coil_temperature.tolist(),
            "cabinetTemperature": self.cabinet_temperature.tolist(),
        }
        self.log.debug(f"thcs_state = {self.llc_status}")

    async def set_temperature(self, temperature: float, current_tai: float) -> None:
        """Set the preferred temperature in the dome.

        Parameters
        ----------
        temperature: `float`
            The preferred temperature (degrees Celsius). In reality this should
            be a realistic temperature in the range of about -30 C to +40 C but
            the provided temperature is not checked against this range.
        current_tai : `float`
            The current time, in UNIX TAI seconds.
        """
        self.command_time_tai = current_tai
        self.drive_temperature[:] = temperature
        self.motor_coil_temperature[:] = temperature
        self.cabinet_temperature[:] = temperature

    async def start_cooling(self, current_tai: float) -> None:
        """Start cooling.

        Parameters
        ----------
        current_tai : `float`
            The current time, in UNIX TAI seconds.
        """
        self.command_time_tai = current_tai
        self.target_state = MotionState.ENABLED.name

    async def stop_cooling(self, current_tai: float) -> None:
        """Stop cooling.

        Parameters
        ----------
        current_tai : `float`
            The current time, in UNIX TAI seconds.
        """
        self.command_time_tai = current_tai
        self.target_state = MotionState.DISABLED.name

    async def exit_fault(self) -> None:
        """Clear the fault state."""
        self.current_state = InternalMotionState.STATIONARY.name
