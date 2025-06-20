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

__all__ = ["MockMTDomeController"]

import asyncio
import logging
import typing

from lsst.ts import tcpip, utils
from lsst.ts.xml.enums.MTDome import MotionState

from .encoding_tools import validate
from .enums import (
    CSCS_COMMANDS,
    EL_COMMANDS,
    LOUVERS_COMMANDS,
    RAD_COMMANDS,
    SHUTTER_COMMANDS,
    CommandName,
    LlcName,
    ResponseCode,
)
from .mock_llc import (
    AmcsStatus,
    ApscsStatus,
    BaseMockStatus,
    CbcsStatus,
    CscsStatus,
    LcsStatus,
    LwscsStatus,
    MoncsStatus,
    RadStatus,
    ThcsStatus,
)


ROTATING_COMMANDS = (
    CSCS_COMMANDS + EL_COMMANDS + LOUVERS_COMMANDS + RAD_COMMANDS + SHUTTER_COMMANDS
)


class MockMTDomeController(tcpip.OneClientReadLoopServer):
    """Mock MTDome Controller that talks over TCP/IP.

    Parameters
    ----------
    port : `int`
        TCP/IP port
    log : `logging.Logger`
        The logger to use.
    connect_callback : `callable`
        The callback to use when a client connects.
    communication_error : `bool`
        Is there a communication error with the rotating part (True) or not
        (False)? This is for unit tests only. The default is False.

    Notes
    -----
    There are six sub-systems that are under control:

    * AMCS: Azimuth Motion Control System
    * ApSCS: Aperture Shutter Control System
    * LCS: Louvers Control System
    * LWSCS: Light and Wind Screen Control System
    * MonCS: Monitoring Control System, which interfaces with the MTDome
        Interlock System
    * ThCS: Thermal Control System, which interfaces with the MTDome
        Environment Control System

    To start the server:

        ctrl = MockMTDomeController(...)
        await ctrl.start()

    To stop the server:

        await ctrl.stop()

    Known Limitations:

    * Just a framework that needs to be implemented properly.
    """

    # A long sleep to mock a slow network [s].
    SLOW_NETWORK_SLEEP = 10.0
    # A long duration [s]. Used as a return value by commands.
    LONG_DURATION = 20

    def __init__(
        self,
        port: int,
        log: logging.Logger,
        connect_callback: None | tcpip.ConnectCallbackType = None,
        communication_error: bool = False,
    ) -> None:
        super().__init__(
            port=port,
            log=log,
            connect_callback=connect_callback,
        )

        # Dict of command: (has_argument, function).
        # The function is called with:
        # * No arguments, if `has_argument` False.
        # * The argument as a string, if `has_argument` is True.
        self.dispatch_dict: dict[str, typing.Callable] = {
            CommandName.CLOSE_LOUVERS: self.close_louvers,
            CommandName.CLOSE_SHUTTER: self.close_shutter,
            CommandName.CONFIG: self.config,
            CommandName.CRAWL_AZ: self.crawl_az,
            CommandName.CRAWL_EL: self.crawl_el,
            CommandName.EXIT_FAULT_AZ: self.exit_fault_az,
            CommandName.EXIT_FAULT_EL: self.exit_fault_el,
            CommandName.EXIT_FAULT_SHUTTER: self.exit_fault_shutter,
            CommandName.EXIT_FAULT_LOUVERS: self.exit_fault_louvers,
            CommandName.EXIT_FAULT_THERMAL: self.exit_fault_thermal,
            CommandName.FANS: self.fans,
            CommandName.GO_STATIONARY_AZ: self.go_stationary_az,
            CommandName.GO_STATIONARY_EL: self.go_stationary_el,
            CommandName.GO_STATIONARY_LOUVERS: self.go_stationary_louvers,
            CommandName.GO_STATIONARY_SHUTTER: self.go_stationary_shutter,
            CommandName.HOME: self.home,
            CommandName.INFLATE: self.inflate,
            CommandName.MOVE_AZ: self.move_az,
            CommandName.MOVE_EL: self.move_el,
            CommandName.OPEN_SHUTTER: self.open_shutter,
            CommandName.PARK: self.park,
            CommandName.RESET_DRIVES_AZ: self.reset_drives_az,
            CommandName.RESET_DRIVES_SHUTTER: self.reset_drives_shutter,
            CommandName.RESTORE: self.restore,
            CommandName.SET_DEGRADED_AZ: self.set_degraded_az,
            CommandName.SET_DEGRADED_EL: self.set_degraded_el,
            CommandName.SET_DEGRADED_LOUVERS: self.set_degraded_louvers,
            CommandName.SET_DEGRADED_MONITORING: self.set_degraded_monitoring,
            CommandName.SET_DEGRADED_SHUTTER: self.set_degraded_shutter,
            CommandName.SET_DEGRADED_THERMAL: self.set_degraded_thermal,
            CommandName.SET_LOUVERS: self.set_louvers,
            CommandName.SET_NORMAL_AZ: self.set_normal_az,
            CommandName.SET_NORMAL_EL: self.set_normal_el,
            CommandName.SET_NORMAL_LOUVERS: self.set_normal_louvers,
            CommandName.SET_NORMAL_MONITORING: self.set_normal_monitoring,
            CommandName.SET_NORMAL_SHUTTER: self.set_normal_shutter,
            CommandName.SET_NORMAL_THERMAL: self.set_normal_thermal,
            CommandName.SET_TEMPERATURE: self.set_temperature,
            CommandName.SET_ZERO_AZ: self.set_zero_az,
            CommandName.STATUS_AMCS: self.status_amcs,
            CommandName.STATUS_APSCS: self.status_apscs,
            CommandName.STATUS_CBCS: self.status_cbcs,
            CommandName.STATUS_CSCS: self.status_cscs,
            CommandName.STATUS_LCS: self.status_lcs,
            CommandName.STATUS_LWSCS: self.status_lwscs,
            CommandName.STATUS_MONCS: self.status_moncs,
            CommandName.STATUS_RAD: self.status_rad,
            CommandName.STATUS_THCS: self.status_thcs,
            CommandName.STOP_AZ: self.stop_az,
            CommandName.STOP_EL: self.stop_el,
            CommandName.STOP_LOUVERS: self.stop_louvers,
            CommandName.STOP_SHUTTER: self.stop_shutter,
        }
        # Time keeping
        self.current_tai = 0
        # Mock a slow network (True) or not (False). To be set by unit tests
        # only.
        self.enable_slow_network = False
        # Mock a network interruption (True) or not (False). To be set by unit
        # tests only.
        self.enable_network_interruption = False
        # Mock a communication error (True) or not (False). To be set by unit
        # tests only.
        self.communication_error = communication_error

        self.read_task: asyncio.Future | None = None

        # Keep track of the command ID.
        self._command_id = -1

        # Variables for the lower level components.
        self.amcs: AmcsStatus | None = None
        self.apscs: ApscsStatus | None = None
        self.cbcs: CbcsStatus | None = None
        self.cscs: CscsStatus | None = None
        self.lcs: LcsStatus | None = None
        self.lwscs: LwscsStatus | None = None
        self.moncs: MoncsStatus | None = None
        self.rad: RadStatus | None = None
        self.thcs: ThcsStatus | None = None

    async def start(self, **kwargs: typing.Any) -> None:
        """Start the TCP/IP server.

        Parameters
        ----------
        **kwargs : `dict` [`str`, `typing.Any`]
            Additional keyword arguments for `asyncio.start_server`,
            beyond host and port.
        """
        self.log.info("Start called")
        await super().start(**kwargs)

        await self.determine_current_tai()

        self.log.info("Starting LLCs")
        self.amcs = AmcsStatus(start_tai=self.current_tai)
        self.apscs = ApscsStatus(start_tai=self.current_tai)
        self.cbcs = CbcsStatus()
        self.cscs = CscsStatus(start_tai=self.current_tai)
        self.lcs = LcsStatus()
        self.lwscs = LwscsStatus(start_tai=self.current_tai)
        self.moncs = MoncsStatus()
        self.rad = RadStatus()
        self.thcs = ThcsStatus()

    async def write_reply(self, **data: typing.Any) -> None:
        """Write the data appended with the commandId.

        The non-negative, non-zero commandId is contained in the incoming data,
        for which this method writes a reply, and is copied as is.

        Parameters
        ----------
        data:
            The data to write.
        """
        data = {"commandId": self._command_id, **data}
        await self.write_json(data)

    async def read_and_dispatch(self) -> None:
        response = ResponseCode.OK
        try:
            data = await self.read_json()
            self.log.debug(f"Read command data: {data!r}.")
        except Exception as e:
            self.log.warning(f"Ignoring a command that was not valid json: {e!r}.")
            return
        try:
            validate(data)
        except Exception:
            self.log.warning(
                f"Ignoring command {data} because it has incorrect schema."
            )
            if "commandId" in data:
                self._command_id = data["commandId"]
            response = ResponseCode.INCORRECT_PARAMETERS
            await self.write_reply(response=response, timeout=-1)
            return

        self._command_id = data["commandId"]
        try:
            cmd = data["command"]
            self.log.debug(f"Trying to execute cmd {cmd}")
            if cmd not in self.dispatch_dict:
                self.log.error(f"Command '{data}' unknown")
                response = ResponseCode.UNSUPPORTED
                duration = -1
            else:
                if self.enable_network_interruption:
                    # Mock a network interruption: it doesn't matter if
                    # the command never is received or the reply never
                    # sent.
                    self.log.debug("Mocking a network interruption.")
                    return

                if self.communication_error and cmd in ROTATING_COMMANDS:
                    self.log.debug("Mocking a communication error.")
                    response = ResponseCode.ROTATING_PART_NOT_RECEIVED
                    duration = -1
                else:
                    func = self.dispatch_dict[cmd]
                    kwargs = data["parameters"]

                    if self.enable_slow_network:
                        # Mock a slow network.
                        await asyncio.sleep(MockMTDomeController.SLOW_NETWORK_SLEEP)

                    duration = await func(**kwargs)

                    if cmd.startswith("status"):
                        # The status commands take care of sending a reply
                        # themselves.
                        return
        except Exception:
            self.log.exception(f"Command '{data}' failed")
            # Command rejected: a message explaining why needs to be
            # added at some point, but we haven't discussed that yet
            # with the vendor.
            response = ResponseCode.INCORRECT_PARAMETERS
            duration = -1
        if duration is None:
            duration = MockMTDomeController.LONG_DURATION
        # DM-25189: timeout should be renamed duration and this
        # needs to be discussed with EIE. As soon as this is done
        # and agreed upon, I will open another issue to fix this.
        await self.write_reply(response=response, timeout=duration)

    async def status_amcs(self) -> None:
        """Request the status from the AMCS lower level component and write it
        in reply.
        """
        assert self.amcs is not None
        await self.request_and_send_status(self.amcs, LlcName.AMCS.value)

    async def status_apscs(self) -> None:
        """Request the status from the ApSCS lower level component and write it
        in reply.
        """
        assert self.apscs is not None
        await self.request_and_send_status(self.apscs, LlcName.APSCS.value)

    async def status_cbcs(self) -> None:
        """Request the status from the CBCS lower level component and write it
        in reply.
        """
        assert self.cbcs is not None
        await self.request_and_send_status(self.cbcs, LlcName.CBCS.value)

    async def status_cscs(self) -> None:
        """Request the status from the Calibration Screen and write it in
        reply.
        """
        assert self.cscs is not None
        await self.request_and_send_status(self.cscs, LlcName.CSCS.value)

    async def status_lcs(self) -> None:
        """Request the status from the LCS lower level component and write it
        in reply.
        """
        assert self.lcs is not None
        await self.request_and_send_status(self.lcs, LlcName.LCS.value)

    async def status_lwscs(self) -> None:
        """Request the status from the LWSCS lower level component and write it
        in reply.
        """
        assert self.lwscs is not None
        await self.request_and_send_status(self.lwscs, LlcName.LWSCS.value)

    async def status_moncs(self) -> None:
        """Request the status from the MonCS lower level component and write it
        in reply.
        """
        assert self.moncs is not None
        await self.request_and_send_status(self.moncs, LlcName.MONCS.value)

    async def status_rad(self) -> None:
        """Request the status from the RAD lower level component and write it
        in reply.
        """
        assert self.rad is not None
        await self.request_and_send_status(self.rad, LlcName.RAD.value)

    async def status_thcs(self) -> None:
        """Request the status from the ThCS lower level component and write it
        in reply.
        """
        assert self.thcs is not None
        await self.request_and_send_status(self.thcs, LlcName.THCS.value)

    async def request_and_send_status(self, llc: BaseMockStatus, llc_name: str) -> None:
        """Request the status of the given Lower Level Component and write it
        to the requester.

        Parameters
        ----------
        llc: `BaseMockStatus`
            The Lower Level Component status to request the status from.
        llc_name: `str`
            The name of the Lower Level Component.
        """
        self.log.debug("Determining current TAI.")
        await self.determine_current_tai()
        self.log.debug(f"Requesting status for LLC {llc_name}")
        await llc.determine_status(self.current_tai)
        state = {llc_name: llc.llc_status}
        if llc_name == LlcName.AMCS:
            assert self.thcs is not None
            if (
                llc.llc_status["status"]["status"]
                == MotionState.STARTING_MOTOR_COOLING.name
            ):
                await self.thcs.start_cooling(self.current_tai)
            elif (
                llc.llc_status["status"]["status"]
                == MotionState.STOPPING_MOTOR_COOLING.name
            ):
                await self.thcs.stop_cooling(self.current_tai)
        await self.write_reply(response=ResponseCode.OK, **state)

    async def start_or_stop_thcs_if_necessary(self) -> None:
        # empty
        pass

    async def determine_current_tai(self) -> None:
        """Determine the current TAI time.

        This is done in a separate method so a mock method can replace it in
        unit tests.
        """
        self.current_tai = utils.current_tai()

    async def move_az(self, position: float, velocity: float) -> float:
        """Move the dome.

        Parameters
        ----------
        position: `float`
            Desired azimuth, in radians, in range [0, 2 pi)
        velocity: `float`
            The velocity, in rad/sec, to start crawling at once the position
            has been reached.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        # No conversion from radians to degrees needed since both the commands
        # and the mock az controller use radians.
        assert self.amcs is not None
        return await self.amcs.moveAz(position, velocity, self.current_tai)

    async def move_el(self, position: float) -> float:
        """Move the light and windscreen.

        Parameters
        ----------
        position: `float`
            Desired elevation, in radians, in range [0, pi/2)

        Returns
        -------
        duration: `float`
            The estimated duration of the execution of the command.
        """
        # No conversion from radians to degrees needed since both the commands
        # and the mock az controller use radians.
        assert self.lwscs is not None
        return await self.lwscs.moveEl(position, self.current_tai)

    async def stop_az(self) -> float:
        """Stop all dome motion.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.amcs is not None
        return await self.amcs.stopAz(self.current_tai)

    async def stop_el(self) -> float:
        """Stop all light and windscreen motion.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.lwscs is not None
        return await self.lwscs.stopEl(self.current_tai)

    async def crawl_az(self, velocity: float) -> float:
        """Crawl the dome.

        Parameters
        ----------
        velocity: `float`
            The velocity, in rad/sec, to crawl at.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        # No conversion from radians to degrees needed since both the commands
        # and the mock az controller use radians.
        assert self.amcs is not None
        return await self.amcs.crawlAz(velocity, self.current_tai)

    async def crawl_el(self, velocity: float) -> float:
        """Crawl the light and windscreen.

        Parameters
        ----------
        velocity: `float`
            The velocity, in rad/sec, to crawl at.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        # No conversion from radians to degrees needed since both the commands
        # and the mock az controller use radians.
        assert self.lwscs is not None
        return await self.lwscs.crawlEl(velocity, self.current_tai)

    async def set_louvers(self, position: list[float]) -> None:
        """Set the positions of the louvers.

        Parameters
        ----------
        position: array of float
            An array of positions, in percentage with 0 meaning closed and 100
            fully open, for each louver. A position of -1 means "do not move".
        """
        assert self.lcs is not None
        await self.lcs.setLouvers(position, self.current_tai)

    async def close_louvers(self) -> None:
        """Close all louvers."""
        assert self.lcs is not None
        await self.lcs.closeLouvers(self.current_tai)

    async def stop_louvers(self) -> None:
        """Stop the motion of all louvers."""
        assert self.lcs is not None
        await self.lcs.stopLouvers(self.current_tai)

    async def open_shutter(self) -> float:
        """Open the shutter.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.apscs is not None
        return await self.apscs.openShutter(self.current_tai)

    async def close_shutter(self) -> float:
        """Close the shutter.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.apscs is not None
        return await self.apscs.closeShutter(self.current_tai)

    async def stop_shutter(self) -> float:
        """Stop the motion of the shutter.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.apscs is not None
        return await self.apscs.stopShutter(self.current_tai)

    async def config(self, system: str, settings: dict) -> None:
        """Configure the lower level components.

        Parameters
        ----------
        system: `str`
            The name of the system to configure.
        settings: `dict`
            An array containing a single dict with key,value pairs for all the
            parameters that need to be configured. The structure is::

                [
                    {
                      "Parameter1_name": Value,
                      "Parameter2_name": Value,
                      ...
                    }
                  ]

            It is assumed that the values of the configuration parameters are
            validated to lie within the limits before being passed on to this
            function.
            It is assumed that all configuration parameters are present and
            that their values represent the value to set even unchanged.
        """
        if system == LlcName.AMCS.value:
            for field in settings:
                if field["target"] in ("jmax", "amax", "vmax"):
                    # DM-25758: All param values are passed on as arrays so in
                    # these cases we need to extract the only value in the
                    # array.
                    assert self.amcs is not None
                    setattr(self.amcs, field["target"], field["setting"][0])
        elif system == LlcName.LWSCS.value:
            for field in settings:
                if field["target"] in ("jmax", "amax", "vmax"):
                    # DM-25758: All param values are passed on as arrays so in
                    # these cases we need to extract the only value in the
                    # array.
                    assert self.lwscs is not None
                    setattr(self.lwscs, field["target"], field["setting"][0])
        else:
            raise KeyError(f"Unknown system {system}.")

    async def restore(self) -> None:
        """Restore the default configuration of the lower level components."""
        self.log.debug("Received command 'restore'")
        # TODO: Need to find a way to store the default values for all lower
        #  level components.

    async def park(self) -> float:
        """Park the dome.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.amcs is not None
        return await self.amcs.park(self.current_tai)

    async def go_stationary_az(self) -> float:
        """Stop azimuth motion and engage the brakes. Also disengage the
        locking pins if engaged.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.amcs is not None
        return await self.amcs.go_stationary(self.current_tai)

    async def go_stationary_el(self) -> float:
        """Stop elevation motion and engage the brakes. Also disengage the
        locking pins if engaged.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.lwscs is not None
        return await self.lwscs.go_stationary(self.current_tai)

    async def go_stationary_shutter(self) -> float:
        """Stop shutter motion and engage the brakes.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.apscs is not None
        return await self.apscs.go_stationary(self.current_tai)

    async def go_stationary_louvers(self) -> None:
        """Stop louvers motion and engage the brakes."""
        assert self.lcs is not None
        await self.lcs.go_stationary(self.current_tai)

    async def set_normal_az(self) -> None:
        """Set az operational mode to normal (as opposed to degraded)."""
        assert self.amcs is not None
        await self.amcs.set_normal()

    async def set_normal_el(self) -> None:
        """Set el operational mode to normal (as opposed to degraded)."""
        assert self.lwscs is not None
        await self.lwscs.set_normal()

    async def set_normal_shutter(self) -> None:
        """Set shutter operational mode to normal (as opposed to degraded)."""
        assert self.apscs is not None
        await self.apscs.set_normal()

    async def set_normal_louvers(self) -> None:
        """Set louvers operational mode to normal (as opposed to degraded)."""
        assert self.lcs is not None
        await self.lcs.set_normal()

    async def set_normal_monitoring(self) -> None:
        """Set monitoring operational mode to normal (as opposed to
        degraded).
        """
        assert self.moncs is not None
        await self.moncs.set_normal()

    async def set_normal_thermal(self) -> None:
        """Set thermal operational mode to normal (as opposed to degraded)."""
        assert self.thcs is not None
        await self.thcs.set_normal()

    async def set_degraded_az(self) -> None:
        """Set az operational mode to degraded (as opposed to normal)."""
        assert self.amcs is not None
        await self.amcs.set_degraded()

    async def set_degraded_el(self) -> None:
        """Set el operational mode to degraded (as opposed to normal)."""
        assert self.lwscs is not None
        await self.lwscs.set_degraded()

    async def set_degraded_shutter(self) -> None:
        """Set shutter operational mode to degraded (as opposed to normal)."""
        assert self.apscs is not None
        await self.apscs.set_degraded()

    async def set_degraded_louvers(self) -> None:
        """Set louvers operational mode to degraded (as opposed to normal)."""
        assert self.lcs is not None
        await self.lcs.set_degraded()

    async def set_degraded_monitoring(self) -> None:
        """Set monitoring operational mode to degraded (as opposed to
        normal).
        """
        assert self.moncs is not None
        await self.moncs.set_degraded()

    async def set_degraded_thermal(self) -> None:
        """Set thermal operational mode to degraded (as opposed to normal)."""
        assert self.thcs is not None
        await self.thcs.set_degraded()

    async def set_temperature(self, temperature: float) -> None:
        """Set the preferred temperature in the dome.

        Parameters
        ----------
        temperature: `float`
            The temperature, in degrees Celsius, to set.
        """
        assert self.thcs is not None
        await self.thcs.set_temperature(temperature, self.current_tai)

    async def exit_fault_az(self) -> None:
        """Exit AMCS from fault state."""
        assert self.amcs is not None
        await self.amcs.exit_fault(self.current_tai)

    async def exit_fault_shutter(self) -> None:
        """Exit ApSCS from fault state."""
        assert self.apscs is not None
        await self.apscs.exit_fault(self.current_tai)

    async def exit_fault_el(self) -> None:
        """Exit LWSCS from fault state."""
        assert self.lcs is not None
        await self.lcs.exit_fault(self.current_tai)

    async def exit_fault_louvers(self) -> None:
        """Exit LCS from fault state."""
        assert self.lwscs is not None
        await self.lwscs.exit_fault(self.current_tai)

    async def exit_fault_thermal(self) -> None:
        """Exit ThCS from fault state."""
        assert self.thcs is not None
        await self.thcs.exit_fault()

    async def inflate(self, action: str) -> None:
        """Inflate or deflate the inflatable seal.

        Parameters
        ----------
        action: `str`
            ON means inflate and OFF deflate the inflatable seal.
        """
        assert self.amcs is not None
        await self.amcs.inflate(self.current_tai, action)

    async def fans(self, speed: float) -> None:
        """Enable or disable the fans in the dome.

        Parameters
        ----------
        speed: `float`
            The speed of the fans [%].
        """
        assert self.amcs is not None
        await self.amcs.fans(self.current_tai, speed)

    async def reset_drives_az(self, reset: list[int]) -> float:
        """Reset one or more AZ drives.

        Parameters
        ----------
        reset: array of int
            Desired reset action to execute on each AZ drive: 0 means don't
            reset, 1 means reset.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.

        Notes
        -----
        This is necessary when exiting from FAULT state without going to
        Degraded Mode since the drives don't reset themselves.
        The number of values in the reset parameter is not validated.
        """
        assert self.amcs is not None
        return await self.amcs.reset_drives_az(self.current_tai, reset)

    async def reset_drives_shutter(self, reset: list[int]) -> None:
        """Reset one or more Aperture Shutter drives.

        Parameters
        ----------
        reset: array of int
            Desired reset action to execute on each Aperture Shutter drive: 0
            means don't reset, 1 means reset.

        Notes
        -----
        This is necessary when exiting from FAULT state without going to
        Degraded Mode since the drives don't reset themselves.
        The number of values in the reset parameter is not validated.
        """
        assert self.apscs is not None
        await self.apscs.reset_drives_shutter(self.current_tai, reset)

    async def set_zero_az(self) -> float:
        """Take the current position of the dome as zero. This is necessary as
        long as the racks, pinions and encoders on the drives have not been
        installed yet to compensate for slippage of the drives.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.amcs is not None
        return await self.amcs.set_zero_az(self.current_tai)

    async def home(self) -> float:
        """Home the Aperture Shutter, which is the closed position.

        This is necessary in case the ApSCS (Aperture Shutter Control System)
        was shutdown with the Aperture Shutter not fully open or fully closed.

        Returns
        -------
        `float`
            The estimated duration of the execution of the command.
        """
        assert self.apscs is not None
        return await self.apscs.home(self.current_tai)


async def main() -> None:
    """Main method that gets executed in standalone mode."""
    log = logging.getLogger("MockMTDomeController")
    log.info("main method")
    # An arbitrarily chosen port. Nothing special about it.
    port = 5000
    log.info("Constructing mock controller.")
    mock_ctrl = MockMTDomeController(port=port, log=log)
    log.info("Starting mock MTDome controller.")
    await mock_ctrl.start(keep_running=True)


if __name__ == "__main__":
    logging.info("main")
    loop = asyncio.get_event_loop()
    try:
        logging.info("Calling main method")
        loop.run_until_complete(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
