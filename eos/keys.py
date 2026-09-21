import logging
import time
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eos.eos import Eos

from eos.helpers import Cue, EosTab

logger = logging.getLogger(__name__)


class EosKeys:
    """
    Please see https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/23_Show_Control/08_OSC/OSC_Dictionary.htm#Keys
        for valid keys
    """
    def __init__(self, eos: "Eos", generic_delay: float = 0) -> None:
        self.eos = eos
        self._write = self.eos.osc.write
        self.generic_delay = generic_delay

    def press_key(self, key: str) -> None:
        """Send a keystroke to Eos."""
        self._write(f"/eos/key/{key}")

    def blind(self) -> None:
        """Press the blind key on Eos."""
        self.press_key("Blind")
        time.sleep(self.generic_delay)

    def live(self) -> None:
        """Press the live key on Eos."""
        self.press_key("Live")
        time.sleep(self.generic_delay)

    def enter(self) -> None:
        """Press the enter key on Eos."""
        self._write("/eos/cmd", ["#"])

    def go(self) -> None:
        """Press the Go key on Eos."""
        self.press_key("Go_0")

    def stop_hold(self) -> None:
        """Press the stop/hold key on Eos."""
        self.press_key("Stop")

    def clear_cmd_line(self) -> None:
        """Clear the active command line on Eos."""
        self._write("/eos/cmd", ["Clear_Cmd"])

    def open_tab(self, tab: EosTab) -> None:
        """Open a new tab in Eos."""
        self._write("/eos/key/Tab", [1.0])
        time.sleep(0.1)
        for i in str(int(tab)):
            self._write(f"/eos/key/{i}")
        self._write("/eos/key/Tab", [0.0])

    def go_to_cue(self, cue: Cue, time_s: int | Decimal = 0) -> None:
        self.eos.send_command(f"Go_To_Cue {cue.cue_format()} Time {time_s} #")

    def go_to_cue_zero(self, time_s: int | Decimal = 0) -> None:
        self.eos.send_command(f"Go_To_Cue 0 Time {time_s} #")

    def go_to_cue_out(self, time_s: int | Decimal = 0) -> None:
        self.eos.send_command(f"Go_To_Cue Out Time {time_s} #")
