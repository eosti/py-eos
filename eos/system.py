import logging
import time
from typing import Any, List, Optional
from decimal import Decimal

from eos.base import EosBase
from eos.types import EosException, EosWheel, EosChannel, EosState

logger = logging.getLogger(__name__)


class EosSystem(EosBase):
    def __init__(self):
        self.wheels: dict[int, EosWheel] = {}
        self.switch: dict[int, EosWheel] = {}
        self.softkeys: List[Optional[str]] = [None] * 12
        self.user_cmd_line: dict[int, tuple[str, str, bool]] = {}

        self.dispatcher.map("/eos/out/user", self._updateUserHandler)
        self.dispatcher.map("/eos/out/show/name", self._updateShowNameHandler)
        self.dispatcher.map("/eos/out/state", self._updateStateHandler)
        self.dispatcher.map("/eos/out/event/state", self._updateStateHandler)
        self.dispatcher.map("/eos/out/locked", self._updateLockedHandler)
        self.dispatcher.map("/eos/out/event/locked", self._updateLockedHandler)
        self.dispatcher.map("/eos/out/cmd", self._updateCmdHandler)
        self.dispatcher.map("/eos/out/user/*", self._updateUserCmdHandler)
        self.dispatcher.map("/eos/out/softkey/*", self._updateSoftKeyHandler)
        self.dispatcher.map("/eos/out/active/chan", self._updateActiveChanHandler)
        self.dispatcher.map("/eos/out/active/wheel/*", self._updateWheelHandler)
        self.dispatcher.map("/eos/out/wheel", self._resetWheelHandler)
        self.dispatcher.map("/eos/out/switch", self._resetSwitchHandler)
        self.dispatcher.map("/eos/out/color/hs", self._updateHSColorHandler)
        self.dispatcher.map("/eos/out/pantilt", self._updatePanTiltHandler)
        self.dispatcher.map("/eos/out/xyz", self._updateXYZHandler)
        super().__init__()

    def ping(self, message: str = ""):
        ping_flag = False

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal ping_flag
            logger.info("Pong!")
            if args[0] != message:
                logger.debug(args)
                raise EosException("Ping doesn't match pong")
            ping_flag = True

        self.write("/eos/ping", message)
        filter = self.dispatcher.map("/eos/out/ping", handler)
        self.handle_messages()
        if ping_flag is False:
            raise EosException("No ping response received")

        self.dispatcher.unmap("/eos/out/ping", filter)

    def get_version(self) -> str:
        version = None

        def handler(addr: str, *args: List[any]) -> None:
            # Ignores fixture library version
            nonlocal version
            version = args[0]

        self.write("/eos/get/version")
        filter = self.dispatcher.map("/eos/out/get/version", handler)
        self.handle_messages()
        if version is None:
            raise EosException("Did not receive version data")

        self.dispatcher.unmap("/eos/out/get/version", filter)
        return version

    def _updateUserHandler(self, addr: str, *args: List[Any]) -> None:
        self.user_id = int(args[0])
        logging.debug("User ID: %i", self.user_id)

    def _updateShowNameHandler(self, addr: str, *args: List[Any]) -> None:
        self.show_name = args[0]
        logging.debug("Show name: %s", self.show_name)

    def _updateStateHandler(self, addr: str, *args: List[Any]) -> None:
        self.eos_state = EosState(int(args[0]))
        logging.debug("Eos state: %s", self.eos_state)

    def _updateLockedHandler(self, addr: str, *args: List[Any]) -> None:
        self.is_locked = bool(args[0])
        logging.debug("Is locked: %s", self.is_locked)

    def _updateSoftKeyHandler(self, addr: str, *args: List[Any]) -> None:
        sk_num = int(addr.rsplit("/", 1)[1])
        # zero-index the python array
        if args[0] == "":
            self.softkeys[sk_num - 1] = None
        else:
            self.softkeys[sk_num - 1] = args[0]

    def _updateActiveChanHandler(self, addr: str, *args: List[Any]) -> None:
        self.active_chan = EosChannel.from_args(args)

        if self.active_chan is not None:
            logging.debug("Active Chan: %s @ %s (%s v%d)", self.active_chan.chan, self.active_chan.intens, self.active_chan.fixture_type, self.active_chan.fixture_version)

        # When active chan is updated, wheels will reset
        self.wheels.clear()

    def _updateWheelHandler(self, addr: str, *args: List[Any]) -> None:
        wheel_no = int(addr.split("/")[-1])
        self.wheels.update({wheel_no: EosWheel.from_args(wheel_no, args)})

    def _resetWheelHandler(self, addr: str, *args: List[Any]) -> None:
        if args[0] != 0:
            logger.warning("Non-zero empty wheel value... Something is afoot!")
            logger.warning("%s %s", addr, args[0])
        else: 
            self.wheels.clear()

    def _resetSwitchHandler(self, addr: str, *args: List[Any]) -> None:
        if args[0] != 0:
            logger.warning("Non-zero empty switch value... Something is afoot!")
            logger.warning("%s %s", addr, args[0])
        else: 
            # Switches not implemented yet
            pass

    def _updateCmdHandler(self, addr: str, *args: List[Any]) -> None:
        combined_cmd = ''.join(args[:-1])
        self.display_mode = combined_cmd.split(":")[0]
        self.cmd_line = combined_cmd.split(":", 2)[2]
        self.cmd_line_error = bool(args[-1])

        if self.cmd_line_error:
            logging.debug("%s: %s (ERROR)", self.display_mode, self.cmd_line)
        else:
            logging.debug("%s: %s", self.display_mode, self.cmd_line)

    def _updateUserCmdHandler(self, addr: str, *args: List[Any]) -> None:
        combined_cmd = ''.join(args[:-1])
        user_number = int(addr.split("/")[-2])
        display_mode = combined_cmd.split(":")[0].strip()
        cmd_line = combined_cmd.split(":", 2)[2].strip()
        self.user_cmd_line.update({user_number: (display_mode, cmd_line, bool(args[-1]))})
        logging.debug("User %i: %s: %s", user_number, self.user_cmd_line[user_number][0], self.user_cmd_line[user_number][1])

    def _updateHSColorHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0:
            self.hs = None
        else:
            self.hs = (Decimal(args[0]), Decimal(args[1]))
            logger.debug("Hue/Sat: %f, %f", self.hs[0], self.hs[1])

    def _updatePanTiltHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0:
            self.pantilt = None
        else:
            self.pantilt = (Decimal(args[0]), Decimal(args[1]))
            logger.debug("Pan/Tilt: %f, %f", self.pantilt[0], self.pantilt[1])

    def _updateXYZHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0:
            self.xyz = None
        else: 
            self.xyz = (Decimal(args[0]), Decimal(args[1]), Decimal(args[2]))
            logger.debug("X/Y/Z: %f, %f, %f", self.xyz[0], self.xyz[1], self.xyz[2])
