import logging
import time
from abc import abstractmethod
from typing import Any, List, Optional

from pythonosc.osc_packet import OscPacket

from eos.types import EosException, EosTab, EosTargets

logger = logging.getLogger(__name__)


class EosBase:
    """Base class for Eos with R/W functions"""

    @abstractmethod
    def write(self, path: str, args: Optional[List[str]]) -> None:
        pass

    @abstractmethod
    def read_next(self, timeout: int) -> OscPacket:
        pass

    @abstractmethod
    def handle_messages(self, timeout: int) -> None:
        pass

    def press_key(self, key: str) -> None:
        self.write(f"/eos/key/{key}")

    def send_command(self, commandline: str) -> None:
        self.write("/eos/newcmd", [commandline])

    def enter(self) -> None:
        self.write("/eos/cmd", ["#"])

    def blind(self) -> None:
        self.press_key("Blind")

    def live(self) -> None:
        self.press_key("Live")

    def open_tab(self, tab: EosTab) -> None:
        self.write("/eos/key/Tab", [1.0])
        time.sleep(0.1)
        for i in str(int(tab)):
            self.write(f"/eos/key/{i}")
        self.write("/eos/key/Tab", [0.0])

    def get_target_count(self, target: str, **kwargs: List[str]) -> int:
        assert target in EosTargets
        if target == "cue":
            query_str = f"get/cue/{kwargs.get('cuelist', 1)}/count"
        else:
            query_str = f"get/{target}/count"

        target_count = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal target_count
            target_count = args[0]

        filter = self.dispatcher.map(f"/eos/out/{query_str}", handler)
        self.write("/eos/{query_str}")
        self.handle_messages()

        if target_count is None:
            raise EosException(f"Unable to get number of targets for {target}")

        self.dispatcher.unmap(f"/eos/out/{query_str}", filter)
        return target_count
