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

import dataclasses

from lsst.ts import mtdomecom
from lsst.ts.xml.enums.MTDome import MotionState


@dataclasses.dataclass
class CoolDownTestData:
    tai: float
    power_drawn: float
    expected_power_available: float
    expected_state: mtdomecom.SlipRingState


@dataclasses.dataclass
class ExpectedState:
    tai: float
    position: float
    velocity: float
    motion_state: MotionState


@dataclasses.dataclass
class SlipRingTestData:
    max_power_drawn: float
    time_over_limit: float
    expected_cool_down_time: float
