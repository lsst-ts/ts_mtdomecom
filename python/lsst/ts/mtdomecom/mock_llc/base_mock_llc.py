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

__all__ = [
    "DEFAULT_MESSAGES",
    "FAULT_MESSAGES",
    "BaseMockStatus",
]

import logging
import typing
from abc import ABC, abstractmethod

from lsst.ts.xml.enums.MTDome import OperationalMode

# Status messages.
DEFAULT_MESSAGES = [{"code": 0, "description": "No Errors"}]
FAULT_MESSAGES = [{"code": 1, "description": "Motors in error state."}]


class BaseMockStatus(ABC):
    """Abstract base class for all mock status classes used by the mock
    controller when in simulator mode.
    """

    def __init__(self) -> None:
        # A dict to hold the status of the Lower Level Component.
        self.llc_status: dict[str, typing.Any] = {}
        # Operational mode of the Lower Level Component.
        self.operational_mode = OperationalMode.NORMAL
        # Time of the last executed command, in TAI Unix seconds.
        self.command_time_tai = 0.0
        # Logger.
        self.log = logging.getLogger("BaseMockStatus")

    @abstractmethod
    async def determine_status(self, current_tai: float) -> None:
        """Abstract method that determines the status of the Lower Level
        Component to be implemented by all concrete sub-classes.

        Parameters
        ----------
        current_tai: `float`
            The current Unix TAI time, in seconds
        """
        raise NotImplementedError

    async def set_normal(self) -> None:
        """Set operational state to normal (as opposed to degraded)."""
        self.operational_mode = OperationalMode.NORMAL

    async def set_degraded(self) -> None:
        """Set operational state to degraded (as opposed to normal)."""
        self.operational_mode = OperationalMode.DEGRADED
