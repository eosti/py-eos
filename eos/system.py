import logging
import time
from typing import Any, List, Optional

from eos.base import EosBase
from eos.types import EosException

logger = logging.getLogger(__name__)


class EosSystem(EosBase):
    def __init__(self):
        self.dispatcher.map("/eos/out/user", self._updateUserHandler)
        self.dispatcher.map("/eos/out/show/name", self._updateShowNameHandler)
        self.dispatcher.map("/eos/out/state", self._updateStateHandler)
        self.dispatcher.map("/eos/out/event/state", self._updateStateHandler)
        self.dispatcher.map("/eos/out/locked", self._updateLockedHandler)
        self.dispatcher.map("/eos/out/event/locked", self._updateLockedHandler)
        # self.dispatcher.map("/eos/out/cmd", self._updateCmdHandler)
        self.dispatcher.map("/eos/out/softkey/*", self._updateSoftKeyHandler)
        self.softkeys: List[Optional[str]] = [None] * 12
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

    def _updateShowNameHandler(self, addr: str, *args: List[Any]) -> None:
        self.show_name = args[0]

    def _updateStateHandler(self, addr: str, *args: List[Any]) -> None:
        self.eos_state = int(args[0])

    def _updateLockedHandler(self, addr: str, *args: List[Any]) -> None:
        self.is_locked = bool(args[0])

    def _updateSoftKeyHandler(self, addr: str, *args: List[Any]) -> None:
        sk_num = int(addr.rsplit("/", 1)[1])
        # zero-index the python array
        if args[0] == "":
            self.softkeys[sk_num - 1] = None
        else:
            self.softkeys[sk_num - 1] = args[0]

    def _updateCmdHandler(self, addr: str, *args: List[Any]) -> None:
        pass
