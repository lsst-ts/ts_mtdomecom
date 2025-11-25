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
    "BRAKES_ENGAGED_STATES",
    "CSCS_COMMANDS",
    "EL_COMMANDS",
    "LOUVERS_COMMANDS",
    "POWER_MANAGEMENT_COMMANDS",
    "RAD_COMMANDS",
    "SHUTTER_COMMANDS",
    "STOP_EL",
    "STOP_FANS",
    "STOP_LOUVERS",
    "STOP_SHUTTER",
    "UNCONTROLLED_LLCS",
    "Brake",
    "CommandName",
    "InternalMotionState",
    "LlcName",
    "LlcNameDict",
    "MaxValueConfigType",
    "MaxValuesConfigType",
    "ResponseCode",
    "ScheduledCommand",
    "SlipRingState",
    "StopCommand",
    "ValidSimulationMode",
    "motion_state_translations",
]

import enum
import typing
from dataclasses import dataclass

from lsst.ts.xml.enums.MTDome import MotionState, OnOff, SubSystemId


class InternalMotionState(enum.IntEnum):
    """Internal Motion states.

    These get translated into IDL MotionState instances by the CSC.
    """

    STATIONARY = enum.auto()


# Dict holding translations from motion states, that the lower level
# controllers can have, to MotionState.
motion_state_translations = {InternalMotionState.STATIONARY.name: MotionState.STOPPED_BRAKED}


# TODO OSW-1491 Remove backward compatibility with XML 24.3
class Brake(enum.IntEnum):
    """Engagable brakes.

    Each item represents multiple brakes that are always engaged at the same
    time. This will be part of ts_xml starting with version 24.4.
    """

    AMCS = 1
    APSCS_LEFT_DOOR = 2
    APSCS_RIGHT_DOOR = 3
    LWSCS = 4
    LOUVER_A1 = 5
    LOUVER_A2 = 6
    LOUVER_B1 = 7
    LOUVER_B2 = 8
    LOUVER_B3 = 9
    LOUVER_C1 = 10
    LOUVER_C2 = 11
    LOUVER_C3 = 12
    LOUVER_D1 = 13
    LOUVER_D2 = 14
    LOUVER_D3 = 15
    LOUVER_E1 = 16
    LOUVER_E2 = 17
    LOUVER_E3 = 18
    LOUVER_F1 = 19
    LOUVER_F2 = 20
    LOUVER_F3 = 21
    LOUVER_G1 = 22
    LOUVER_G2 = 23
    LOUVER_G3 = 24
    LOUVER_H1 = 25
    LOUVER_H2 = 26
    LOUVER_H3 = 27
    LOUVER_I1 = 28
    LOUVER_I2 = 29
    LOUVER_I3 = 30
    LOUVER_L1 = 31
    LOUVER_L2 = 32
    LOUVER_L3 = 33
    LOUVER_M1 = 34
    LOUVER_M2 = 35
    LOUVER_M3 = 36
    LOUVER_N1 = 37
    LOUVER_N2 = 38
    CSCS = 39
    RAD_LEFT_DOOR = 40
    RAD_RIGHT_DOOR = 41


class CommandName(enum.StrEnum):
    """Command names."""

    CLOSE_LOUVERS = "closeLouvers"
    CLOSE_SHUTTER = "closeShutter"
    CONFIG = "config"
    CRAWL_AZ = "crawlAz"
    CRAWL_EL = "crawlEl"
    EXIT_FAULT = "exitFault"
    EXIT_FAULT_AZ = "exitFaultAz"
    EXIT_FAULT_EL = "exitFaultEl"
    EXIT_FAULT_SHUTTER = "exitFaultShutter"
    EXIT_FAULT_LOUVERS = "exitFaultLouvers"
    EXIT_FAULT_THERMAL = "exitFaultThermal"
    FANS = "fans"
    GO_STATIONARY_AZ = "goStationaryAz"
    GO_STATIONARY_EL = "goStationaryEl"
    GO_STATIONARY_LOUVERS = "goStationaryLouvers"
    GO_STATIONARY_SHUTTER = "goStationaryShutter"
    HOME = "home"
    INFLATE = "inflate"
    MOVE_AZ = "moveAz"
    MOVE_EL = "moveEl"
    OPEN_SHUTTER = "openShutter"
    PARK = "park"
    RESET_DRIVES_AZ = "resetDrivesAz"
    RESET_DRIVES_LOUVERS = "resetDrivesLouvers"
    RESET_DRIVES_SHUTTER = "resetDrivesShutter"
    RESTORE = "restore"
    SET_DEGRADED_AZ = "setDegradedAz"
    SET_DEGRADED_EL = "setDegradedEl"
    SET_DEGRADED_LOUVERS = "setDegradedLouvers"
    SET_DEGRADED_SHUTTER = "setDegradedShutter"
    SET_DEGRADED_MONITORING = "setDegradedMonitoring"
    SET_DEGRADED_THERMAL = "setDegradedThermal"
    SET_LOUVERS = "setLouvers"
    SET_NORMAL_AZ = "setNormalAz"
    SET_NORMAL_EL = "setNormalEl"
    SET_NORMAL_LOUVERS = "setNormalLouvers"
    SET_NORMAL_SHUTTER = "setNormalShutter"
    SET_NORMAL_MONITORING = "setNormalMonitoring"
    SET_NORMAL_THERMAL = "setNormalThermal"
    SET_POWER_MANAGEMENT_MODE = "setPowerManagementMode"
    SET_TEMPERATURE = "setTemperature"
    SET_ZERO_AZ = "setZeroAz"
    STATUS_AMCS = "statusAMCS"
    STATUS_APSCS = "statusApSCS"
    STATUS_CBCS = "statusCBCS"
    STATUS_CSCS = "statusCSCS"
    STATUS_LCS = "statusLCS"
    STATUS_LWSCS = "statusLWSCS"
    STATUS_MONCS = "statusMonCS"
    STATUS_RAD = "statusRAD"
    STATUS_THCS = "statusThCS"
    STOP_AZ = "stopAz"
    STOP_EL = "stopEl"
    STOP_LOUVERS = "stopLouvers"
    STOP_SHUTTER = "stopShutter"


