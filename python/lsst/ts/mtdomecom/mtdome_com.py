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

from __future__ import annotations

__all__ = ["COMMANDS_REPLIED_PERIOD", "CommandTime", "MTDomeCom"]

import asyncio
import logging
import math
import types
import typing
from dataclasses import dataclass
from types import SimpleNamespace

from lsst.ts import tcpip, utils
from lsst.ts.xml.enums.MTDome import (
    MotionState,
    OnOff,
    OperationalMode,
    PowerManagementMode,
    SubSystemId,
)

from .constants import (
    AMCS_NUM_MOTORS,
    APSCS_NUM_MOTORS_PER_SHUTTER,
    APSCS_NUM_SHUTTERS,
    DOME_AZIMUTH_OFFSET,
)
from .enums import (
    CommandName,
    LlcName,
    MaxValuesConfigType,
    ResponseCode,
    ScheduledCommand,
    ValidSimulationMode,
    motion_state_translations,
)
from .llc_configuration_limits import AmcsLimits, LwscsLimits
from .mock_controller import MockMTDomeController
from .power_management import (
    CONTINUOUS_ELECTRONICS_POWER_DRAW,
    CONTINUOUS_SLIP_RING_POWER_CAPACITY,
    FANS_POWER_DRAW,
    PowerManagementHandler,
    command_priorities,
)

# Timeout [sec] used when creating a Client, a mock controller or when waiting
# for a reply when sending a command to the controller.
_TIMEOUT = 20

# Polling period [sec] for the task that checks if all commands have been
# replied to.
COMMANDS_REPLIED_PERIOD = 600

# These next commands are temporarily disabled in simulation mode 0 because
# they will be issued during the upcoming TMA pointing test and the EIE LabVIEW
# code doesn't handle them yet, which will result in an error. As soon as the
# TMA pointing test is done, they will be reenabled. The name reflects the fact
# that there probably will be more situations during commissioning in which
# commands need to be disabled.
COMMANDS_DISABLED_FOR_COMMISSIONING = {
    CommandName.CLOSE_LOUVERS,
    CommandName.CRAWL_EL,
    CommandName.FANS,
    CommandName.GO_STATIONARY_EL,
    CommandName.GO_STATIONARY_LOUVERS,
    CommandName.INFLATE,
    CommandName.MOVE_EL,
    CommandName.SET_LOUVERS,
    CommandName.SET_TEMPERATURE,
    CommandName.STOP_EL,
    CommandName.STOP_LOUVERS,
}
REPLY_DATA_FOR_DISABLED_COMMANDS = {"response": 0, "timeout": 0}

ALL_OPERATIONAL_MODE_COMMANDS = {
    SubSystemId.AMCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_AZ,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_AZ,
    },
    SubSystemId.LWSCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_EL,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_EL,
    },
    SubSystemId.APSCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_SHUTTER,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_SHUTTER,
    },
    SubSystemId.LCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_LOUVERS,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_LOUVERS,
    },
    SubSystemId.MONCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_MONITORING,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_MONITORING,
    },
    SubSystemId.THCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_THERMAL,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_THERMAL,
    },
}

OPERATIONAL_MODE_COMMANDS_FOR_COMMISSIONING = {
    SubSystemId.AMCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_AZ,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_AZ,
    },
    SubSystemId.APSCS: {
        OperationalMode.NORMAL.name: CommandName.SET_NORMAL_SHUTTER,
        OperationalMode.DEGRADED.name: CommandName.SET_DEGRADED_SHUTTER,
    },
}

# The values of these keys need to be compensated for the dome azimuth offset
# in the AMCS status. Note that these keys are shared with LWSCS so they can be
# added to _KEYS_IN_RADIANS to avoid duplication but this also means that an
# additional check for the AMCS lower level component needs to be done when
# applying the offset correction. That is a trade-off I can live with.
_AMCS_KEYS_OFFSET = {
    "positionActual",
    "positionCommanded",
}
# The values of these keys need to be converted from radians to degrees when
# the status is recevied and telemetry with these values is sent.
_KEYS_IN_RADIANS = {
    "velocityActual",
    "velocityCommanded",
}.union(_AMCS_KEYS_OFFSET)

_KEYS_TO_ROUND = {
    LlcName.APSCS.value: {
        "positionActual": 2,
    }
}

# Polling periods [sec] for the lower level components.
_STATUS_POKE_PERIOD = 0.1

# Use the _STATUS_POKE_PERIOD as the unit for the following poking periods.
_STATUS_POKE_PERIODS = {
    LlcName.AMCS: 2,
    LlcName.APSCS: 5,
    LlcName.CBCS: 5,
    LlcName.CSCS: 5,
    LlcName.LCS: 5,
    LlcName.LWSCS: 5,
    LlcName.MONCS: 5,
    LlcName.RAD: 5,
    LlcName.THCS: 5,
}

# Polling period [sec] for the task that checks if any commands are waiting to
# be issued.
_COMMAND_QUEUE_PERIOD = 1.0

# Interval to sleep [sec] while running periodic tasks.
SLEEP_INTERVAL = 1.0


@dataclass
class CommandTime:
    """Class representing the TAI time at which a command was issued.

    Attributes
    ----------
    command : `CommandName`
        The command issued.
    tai : `float`
        TAI time as unix seconds, e.g. the time returned by CLOCK_TAI
        on linux systems.
    """

    command: CommandName
    tai: float


