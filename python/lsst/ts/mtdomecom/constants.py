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

import math

from .power_management import APS_POWER_DRAW, LOUVERS_POWER_DRAW, LWS_POWER_DRAW

# General constants.
DOME_AZIMUTH_OFFSET = 32.0
DOME_VOLTAGE = 220.0

# AMCS constants.
AMCS_NUM_MOTORS = 5
AMCS_NUM_MOTOR_TEMPERATURES = 13
AMCS_NUM_ENCODERS = 5
AMCS_NUM_RESOLVERS = 3
# Current consumption per motor when moving [A], assuming no acceleration and
# no wind gust, which is good enough for this simulator, since it ignores both.
AMCS_CURRENT_PER_MOTOR_MOVING = 40.0
# Current consumption per motor when crawling [A].
AMCS_CURRENT_PER_MOTOR_CRAWLING = 4.1
AMCS_PARK_POSITION = 0.0
# Maximum jerk in rad/s^3
AMCS_JMAX = math.radians(3.0)
# Maximum acceleration in rad/s^2
AMCS_AMAX = math.radians(0.75)
# Maximum velocity in rad/s
AMCS_VMAX = math.radians(1.5)

# APSCS constants.
APSCS_NUM_SHUTTERS = 2
# The number of motors per shutter.
APSCS_NUM_MOTORS_PER_SHUTTER = 2
# The shutter is 0% open.
APSCS_CLOSED_POSITION = 0.0
# The shutter is 100% open.
APSCS_OPEN_POSITION = 100.0
# The shutter speed (%/s). This is an assumed value such that the shutter opens
# or closes in 10 seconds.
APSCS_SHUTTER_SPEED = 10.0
# The motors jitter a bit and this defines the jitter range.
APSCS_POSITION_JITTER = 2.5e-7
# Current per motor drawn by the Aperture Shutter [A].
APSCS_CURRENT_PER_MOTOR = (
    APS_POWER_DRAW / APSCS_NUM_SHUTTERS / APSCS_NUM_MOTORS_PER_SHUTTER / DOME_VOLTAGE
)

# CBCS constants.
CBCS_NUM_CAPACITOR_BANKS = 2

# LCS constants.
LCS_NUM_LOUVERS = 34
LCS_NUM_MOTORS_PER_LOUVER = 2
# Current drawn per louver [A].
_CURRENT_PER_LOUVER = LOUVERS_POWER_DRAW / LCS_NUM_LOUVERS / DOME_VOLTAGE
# Current drawn per motor by the louvers [A].
LCS_CURRENT_PER_MOTOR = _CURRENT_PER_LOUVER / LCS_NUM_MOTORS_PER_LOUVER
# Motion velocity of the louvers, equalling 100 % / 30 s
LCS_MOTION_VELOCITY = 100 / 30

# LWSCS constants.
LWSCS_NUM_MOTORS = 2
LWSCS_MIN_POSITION = 0.0
LWSCS_MAX_POSITION = math.pi / 2.0
# Current drawn per motor by the Light Wind Screen [A].
LWSCS_CURRENT_PER_MOTOR = LWS_POWER_DRAW / LWSCS_NUM_MOTORS / DOME_VOLTAGE
# Maximum jerk in rad/s^3
LWSCS_JMAX = math.radians(3.5)
# Maximum acceleration in rad/s^2
LWSCS_AMAX = math.radians(0.875)
# Maximum velocity in rad/s
LWSCS_VMAX = math.radians(1.75)

# MON constants.
MON_NUM_SENSORS = 16

# RAD constants.
RAD_NUM_DOORS = 2
RAD_NUM_LIMIT_SWITCHES = 4
RAD_NUM_LOCKING_PINS = 2

# THCS constants.
THCS_NUM_CABINET_TEMPERATURES = 3
THCS_NUM_MOTOR_COIL_TEMPERATURES = 5
THCS_NUM_MOTOR_DRIVE_TEMPERATURES = 10
# TODO OSW-862 Remove all references to the old temperature schema.
THCS_NUM_SENSORS = 13
