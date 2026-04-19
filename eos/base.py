"""Base module for Eos functions."""

import logging
import time
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pythonosc.dispatcher import Dispatcher

from pythonosc.osc_packet import OscPacket

from eos.helpers import EosException, EosTab, EosTargets

logger = logging.getLogger(__name__)


class EosBase:
    """Base class for Eos with R/W functions."""

    GENERIC_DELAY = 0.02

    def __init__(self) -> None:
        """Initialize EosBase."""
        self.dispatcher: Dispatcher

    @abstractmethod
    def write(self, path: str, args: list[str | int | float | bool] | None = None) -> None:
        """Write an OSC string to Eos."""

    @abstractmethod
    def read_next(self, timeout: int = 30) -> OscPacket:
        """Read the next message in the queue."""

    @abstractmethod
    def handle_messages(self, timeout: float = 0.1, retries: int = 3) -> None:
        """Read all messages in queue and execute associated handlers."""

    def press_key(self, key: str) -> None:
        """Send a keystroke to Eos."""
        self.write(f"/eos/key/{key}")

    def send_command(self, commandline: str) -> None:
        """Send a full command to Eos."""
        self.write("/eos/newcmd", [commandline])

    def enter(self) -> None:
        """Press the enter key on Eos."""
        self.write("/eos/cmd", ["#"])

    def clear_cmd_line(self) -> None:
        """Clear the active command line on Eos."""
        self.write("/eos/cmd", ["Clear_Cmd"])

    def blind(self) -> None:
        """Press the blind key on Eos."""
        self.press_key("Blind")
        time.sleep(self.GENERIC_DELAY)

    def live(self) -> None:
        """Press the live key on Eos."""
        self.press_key("Live")
        time.sleep(self.GENERIC_DELAY)

    def open_tab(self, tab: EosTab) -> None:
        """Open a new tab in Eos."""
        self.write("/eos/key/Tab", [1.0])
        time.sleep(0.1)
        for i in str(int(tab)):
            self.write(f"/eos/key/{i}")
        self.write("/eos/key/Tab", [0.0])

    def get_target_count(self, target: str, **kwargs: list[str]) -> int:
        """Get the number of targets of a particular type."""
        if target not in EosTargets:
            raise ValueError("Invalid target %s", target)

        if target == "cue":
            if "cuelist" not in kwargs:
                logger.warning("Cuelist not specified for target count; defaulting to 1")
            query_str = f"get/cue/{kwargs.get('cuelist', 1)}/count"
        else:
            query_str = f"get/{target}/count"

        target_count: int | None = None

        def handler(_: str, *args: list[Any]) -> None:
            nonlocal target_count
            if isinstance(args[0], int):
                target_count = args[0]
            else:
                logger.warning("Uncertain target count conversion %s", args[0])
                target_count = int(args[0])

        osc_filter = self.dispatcher.map(f"/eos/out/{query_str}", handler)
        self.write(f"/eos/{query_str}")
        self.handle_messages()

        if target_count is None:
            raise EosException(f"Unable to get number of targets for {target}")

        self.dispatcher.unmap(f"/eos/out/{query_str}", osc_filter)
        return target_count