class LlcName(enum.StrEnum):
    """LLC names."""

    AMCS = "AMCS"
    APSCS = "ApSCS"
    CBCS = "CBCS"
    CSCS = "CSCS"
    LCS = "LCS"
    LWSCS = "LWSCS"
    MONCS = "MonCS"
    OBC = "OBC"
    RAD = "RAD"
    THCS = "ThCS"


class ResponseCode(enum.IntEnum):
    """Response codes.

    The codes mean

        * 0, "OK", "Command received correctly and is being executed."
        * 1, "Not Connected", "The CSC is not connected to the fixed cRIO."
        * 2, "Unsupported", "A command was sent that is not supported by the
          lower level component, for instance park is sent to LCS or 'mooveAz'
          instead of 'moveAz' to AMCS."
        * 3, "Incorrect parameter(s)", "The command that was sent is supported
          by the lower level component but the parameters for the command are
          incorrect. This can mean not enough parameters, too many parameters
          or one or more parameters with the wrong name."
        * 4, "Incorrect source", "The current command source is not valid, e.g.
          a remote command arrives while the system is operated in local mode,
          like the push buttons for the Aperture Shutters."
        * 5, "Incorrect state", "The current command cannot be executed in
          current state, e.g. moveAz when the AMCS is in fault state."
        * 6, "Rotating part did not receive", "It was not possible to forward
          the command to the rotating part."
        * 7, "Rotating part did not reply", "The command was sent to the
          rotating part, but it did not send a reply before a timeout."
    """

    OK = 0
    NOT_CONNECTED = 1
    UNSUPPORTED = 2
    INCORRECT_PARAMETERS = 3
    INCORRECT_SOURCE = 4
    INCORRECT_STATE = 5
    ROTATING_PART_NOT_RECEIVED = 6
    ROTATING_PART_NOT_REPLIED = 7


class SlipRingState(enum.IntEnum):
    BELOW_LOW_LIMIT = enum.auto()
    OVER_LOW_LIMIT = enum.auto()
    COOLING_DOWN = enum.auto()


class ValidSimulationMode(enum.IntEnum):
    """Valid values for the simulation_mode attribute of the CSC."""

    NORMAL_OPERATIONS = 0
    SIMULATION_WITH_MOCK_CONTROLLER = 1
    SIMULATION_WITHOUT_MOCK_CONTROLLER = 2


# Lower Level Component states for which the brake is or brakes are engaged.
BRAKES_ENGAGED_STATES = [
    MotionState.ERROR,
    MotionState.BRAKES_ENGAGED,
    MotionState.GO_STATIONARY,
    MotionState.DISABLING_MOTOR_POWER,
    MotionState.MOTOR_POWER_OFF,
    MotionState.ENABLING_MOTOR_POWER,
    MotionState.MOTOR_POWER_ON,
    MotionState.GO_NORMAL,
    MotionState.GO_DEGRADED,
    MotionState.DISENGAGING_BRAKES,
    MotionState.STOPPING_MOTOR_COOLING,
    MotionState.MOTOR_COOLING_OFF,
    MotionState.PARKED,
    MotionState.INFLATING,
    MotionState.INFLATED,
    MotionState.STOPPED_BRAKED,
    MotionState.DEFLATING,
    MotionState.DEFLATED,
    MotionState.STARTING_MOTOR_COOLING,
    MotionState.MOTOR_COOLING_ON,
    MotionState.UNDETERMINED,
    MotionState.LP_ENGAGING,
    MotionState.LP_ENGAGED,
    MotionState.CLOSED,
    MotionState.OPEN,
    MotionState.LP_DISENGAGING,
    MotionState.LP_DISENGAGED,
    MotionState.BRAKE_ENGAGED,
    MotionState.VERTICAL,
    MotionState.INCLINED,
]