# TODO OSW-862 Remove all references to the old temperature schema.
class MTDomeCom:
    """TCP/IP interface to the MTDome controller.

    Parameters
    ----------
    log : `logging.Logger`
        Logger for which a child logger is created.
    config : `SimpleNameSpace`
        The configuration to use. This should contain the host name and port to
        connect to.
    simulation_mode : `ValidSimulationMode`
        The simulation mode to use. Defaults to `NORMAL_OPERATIONS`.
    telemetry_callbacks : `dict`[`LlcName`, `typing.Callable`]
        List of telemetry callback coroutines to use. Defaults to `None`.
    start_periodic_tasks : `bool`
        Start the periodic tasks or not. Defaults to `True`. Unit tests may set
        this to `False`.
    communication_error : `bool`
        Is there a communication error with the rotating part (True) or not
        (False)? This is for unit tests only. The default is False.
    timeout_error : `bool`
        Do command replies timeout of not? The default is False.
    new_thermal_schema : `bool`
        Is the new thermal schema used (True) or not (False, the default).
        If True, the temperature values only occur in the ThCS telemetry and
        are split over their repspective items. If False, all temperatures are
        reported in one item in both AMCS and ThCS telemetry. This is only
        used by the mock controller.
    """

    _index_iter = utils.index_generator()

    def __init__(
        self,
        log: logging.Logger,
        config: SimpleNamespace,
        simulation_mode: ValidSimulationMode = ValidSimulationMode.NORMAL_OPERATIONS,
        telemetry_callbacks: (
            dict[LlcName, typing.Callable[[dict[str, typing.Any]], None]] | None
        ) = None,
        start_periodic_tasks: bool = True,
        communication_error: bool = False,
        timeout_error: bool = False,
        new_thermal_schema: bool = False,
    ) -> None:
        self.client: tcpip.Client | None = None
        self.log = log.getChild(type(self).__name__)
        self.config = config
        self.simulation_mode = simulation_mode
        self.start_periodic_tasks = start_periodic_tasks

        # Initialize telemetry_callbacks to an empty dict if None.
        self.telemetry_callbacks = telemetry_callbacks or {}

        # Mock controller, or None if not constructed
        self.mock_ctrl: MockMTDomeController | None = None
        # Mock a communication error (True) or not (False). To be set by unit
        # tests only.
        self.communication_error = communication_error
        # Mock a timeout error (True) or not (False). To be set by unit
        # tests only.
        self.timeout_error = timeout_error

        # Is the new temperature schema used or not?
        self.new_thermal_schema = new_thermal_schema

        # Keep the lower level statuses in memory for unit tests.
        self.lower_level_status: dict[LlcName, typing.Any] = {}
        # Keep track of the latest communication error report.
        self.communication_error_report: dict[str, typing.Any] = {}

        # List of periodic tasks to start.
        self.periodic_tasks: list[asyncio.Future] = []
        self.run_periodic_tasks = False

        # Keep a lock so only one remote command can be executed at a time.
        self.communication_lock = asyncio.Lock()

        # Lock to issue the non-status command
        self._non_status_command_lock = asyncio.Lock()
        self._has_non_status_command = False

        # All status commands.
        self._status_methods = {
            LlcName.AMCS: self.status_amcs,
            LlcName.APSCS: self.status_apscs,
            LlcName.CBCS: self.status_cbcs,
            LlcName.CSCS: self.status_cscs,
            LlcName.LCS: self.status_lcs,
            LlcName.LWSCS: self.status_lwscs,
            LlcName.MONCS: self.status_moncs,
            LlcName.RAD: self.status_rad,
            LlcName.THCS: self.status_thcs,
        }

        # Status command counts information. This holds the amount of times a
        # status command has been executed for all LlcNames for which the
        # status commands need to be executed.
        self._status_command_counts: dict = {}

        self.amcs_limits = AmcsLimits()
        self.lwscs_limits = LwscsLimits()

        # Keep track of which stop function to call for which SubSystemId
        self.stop_function_dict = {
            SubSystemId.AMCS: self.stop_az,
            SubSystemId.LWSCS: self.stop_el,
            SubSystemId.APSCS: self.stop_shutter,
            SubSystemId.LCS: self.stop_louvers,
        }

        # Keep track of which command to send to set the operational mode on a
        # lower level component.
        self.operational_mode_command_dict = ALL_OPERATIONAL_MODE_COMMANDS
        if self.simulation_mode == ValidSimulationMode.NORMAL_OPERATIONS:
            self.operational_mode_command_dict = (
                OPERATIONAL_MODE_COMMANDS_FOR_COMMISSIONING
            )

        # Keep track of which command to send the home command on a lower level
        # component.
        self.set_home_command_dict = {
            SubSystemId.APSCS: CommandName.HOME,
        }

        # Keep track of the commands that have been sent and that haven't been
        # replied to yet. The key of the dict is the commandId for the commands
        # that have been sent.
        self.commands_without_reply: dict[int, CommandTime] = {}

        # Power management attributes.
        self.power_management_mode = PowerManagementMode.NO_POWER_MANAGEMENT
        self.power_management_handler = PowerManagementHandler(
            self.log, command_priorities
        )

        self.log.info("MTDomeCom constructed.")

    @property
    def connected(self) -> bool:
        return self.client is not None and self.client.connected

    async def connect(self) -> None:
        """Connect to the dome controller's TCP/IP port.

        Start the mock controller, if simulating.
        """
        self.log.info("connect")
        self.log.info(self.config)
        self.log.info(f"self.simulation_mode = {self.simulation_mode}.")
        if self.config is None:
            raise RuntimeError("Not yet configured.")
        if self.connected:
            raise RuntimeError("Already connected.")
        if self.simulation_mode == ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER:
            await self._start_mock_ctrl()
            assert self.mock_ctrl is not None
            host = self.mock_ctrl.host
            port = self.mock_ctrl.port
        elif (
            self.simulation_mode
            == ValidSimulationMode.SIMULATION_WITHOUT_MOCK_CONTROLLER
        ):
            host = tcpip.DEFAULT_LOCALHOST
            port = self.config.port
        else:
            host = self.config.host
            port = self.config.port

        self.log.info(f"Connecting to host={host} and port={port}.")
        self.client = tcpip.Client(
            host=host, port=port, log=self.log, name="MTDomeClient"
        )
        await asyncio.wait_for(fut=self.client.start_task, timeout=_TIMEOUT)

        if self.start_periodic_tasks:
            await self._start_periodic_tasks()

        self.log.info("connected")

    async def disconnect(self) -> None:
        """Disconnect from the TCP/IP controller, if connected, and stop the
        mock controller, if running.
        """
        self.log.info("disconnect.")

        if self.connected:
            # Stop all periodic tasks, including polling for the status of the
            # lower level components.
            await self._cancel_periodic_tasks()

            assert self.client is not None
            await self.client.close()
            self.client = None
        if self.simulation_mode == ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER:
            await self._stop_mock_ctrl()

    async def _start_periodic_tasks(self) -> None:
        """Start all periodic tasks."""
        await self._cancel_periodic_tasks()

        for llc_name in LlcName:
            # Only request the LLC status if the corresponding callback exists.
            # This is necessary because some telemetry commands time out and
            # slow down operating the dome. The unsupported callbacks should
            # not be included.
            if llc_name in self.telemetry_callbacks:
                self._status_command_counts[llc_name] = 0

        self.run_periodic_tasks = True
        self.periodic_tasks.append(
            asyncio.create_task(
                self.one_periodic_task(
                    self.query_status,
                    _STATUS_POKE_PERIOD,
                    wrap_with_async_task=False,
                ),
                name="query_status",
            )
        )

        self.periodic_tasks.append(
            asyncio.create_task(
                self.one_periodic_task(
                    self.check_all_commands_have_replies, COMMANDS_REPLIED_PERIOD
                ),
                name="check_all_commands_have_replies",
            )
        )

        self.periodic_tasks.append(
            asyncio.create_task(
                self.one_periodic_task(
                    self.process_command_queue, _COMMAND_QUEUE_PERIOD
                ),
                name="process_command_queue",
            )
        )

    async def query_status(self) -> None:
        """Query the status of all lower level components."""

        for llc_name in self._status_command_counts:
            # Return immediately if we have the non-status command to process.
            if await self.has_non_status_command():
                return

            # Update the counts for the status commands.
            self._status_command_counts[llc_name] += 1

            # Execute the command if the count is greater than the max count.
            if self._status_command_counts[llc_name] >= _STATUS_POKE_PERIODS[llc_name]:
                # Reset the count.
                self._status_command_counts[llc_name] = 0

                # Execute the command.
                try:
                    await self._status_methods[llc_name]()
                except Exception:
                    self.log.exception(
                        f"Failed to get the status for {llc_name}. Ignoring."
                    )

    async def one_periodic_task(
        self,
        method: typing.Callable,
        interval: float,
        wrap_with_async_task: bool = True,
    ) -> None:
        """Run one method forever at the specified interval.

        Parameters
        ----------
        method : `typing.Callable`
            The periodic method to run.
        interval : `float`
            The interval (sec) at which to run the status method.
        wrap_with_async_task : `bool`, optional
            Wrap the method in an asyncio task or not. Defaults to `True`.
        """
        self.log.debug(f"Starting periodic task {method=} with {interval=}")
        try:
            background_tasks = set()
            while self.run_periodic_tasks:
                if wrap_with_async_task:
                    task = asyncio.create_task(method())
                    background_tasks.add(task)

                    task.add_done_callback(background_tasks.discard)
                else:
                    await method()

                # Don't sleep long intervals but instead break up in small
                # steps so it can be interrupted if necessary.
                interval_slept = 0.0
                while interval_slept < interval and self.run_periodic_tasks:
                    await asyncio.sleep(_STATUS_POKE_PERIOD)
                    interval_slept += _STATUS_POKE_PERIOD
        except asyncio.CancelledError:
            # Ignore task cancellation.
            self.log.warning(f"one_periodic_task({method}) has been cancelled.")
        except BaseException as e:
            self.log.exception(f"one_periodic_task({method}) has stopped.")
            raise e

    async def _cancel_periodic_tasks(self) -> None:
        """Cancel all periodic tasks."""
        self.run_periodic_tasks = False
        while self.periodic_tasks:
            periodic_task: asyncio.Future = self.periodic_tasks.pop()
            self.log.debug(f"Waiting for periodic task {periodic_task=!r} to be done.")
            try:
                async with asyncio.timeout(_TIMEOUT):
                    # Need to cancel the task here because waiting for it to
                    # stop by itself may take a long time in case of network
                    # or connection issues.
                    periodic_task.cancel()
            except TimeoutError:
                self.log.debug(f"Canceling periodic task {periodic_task=!r}.")
                periodic_task.cancel()
                await periodic_task

    async def _start_mock_ctrl(self) -> None:
        """Start the mock controller.

        The simulation mode must be 1.
        """
        self.log.info("start_mock_ctrl.")
        assert (
            self.simulation_mode
            == ValidSimulationMode.SIMULATION_WITH_MOCK_CONTROLLER.value
        )
        self.mock_ctrl = MockMTDomeController(
            port=0,
            log=self.log,
            communication_error=self.communication_error,
            timeout_error=self.timeout_error,
            new_thermal_schema=self.new_thermal_schema,
        )
        await asyncio.wait_for(self.mock_ctrl.start(), timeout=_TIMEOUT)

    async def _stop_mock_ctrl(self) -> None:
        """Stop the mock controller, if running."""
        self.log.info("stop_mock_ctrl")
        mock_ctrl = self.mock_ctrl
        self.mock_ctrl = None
        if mock_ctrl:
            await mock_ctrl.close()

    async def _schedule_command_if_power_management_active(
        self, command: CommandName, **params: typing.Any
    ) -> None:
        """Schedule the provided command if power management is active.

        If power management is not active then the command is executed
        immediately.

        Parameters
        ----------
        command : `CommandName`
            The command to schedule or execute immediately.
        params : `typing.Any`
            The parameters to pass along with the command. This may be empty.
        """
        # All commands, that help reduce the power draw, are scheduled. It is
        # up to the dome lower level control system to execute them or not.
        if self.power_management_mode == PowerManagementMode.NO_POWER_MANAGEMENT:
            await self.update_status_of_non_status_command(True)
            await self.write_then_read_reply(command=command, **params)
        else:
            scheduled_command = ScheduledCommand(command=command, params=params)
            await self.power_management_handler.schedule_command(scheduled_command)

    async def update_status_of_non_status_command(self, status: bool) -> None:
        """Update the status of the non-status command.

        Parameters
        ----------
        status : `bool`
            Set True if running a non-status command. After it is done, set
            False.
        """

        async with self._non_status_command_lock:
            self._has_non_status_command = status

    async def process_command_queue(self) -> None:
        """Process the commands in the queue, if there are any.

        Depending on the power management state, certain commands take
        precedence over others. Whether a command actually can be issued
        depends on the expected power draw for the command and the available
        power for the rotating part of the dome. If a command can be issued
        then it is removed from the queue, otherwise not.
        """

        if self.power_management_mode == PowerManagementMode.NO_POWER_MANAGEMENT:
            # This is only needed if the dome power management is active.
            return

        current_power_draw = await self._get_current_power_draw_for_llcs()
        total_current_power_draw = sum([p for k, p in current_power_draw.items()])
        power_available = (
            CONTINUOUS_SLIP_RING_POWER_CAPACITY
            - CONTINUOUS_ELECTRONICS_POWER_DRAW
            - total_current_power_draw
        )
        self.log.debug(f"{current_power_draw=}, {power_available=}")

        scheduled_command = await self.power_management_handler.get_next_command(
            current_power_draw
        )
        if scheduled_command is not None:
            await self.update_status_of_non_status_command(True)
            await self.write_then_read_reply(
                command=scheduled_command.command, **scheduled_command.params
            )

    async def _get_current_power_draw_for_llcs(self) -> dict[str, float]:
        """Determine the current power draw for each subsystem based on the
        telemetry sent by them.

        In case of AMCS, the power draw of interest is the one of the fans
        because that's the only one that contributes to the power draw of the
        slip ring.

        Returns
        -------
        dict[str, float]
            A dict with the subsystem names as keys and their power draw as
            values.
        """
        current_power_draw: dict[str, float] = {}
        for llc_name in self.lower_level_status:
            llc_status = self.lower_level_status[llc_name]
            if llc_name == LlcName.AMCS:
                # AMCS doesn't contribute to total power draw, except the fans.
                if llc_status["status"]["fans"]:
                    current_power_draw[llc_name] = FANS_POWER_DRAW
                else:
                    current_power_draw[llc_name] = 0.0
            else:
                if "powerDraw" in llc_status:
                    current_power_draw[llc_name] = llc_status["powerDraw"]
        return current_power_draw

    async def write_then_read_reply(
        self, command: CommandName, **params: typing.Any
    ) -> dict[str, typing.Any]:
        """Write the cmd string and then read the reply to the command.

        Notes
        -----
        For the function that calls this method, it might need to call the
        self.update_status_of_non_status_command() first and set the argument
        to be True if it is a non-status command. Otherwise, the continuous
        status commands in self.query_status() will block this in the TCP/IP
        pipe.

        Parameters
        ----------
        command : `CommandName`
            The command to write.
        **params : `typing.Any`
            The parameters for the command. This may be empty.

        Returns
        -------
        data : `dict`
            A dict of the form {"response": ResponseCode, "timeout":
            TimeoutValue} where "response" can be zero for "OK" or non-zero
            for any other situation.

        Raises
        ------
        TimeoutError
            If waiting for a command reply takes longer than _TIMEOUT seconds.
        """
        command_id = next(self._index_iter)
        self.commands_without_reply[command_id] = CommandTime(
            command=command, tai=utils.current_tai()
        )
        command_name = command.value
        command_dict = {
            "commandId": command_id,
            "command": command_name,
            "parameters": params,
        }
        async with self.communication_lock:
            # For the non-status command, reset the flag.
            if not command_name.startswith("status"):
                if await self.has_non_status_command():
                    await self.update_status_of_non_status_command(False)

            if self.client is None:
                raise RuntimeError(
                    f"Error writing command {command_dict}: self.client == None."
                )

            disabled_commands: set[CommandName] = set()
            if self.simulation_mode == ValidSimulationMode.NORMAL_OPERATIONS:
                disabled_commands = COMMANDS_DISABLED_FOR_COMMISSIONING

            if command not in disabled_commands:
                self.log.debug(f"Sending {command_dict=}.")
                await self.client.write_json(data=command_dict)
                try:
                    async with asyncio.timeout(_TIMEOUT):
                        data = await self.client.read_json()
                except TimeoutError as exc:
                    self.communication_error_report = {
                        "command_name": CommandName(command_name),
                        "exception": exc,
                        "response_code": ResponseCode.UNSUPPORTED,
                    }
                    raise exc
                except asyncio.CancelledError:
                    # Ignore task cancellation.
                    self.log.warning(
                        f"Waiting for reply to {command_name} was cancelled."
                    )
                    data = REPLY_DATA_FOR_DISABLED_COMMANDS
                self.log.debug(f"Received {command_name=}, {data=}.")

                if "commandId" not in data:
                    self.log.error(f"No 'commandId' in reply for {command_name=}")
                else:
                    received_command_id = data["commandId"]
                    if received_command_id in self.commands_without_reply:
                        self.commands_without_reply.pop(received_command_id)
                    else:
                        self.log.warning(
                            f"Ignoring unknown commandId {received_command_id}."
                        )
            else:
                data = REPLY_DATA_FOR_DISABLED_COMMANDS
            response = data["response"]

            if response != ResponseCode.OK:
                error_suffix = {
                    ResponseCode.INCORRECT_PARAMETERS: "has incorrect parameters.",
                    ResponseCode.INCORRECT_SOURCE: "was sent from an incorrect source.",
                    ResponseCode.INCORRECT_STATE: "was sent for an incorrect state.",
                    ResponseCode.ROTATING_PART_NOT_RECEIVED: "was not received by the rotating part.",
                    ResponseCode.ROTATING_PART_NOT_REPLIED: "was not replied to by the rotating part.",
                }.get(response, "is not supported.")
                message = f"Command {command_name} {error_suffix}"
                self.log.debug(f"{message} -> {command_name=}, {data=}")
                exception = ValueError(message)
                self.communication_error_report = {
                    "command_name": CommandName(command_name),
                    "exception": exception,
                    "response_code": ResponseCode(response),
                }
                raise exception
            else:
                self.communication_error_report = {}

            return data

    async def has_non_status_command(self) -> bool:
        """Check if a non-status command is running.

        Returns
        -------
        status : `bool`
            True if a non-status command is running, False otherwise.
        """

        async with self._non_status_command_lock:
            return self._has_non_status_command

    async def move_az(self, position: float, velocity: float) -> None:
        """Move AZ.

        Parameters
        ----------
        position : `float`
            The current azimuth position of the target [deg].
        velocity : `float`
            The velocity of the target [deg/s].

        Notes
        -----
        The AMCS expects the position in radians and the velocity in radians/s.
        On top of that, the AMCS internal angle is offset by about 32 degrees
        east with respect to 0 degrees azimuth. This method takes care of the
        offset and the conversion to radians.
        """
        self.log.debug(f"move_az: {position=!s}, {velocity=!s}")
        # Compensate for the dome azimuth offset.
        dome_position = utils.angle_wrap_nonnegative(
            position + DOME_AZIMUTH_OFFSET
        ).degree
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.MOVE_AZ,
            position=math.radians(dome_position),
            velocity=math.radians(velocity),
        )

    async def move_el(self, position: float) -> None:
        """Move El.

        Parameters
        ----------
        position : `float`
            The elevation position of the target [deg].

        Notes
        -----
        The LWSCS expects the position in radians. This method takes care of
        the conversion to radians.
        """
        self.log.debug(f"move_el: {position=!s}")
        await self._schedule_command_if_power_management_active(
            command=CommandName.MOVE_EL, position=math.radians(position)
        )

    async def stop_az(self, engage_brakes: bool) -> None:
        """Stop AZ motion and engage the brakes if indicated. Also
        disengage the locking pins if engaged.

        Parameters
        ----------
        engage_brakes : bool
            Engage the brakes (true) or not (false).
        """
        self.log.debug(f"stop_az: {engage_brakes=!s}")
        await self.update_status_of_non_status_command(True)
        if engage_brakes:
            await self.write_then_read_reply(command=CommandName.GO_STATIONARY_AZ)
        else:
            await self.write_then_read_reply(command=CommandName.STOP_AZ)

    async def stop_el(self, engage_brakes: bool) -> None:
        """Stop EL motion and engage the brakes if indicated. Also
        disengage the locking pins if engaged.

        Parameters
        ----------
        engage_brakes : bool
            Engage the brakes (true) or not (false).
        """
        self.log.debug(f"stop_el: {engage_brakes=!s}")
        await self.update_status_of_non_status_command(True)
        if engage_brakes:
            await self.write_then_read_reply(command=CommandName.GO_STATIONARY_EL)
        else:
            await self.write_then_read_reply(command=CommandName.STOP_EL)

    async def stop_louvers(self, engage_brakes: bool) -> None:
        """Stop Louvers motion and engage the brakes if indicated.
        Also disengage the locking pins if engaged.

        Parameters
        ----------
        engage_brakes : bool
            Engage the brakes (true) or not (false).
        """
        self.log.debug(f"stop_louvers: {engage_brakes=!s}")
        await self.update_status_of_non_status_command(True)
        if engage_brakes:
            await self.write_then_read_reply(command=CommandName.GO_STATIONARY_LOUVERS)
        else:
            await self.write_then_read_reply(command=CommandName.STOP_LOUVERS)

    async def stop_shutter(self, engage_brakes: bool) -> None:
        """Stop Shutter motion and engage the brakes if indicated.
        Also disengage the locking pins if engaged.

        Parameters
        ----------
        engage_brakes : bool
            Engage the brakes (true) or not (false).
        """
        self.log.debug(f"stop_shutter: {engage_brakes=!s}")
        await self.update_status_of_non_status_command(True)
        if engage_brakes:
            await self.write_then_read_reply(command=CommandName.GO_STATIONARY_SHUTTER)
        else:
            await self.write_then_read_reply(command=CommandName.STOP_SHUTTER)

    async def stop_sub_systems(self, sub_system_ids: int, engage_brakes: bool) -> None:
        """Stop all motion and engage the brakes if indicated in the data.
        Also disengage the locking pins if engaged.

        Parameters
        ----------
        sub_system_ids : `int`
            Bitmask of the sub-systems to stop.
        engage_brakes : `bool`
            Engage the brakes (True) or not (False).
        """
        for sub_system_id in SubSystemId:
            # Do not nest these two if statements, otherwise a warning will be
            # logged for each SubsystemId that is not in data.subSystemIds.
            if sub_system_id & sub_system_ids:
                if sub_system_id in self.stop_function_dict:
                    func = self.stop_function_dict[sub_system_id]
                    await func(engage_brakes)
                else:
                    self.log.warning(
                        f"Subsystem {SubSystemId(sub_system_id).name} doesn't have a "
                        "stop function. Ignoring."
                    )

    async def crawl_az(self, velocity: float) -> None:
        """Crawl AZ.

        Parameters
        ----------
        velocity : `float`
            The velocity of the target [deg/s].

        Notes
        -----
        The AMCS expects the velocity in radians/sec. This method takes
        care the conversion to radians.
        """
        self.log.debug(f"crawl_az: {velocity=!s}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.CRAWL_AZ, velocity=math.radians(velocity)
        )

    async def crawl_el(self, velocity: float) -> None:
        """Crawl El.

        Parameters
        ----------
        velocity : `float`
            The velocity of the target [deg/s].

        Notes
        -----
        The LWSCS expects the velocity in radians/sec. This method takes
        care the conversion to radians.
        """
        self.log.debug(f"crawl_el: {velocity=!s}")
        await self._schedule_command_if_power_management_active(
            command=CommandName.CRAWL_EL, velocity=math.radians(velocity)
        )

    async def set_louvers(self, position: list[float]) -> None:
        """Set the positions of the louvers.

        Parameters
        ----------
        position: array of float
            An array of positions, in percentage with 0 meaning closed and 100
            fully open, for each louver. A position of -1 means "do not move".
        """
        self.log.debug(f"set_louvers: {position=!s}")
        await self._schedule_command_if_power_management_active(
            command=CommandName.SET_LOUVERS, position=position
        )

    async def close_louvers(self) -> None:
        """Close all louvers."""
        self.log.debug("close_louvers")
        await self._schedule_command_if_power_management_active(
            command=CommandName.CLOSE_LOUVERS
        )

    async def open_shutter(self) -> None:
        """Open the shutter."""
        self.log.debug("open_shutter")
        await self._schedule_command_if_power_management_active(
            command=CommandName.OPEN_SHUTTER
        )

    async def close_shutter(self) -> None:
        """Close the shutter."""
        self.log.debug("close_shutter")
        await self._schedule_command_if_power_management_active(
            command=CommandName.CLOSE_SHUTTER
        )

    async def park(self) -> None:
        """Park the dome."""
        self.log.debug("park")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.PARK)

    async def set_temperature(self, temperature: float) -> None:
        """Set the preferred temperature in the dome.

        Parameters
        ----------
        temperature: `float`
            The temperature, in degrees Celsius, to set.
        """
        self.log.debug(f"set_temperature: {temperature=!s}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.SET_TEMPERATURE, temperature=temperature
        )

    async def exit_fault(self, sub_system_ids: int) -> None:
        """Indicate that all hardware errors have been resolved.

        Parameters
        ----------
        sub_system_ids : `int`
            Bitmask of the sub-systems to exit fault for.
        """
        for sub_system_id in SubSystemId:
            if sub_system_id & sub_system_ids:
                match sub_system_id:
                    case SubSystemId.AMCS:
                        await self.exit_fault_az()
                    case SubSystemId.APSCS:
                        await self.exit_fault_shutter()
                    case SubSystemId.LCS:
                        await self.exit_fault_louvers()
                    case SubSystemId.LWSCS:
                        await self.exit_fault_el()
                    case SubSystemId.THCS:
                        await self.exit_fault_thermal()
                    case _:
                        self.log.warning(
                            f"Ignoring reset_drives for sub_system_id={sub_system_id.name}."
                        )

    async def exit_fault_az(self) -> None:
        """Indicate that all AMCS hardware errors have been resolved."""
        # To help the operators minimize the amount of commands to send, we
        # always send resetDrives commands.
        az_reset = [1] * AMCS_NUM_MOTORS
        self.log.debug(f"reset_drives_az: {az_reset=!s}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.RESET_DRIVES_AZ, reset=az_reset
        )
        self.log.debug("exit_fault_az")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.EXIT_FAULT_AZ)

    async def exit_fault_shutter(self) -> None:
        """Indicate that all ApSCS hardware errors have been resolved."""
        # To help the operators minimize the amount of commands to send, we
        # always send resetDrives commands.
        aps_reset = [1] * APSCS_NUM_SHUTTERS * APSCS_NUM_MOTORS_PER_SHUTTER
        self.log.debug(f"reset_drives_shutter: {aps_reset=!s}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.RESET_DRIVES_SHUTTER,
            reset=aps_reset,
        )
        self.log.debug("exit_fault_shutter")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.EXIT_FAULT_SHUTTER)

    async def exit_fault_louvers(self) -> None:
        """Indicate that all LCS hardware errors have been resolved."""
        self.log.debug("exit_fault_louvers")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.EXIT_FAULT_LOUVERS)

    async def exit_fault_el(self) -> None:
        """Indicate that all LWSCS hardware errors have been resolved."""
        self.log.debug("exit_fault_el")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.EXIT_FAULT_EL)

    async def exit_fault_thermal(self) -> None:
        """Indicate that all ThCS hardware errors have been resolved."""
        self.log.debug("exit_fault_th")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.EXIT_FAULT_THERMAL)

    async def set_operational_mode(
        self,
        operational_mode: OperationalMode,
        sub_system_ids: int,
    ) -> None:
        """Indicate that one or more sub_systems need to operate in degraded or
        normal state.

        Parameters
        ----------
        operational_mode : `OperationalMode`
            The operaitonal mode to set.
        sub_system_ids : `int`
            Bitmask of the sub-systems to set the operational mode for.
        """
        self.log.debug("set_operational_mode")
        for sub_system_id in SubSystemId:
            if (
                sub_system_id & sub_system_ids
                and sub_system_id in self.operational_mode_command_dict
                and operational_mode.name
                in self.operational_mode_command_dict[sub_system_id]
            ):
                self.log.debug(
                    f"do_setOperationalMode: sub_system_id={sub_system_id.name}"
                )
                command = self.operational_mode_command_dict[sub_system_id][
                    operational_mode.name
                ]
                await self.update_status_of_non_status_command(True)
                await self.write_then_read_reply(command=command)

    async def reset_drives_az(self, reset: list[int]) -> None:
        """Reset one or more AZ drives.

        This is necessary when exiting from FAULT state without going to
        Degraded Mode since the drives don't reset themselves.

        Parameters
        ----------
        reset : `list`[`int`]
            List of indices of the motors to reset.
        """
        self.log.debug(f"reset_drives_az: {reset=}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.RESET_DRIVES_AZ, reset=reset
        )

    async def reset_drives_shutter(self, reset: list[int]) -> None:
        """Reset one or more Aperture Shutter drives.

        This is necessary when exiting from FAULT state without going to
        Degraded Mode since the drives don't reset themselves.

        Parameters
        ----------
        reset : `list`[`int`]
            List of indices of the motors to reset.
        """
        self.log.debug(f"reset_drives_shutter: reset={reset}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.RESET_DRIVES_SHUTTER, reset=reset
        )

    async def set_zero_az(self) -> None:
        """Take the current position of the dome as zero.

        This is necessary as long as the racks and pinions on the drives have
        not been installed yet to compensate for slippage of the drives.
        """
        self.log.debug("set_zero_az")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.SET_ZERO_AZ)

    async def home(self, sub_system_ids: int) -> None:
        """Search the home position of the Aperture Shutter, which is the
        closed position.

        This is necessary in case the ApSCS (Aperture Shutter Control system)
        was shutdown with the Aperture Shutter not fully open or fully closed.

        Parameters
        ----------
        sub_system_ids : int
            Bitmask of the sub-systems to home.
        """
        for sub_system_id in SubSystemId:
            self.log.debug(f"home: sub_system_id={sub_system_id.name}")
            if (
                sub_system_id & sub_system_ids
                and sub_system_id in self.set_home_command_dict
            ):
                command = self.set_home_command_dict[sub_system_id]
                await self._schedule_command_if_power_management_active(command=command)

    async def config_llcs(self, system: LlcName, settings: MaxValuesConfigType) -> None:
        """Config command not to be executed by SAL.

        This command will be used to send the values of one or more parameters
        to configure the lower level components.

        Parameters
        ----------
        system: `LlcName`
            The name of the lower level component to configure.
        settings : `dict`
            A dict containing key,value for all the parameters that need to be
            configured. The structure is::

                "jmax"
                "amax"
                "vmax"

        """
        self.log.debug(f"config_llcs: {settings=}")
        if system == LlcName.AMCS:
            validated_settings = self.amcs_limits.validate(settings)
        elif system == LlcName.LWSCS:
            validated_settings = self.lwscs_limits.validate(settings)
        else:
            raise ValueError(f"Encountered unsupported {system=!s}")

        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.CONFIG, system=system, settings=validated_settings
        )

    async def restore_llcs(self) -> None:
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(command=CommandName.RESTORE)

    async def fans(self, speed: float) -> None:
        """Set the speed of the fans.

        Parameters
        ----------
        speed : `float`
            The speed to set.
        """
        self.log.debug(f"fans: {speed=!s}")
        await self._schedule_command_if_power_management_active(
            command=CommandName.FANS, speed=speed
        )

    async def inflate(self, action: OnOff) -> None:
        """Inflate or deflate the inflatable seal.

        Parameters
        ----------
        action : `OnOff`
            The action to perform.
        """
        self.log.debug(f"inflate: {action=!s}")
        await self.update_status_of_non_status_command(True)
        await self.write_then_read_reply(
            command=CommandName.INFLATE, action=action.value
        )

    async def set_power_management_mode(
        self, power_management_mode: PowerManagementMode
    ) -> None:
        """Set the power management mode.

        Parameters
        ----------
        power_management_mode : `PowerManagementMode`
            The power management mode to set.
        """
        if power_management_mode == PowerManagementMode.NO_POWER_MANAGEMENT:
            self.log.warning("Will not set PowerManagementMode to NO_POWER_MANAGEMENT.")

        elif power_management_mode == self.power_management_mode:
            self.log.warning(
                "New PowerManagementMode is equal to current mode. Ignoring."
            )

        else:
            self.log.debug(
                f"setPowerManagementMode: {power_management_mode}. Clearing command queue."
            )
            while not self.power_management_handler.command_queue.empty():
                self.power_management_handler.command_queue.get_nowait()
            self.power_management_mode = power_management_mode

    def _translate_motion_state_if_necessary(self, state: str) -> MotionState:
        try:
            motion_state = MotionState[state]
        except KeyError:
            motion_state = motion_state_translations[state]
        return motion_state

    async def status_amcs(self) -> None:
        """AMCS status command."""
        await self.request_llc_status(LlcName.AMCS)

    async def status_apscs(self) -> None:
        """ApSCS status command."""
        await self.request_llc_status(LlcName.APSCS)

    async def status_cbcs(self) -> None:
        """CBCS status command."""
        await self.request_llc_status(LlcName.CBCS)

    async def status_cscs(self) -> None:
        """CSCS status command."""
        await self.request_llc_status(LlcName.CSCS)

    async def status_lcs(self) -> None:
        """LCS status command."""
        await self.request_llc_status(LlcName.LCS)

    async def status_lwscs(self) -> None:
        """LWSCS status command."""
        await self.request_llc_status(LlcName.LWSCS)

    async def status_moncs(self) -> None:
        """MonCS status command."""
        await self.request_llc_status(LlcName.MONCS)

    async def status_rad(self) -> None:
        """RAD status command."""
        await self.request_llc_status(LlcName.RAD)

    async def status_thcs(self) -> None:
        """ThCS status command."""
        await self.request_llc_status(LlcName.THCS)

    async def request_llc_status(self, llc_name: LlcName) -> None:
        """Generic method for retrieving the status of a lower level component.

        The status also is pre_processed, meaning prepared for further
        processing downstream.

        Parameters
        ----------
        llc_name: `LlcName`
            The name of the lower level component.
        """
        # Assume that the corresponding callback exists. The check for that is
        # in _start_periodic_tasks where the telemetry task is scheduled.
        cb: typing.Callable = self.telemetry_callbacks[llc_name]

        command = CommandName(f"status{llc_name.value}")
        status: dict[str, typing.Any] = {}
        while llc_name not in status:
            try:
                status = await self.write_then_read_reply(command=command)
            except Exception:
                self.log.exception(f"Exception requesting status for {llc_name.value}.")
                await cb(self.communication_error_report)
                return

        pre_processed_status = await self._pre_process_status(
            llc_name, status[llc_name]
        )

        # The timestamp is irrelevant for capacitor banks status.
        if llc_name == LlcName.CBCS and "timestamp" in pre_processed_status:
            del pre_processed_status["timestamp"]

        # Store the status for reference.
        self.lower_level_status[llc_name] = pre_processed_status

        await cb(pre_processed_status)  # type: ignore

    async def _pre_process_status(
        self, llc_name: str, llc_status: dict[str, typing.Any]
    ) -> dict[str, typing.Any]:
        """Pre-process the telemetry.

        This means converting radians to degrees, rounding off values, and
        renaming and removing keys.

        Parameters
        ----------
        llc_name: `str`
            The name of the lower level component.

        Returns
        -------
        dict[str, typing.Any]
            The pre-processed telemetry.
        """
        pre_processed_telemetry: dict[str, typing.Any] = {}
        for key in llc_status.keys():
            if key in _KEYS_IN_RADIANS and llc_name in [
                LlcName.AMCS.value,
                LlcName.LWSCS.value,
            ]:
                pre_processed_telemetry[key] = math.degrees(llc_status[key])
                # Compensate for the dome azimuth offset. This is done here and
                # not one level higher since angle_wrap_nonnegative only
                # accepts Angle or a float in degrees and this way the
                # conversion from radians to degrees only is done in one line
                # of code.
                if key in _AMCS_KEYS_OFFSET and llc_name == LlcName.AMCS.value:
                    offset_value = utils.angle_wrap_nonnegative(
                        pre_processed_telemetry[key] - DOME_AZIMUTH_OFFSET
                    ).degree
                    pre_processed_telemetry[key] = offset_value
            elif key == "timestampUTC":
                # DM-26653: The name of this parameter is still under
                # discussion.
                pre_processed_telemetry["timestamp"] = llc_status["timestampUTC"]
            else:
                # No conversion needed since the value does not express an
                # angle.
                pre_processed_telemetry[key] = llc_status[key]

        # Round off values.
        await self._round_telemetry_values(llc_name, pre_processed_telemetry)

        return pre_processed_telemetry

    async def _round_telemetry_values(
        self, llc_name: str, telemetry: dict[str, typing.Any]
    ) -> None:
        """Round the values in the telemetry.

        Whether a value is rounded and to how many decimals is defined
        in the _KEYS_TO_ROUND dict.

        Parameters
        ----------
        llc_name: `str`
            The name of the lower level component.
        telemetry : `dict`[`str`, `typing.Any`]
            The telemetry which values may be rounded.
        """
        keys_to_round = _KEYS_TO_ROUND[llc_name] if llc_name in _KEYS_TO_ROUND else {}
        for key in telemetry.keys():
            if key in keys_to_round:
                if isinstance(telemetry[key], list):
                    # Add 0.0 to avoid -0.0 values
                    telemetry[key] = [
                        round(val, keys_to_round[key]) + 0.0 for val in telemetry[key]
                    ]
                else:
                    # Add 0.0 to avoid -0.0 values
                    telemetry[key] = round(telemetry[key], keys_to_round[key]) + 0.0

    async def check_all_commands_have_replies(self) -> None:
        """Check if all commands have received a reply.

        If a command hasn't received a reply after at least
        COMMANDS_REPLIED_PERIOD seconds, a warning is logged.

        If a command hasn't received a reply after at least 2 *
        COMMANDS_REPLIED_PERIOD seconds, an error is logged and the command
        is removed from the waiting list.
        """
        current_tai = utils.current_tai()
        commands_to_remove: set[int] = set()
        commands_still_waiting: set[int] = set()
        for command_id in self.commands_without_reply:
            command_time = self.commands_without_reply[command_id]
            if current_tai - command_time.tai >= 2.0 * COMMANDS_REPLIED_PERIOD:
                commands_to_remove.add(command_id)
            elif current_tai - command_time.tai >= COMMANDS_REPLIED_PERIOD:
                commands_still_waiting.add(command_id)
        for command_id in commands_to_remove:
            self.commands_without_reply.pop(command_id)
        if len(commands_still_waiting) > 0:
            self.log.warning(
                f"Still waiting for replies for the following command_ids: {commands_still_waiting}."
            )
        if len(commands_to_remove) > 0:
            self.log.error(
                f"Giving up waiting for replies for the following command_ids: {commands_to_remove}."
            )

    def remove_keys_from_dict(
        self, dict_with_too_many_keys: dict[str, typing.Any], keys_to_remove: set[str]
    ) -> dict[str, typing.Any]:
        """
        Return a copy of a dict with specified items removed.

        Parameters
        ----------
        dict_with_too_many_keys : `dict`
            The dict where to remove the keys from.
        keys_to_remove : `set`[`str`]
            The keys to remove from the dict.

        Returns
        -------
        dict_with_keys_removed : `dict`
            A dict with the same keys as the given dict but with the given keys
            removed.
        """
        dict_with_keys_removed = {
            x: dict_with_too_many_keys[x]
            for x in dict_with_too_many_keys
            if x not in keys_to_remove
        }
        return dict_with_keys_removed

    async def __aenter__(self) -> MTDomeCom:
        await self.connect()
        return self

    async def __aexit__(
        self,
        type: typing.Type[BaseException],
        value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        await self.disconnect()
