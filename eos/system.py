"""Collection of logic for Eos system-level functions."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eos.eos import Eos


from eos.helpers import EosActiveChannel, EosError, EosState, EosTimeoutError, EosWheel
from eos.transaction import Transaction

logger = logging.getLogger(__name__)


class EosSystem:
    """Mixin for Eos system-level actions."""

    def __init__(self, eos: "Eos") -> None:
        self.eos = eos
        self.wheels: dict[int, EosWheel] = {}
        self.switch: dict[int, EosWheel] = {}
        self.softkeys: list[str | None] = [None] * 12
        self.user_cmd_line: dict[int, tuple[str, str, bool]] = {}

        self.hs: tuple(float, float)
        self.pantilt: tuple(float, float)
        self.xyz: tuple(float, float, float)
        self.user_id: int
        self.show_name: str
        self.eos_state: EosState
        self.display_mode: str
        self.is_locked: bool
        self.active_chan: EosActiveChannel
        self.cmd_line: str
        self.cmd_line_error: bool

        self.eos.osc.dispatcher.map("/eos/out/user", self._updateUserHandler)
        self.eos.osc.dispatcher.map("/eos/out/show/name", self._updateShowNameHandler)
        self.eos.osc.dispatcher.map("/eos/out/state", self._updateStateHandler)
        self.eos.osc.dispatcher.map("/eos/out/event/state", self._updateStateHandler)
        self.eos.osc.dispatcher.map("/eos/out/locked", self._updateLockedHandler)
        self.eos.osc.dispatcher.map("/eos/out/event/locked", self._updateLockedHandler)
        self.eos.osc.dispatcher.map("/eos/out/cmd", self._updateCmdHandler)
        self.eos.osc.dispatcher.map("/eos/out/user/*", self._updateUserCmdHandler)
        self.eos.osc.dispatcher.map("/eos/out/softkey/*", self._updateSoftKeyHandler)
        self.eos.osc.dispatcher.map("/eos/out/active/chan", self._updateActiveChanHandler)
        self.eos.osc.dispatcher.map("/eos/out/active/wheel/*", self._updateWheelHandler)
        self.eos.osc.dispatcher.map("/eos/out/wheel", self._resetWheelHandler)
        self.eos.osc.dispatcher.map("/eos/out/switch", self._resetSwitchHandler)
        self.eos.osc.dispatcher.map("/eos/out/color/hs", self._updateHSColorHandler)
        self.eos.osc.dispatcher.map("/eos/out/pantilt", self._updatePanTiltHandler)
        self.eos.osc.dispatcher.map("/eos/out/xyz", self._updateXYZHandler)

    def ping(self, message: str = "") -> None:
        """Pings Eos to check for liveness.

        Raises:
            EosError if no ping back received.

        """
        try:
            resp = Transaction(
                osc_conn=self.eos.osc,
                query_path="/eos/ping",
                query_data=[message],
                resp_filter="/eos/out/ping",
                num_resps=1,
            ).query()
        except EosTimeoutError as e:
            raise EosError("No ping response received") from e

        if resp[0][1] != message:
            logger.debug(resp)
            raise EosError("Ping doesn't match pong")

    def get_version(self) -> str:
        """Gets Eos's current version.

        Returns: current Eos version.
        """
        try:
            resp = Transaction(
                osc_conn=self.eos.osc,
                query_path="/eos/get/version",
                query_data=None,
                resp_filter="/eos/out/get/version",
                num_resps=1,
            ).query()
        except EosTimeoutError as e:
            raise EosError("No version data received") from e

        version = resp[0][0]
        return str(version)

    def _updateUserHandler(self, _addr: str, *args: list[Any]) -> None:
        self.user_id = int(args[0])
        logger.debug("User ID: %i", self.user_id)

    def _updateShowNameHandler(self, _addr: str, *args: list[Any]) -> None:
        self.show_name = args[0]
        logger.debug("Show name: %s", self.show_name)

    def _updateStateHandler(self, _addr: str, *args: list[Any]) -> None:
        self.eos_state = EosState(int(args[0]))
        logger.debug("Eos state: %s", self.eos_state)

    def _updateLockedHandler(self, _addr: str, *args: list[Any]) -> None:
        self.is_locked = bool(args[0])
        logger.debug("Is locked: %s", self.is_locked)

    def _updateSoftKeyHandler(self, addr: str, *args: list[Any]) -> None:
        sk_num = int(addr.rsplit("/", 1)[1])
        # zero-index the python array
        if args[0] == "":
            self.softkeys[sk_num - 1] = None
        else:
            self.softkeys[sk_num - 1] = args[0]

    def _updateActiveChanHandler(self, _addr: str, *args: list[Any]) -> None:
        self.active_chan = EosActiveChannel.from_args(args)

        if self.active_chan is not None:
            logger.debug(
                "Active Chan: %s @ %s (%s v%d)",
                self.active_chan.chan,
                self.active_chan.intens,
                self.active_chan.fixture_type,
                self.active_chan.fixture_version,
            )

        # When active chan is updated, wheels will reset
        self.wheels.clear()

    def _updateWheelHandler(self, addr: str, *args: list[Any]) -> None:
        wheel_no = int(addr.rsplit("/", maxsplit=1)[-1])
        self.wheels.update({wheel_no: EosWheel.from_args(wheel_no, args)})

    def _resetWheelHandler(self, addr: str, *args: list[Any]) -> None:
        if args[0] != 0:
            logger.warning("Non-zero empty wheel value... Something is afoot!")
            logger.warning("%s %s", addr, args[0])
        else:
            self.wheels.clear()

    def _resetSwitchHandler(self, addr: str, *args: list[Any]) -> None:
        if args[0] != 0:
            logger.warning("Non-zero empty switch value... Something is afoot!")
            logger.warning("%s %s", addr, args[0])
        else:
            # Switches not implemented yet
            pass

    def _updateCmdHandler(self, _addr: str, *args: list[Any]) -> None:
        combined_cmd = "".join(args[:-1])
        self.display_mode = combined_cmd.split(":")[0]
        self.cmd_line = combined_cmd.split(":", 2)[2]
        self.cmd_line_error = bool(args[-1])

        if self.cmd_line_error:
            logger.debug("%s: %s (ERROR)", self.display_mode, self.cmd_line)
        else:
            logger.debug("%s: %s", self.display_mode, self.cmd_line)

    def _updateUserCmdHandler(self, addr: str, *args: list[Any]) -> None:
        logger.debug(args)
        user_number = int(addr.split("/")[-2])
        combined_cmd = "".join(args[:-1])
        display_mode = combined_cmd.split(":")[0].strip()
        if combined_cmd.count(":") == 1:
            # No cues exist
            cmd_line = combined_cmd.split(":", 1)[1].strip()
        else:
            cmd_line = combined_cmd.split(":", 2)[2].strip()

        self.user_cmd_line.update({user_number: (display_mode, cmd_line, bool(args[-1]))})
        logger.debug(
            "User %i: %s: %s",
            user_number,
            self.user_cmd_line[user_number][0],
            self.user_cmd_line[user_number][1],
        )

    def _updateHSColorHandler(self, _addr: str, *args: list[Any]) -> None:
        if len(args) == 0:
            self.hs = None
        else:
            self.hs = (Decimal(args[0]), Decimal(args[1]))
            logger.debug("Hue/Sat: %f, %f", self.hs[0], self.hs[1])

    def _updatePanTiltHandler(self, _addr: str, *args: list[Any]) -> None:
        if len(args) == 0:
            self.pantilt = None
        else:
            self.pantilt = (Decimal(args[0]), Decimal(args[1]))
            logger.debug("Pan/Tilt: %f, %f", self.pantilt[0], self.pantilt[1])

    def _updateXYZHandler(self, _addr: str, *args: list[Any]) -> None:
        if len(args) == 0:
            self.xyz = None
        else:
            self.xyz = (Decimal(args[0]), Decimal(args[1]), Decimal(args[2]))
            logger.debug("X/Y/Z: %f, %f, %f", self.xyz[0], self.xyz[1], self.xyz[2])