# Commands of the Lower Level Components on the rotating part of the dome.
CSCS_COMMANDS = [CommandName.STATUS_CSCS]
EL_COMMANDS = [
    CommandName.CRAWL_EL,
    CommandName.EXIT_FAULT_EL,
    CommandName.GO_STATIONARY_EL,
    CommandName.MOVE_EL,
    CommandName.SET_DEGRADED_EL,
    CommandName.SET_NORMAL_EL,
    CommandName.STATUS_LWSCS,
    CommandName.STOP_EL,
]
LOUVERS_COMMANDS = [
    CommandName.CLOSE_LOUVERS,
    CommandName.EXIT_FAULT_LOUVERS,
    CommandName.GO_STATIONARY_LOUVERS,
    CommandName.SET_DEGRADED_LOUVERS,
    CommandName.SET_LOUVERS,
    CommandName.SET_NORMAL_LOUVERS,
    CommandName.STATUS_LCS,
    CommandName.STOP_LOUVERS,
]
RAD_COMMANDS = [CommandName.STATUS_RAD]
SHUTTER_COMMANDS = [
    CommandName.CLOSE_SHUTTER,
    CommandName.EXIT_FAULT_SHUTTER,
    CommandName.GO_STATIONARY_SHUTTER,
    CommandName.HOME,
    CommandName.OPEN_SHUTTER,
    CommandName.RESET_DRIVES_SHUTTER,
    CommandName.SET_DEGRADED_SHUTTER,
    CommandName.SET_NORMAL_SHUTTER,
    CommandName.STATUS_APSCS,
    CommandName.STOP_SHUTTER,
]

# Dictionary to look up which LlcName is associated with which sub-system.
LlcNameDict = {getattr(SubSystemId, enum.name): enum.value for enum in LlcName}

# Custom types used for configurable maximum values.
MaxValueConfigType = dict[str, str | list[float]]
MaxValuesConfigType = list[MaxValueConfigType]

# Commands under power management.
POWER_MANAGEMENT_COMMANDS = [
    CommandName.CLOSE_LOUVERS,
    CommandName.CLOSE_SHUTTER,
    CommandName.CRAWL_EL,
    CommandName.FANS,
    CommandName.HOME,
    CommandName.MOVE_EL,
    CommandName.OPEN_SHUTTER,
    CommandName.SET_LOUVERS,
]


@dataclass(order=True)
class ScheduledCommand:
    """Class representing a scheduled command.

    A command needs to be scheduled in case the power draw by it would cause
    the total power draw on the rotating part of the dome to exceed the
    threshold value defined in `CONTINUOUS_SLIP_RING_POWER_CAPACITY`.

    Parameters
    ----------
    command : `CommandName`
        The command that may need to be scheduled.
    params : `dict`[`str`, `typing.Any`]
        The parameters for the command. Defaults to None.
    """

    command: CommandName
    params: dict[str, typing.Any]


@dataclass
class StopCommand:
    """Class representing a command to stop an ongoing motion.

    An ongoing motion may need to be stopped if the subsystem, represented by
    the LlcName, draws power so that issuing a higher priority command would
    push the power draw over the slip ring limit.

    Parameters
    ----------
    scheduled_command : `ScheduledCommand`
        The command and its parameters that will stop the ongoing motion.
    llc_name : `LlcName`
        The name of the subsystem, or Lower Level Component, that the stop
        command is issued for. This name is used to check if the subsystem
        currently draws power so that issuing a higher priority command would
        push the power draw over the slip ring limit.
    """

    scheduled_command: ScheduledCommand
    llc_name: LlcName


# Stop commands.
STOP_EL = StopCommand(
    ScheduledCommand(command=CommandName.STOP_EL, params={}),
    LlcName.LWSCS,
)
STOP_FANS = StopCommand(
    ScheduledCommand(command=CommandName.FANS, params={"action": OnOff.OFF}),
    LlcName.AMCS,
)
STOP_LOUVERS = StopCommand(
    ScheduledCommand(command=CommandName.STOP_LOUVERS, params={}),
    LlcName.LCS,
)
STOP_SHUTTER = StopCommand(
    ScheduledCommand(command=CommandName.STOP_SHUTTER, params={}),
    LlcName.APSCS,
)

# These LLCs are not controlled by the cRIO.
UNCONTROLLED_LLCS = [LlcName.RAD, LlcName.CSCS, LlcName.OBC]
