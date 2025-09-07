import logging
import time
from typing import Any, List

from eos.base import EosBase
from eos.types import Cue, CueProperties, EosException

logger = logging.getLogger(__name__)


class EosCues(EosBase):
    def __init__(self):
        self.dispatcher.map("/eos/out/previous/cue*", self._updatePreviousCueHandler)
        self.dispatcher.map("/eos/out/active/cue*", self._updateActiveCueHandler)
        self.dispatcher.map("/eos/out/pending/cue*", self._updatePendingCueHandler)
        super().__init__()

    def _updatePreviousCueHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0 or args[0] == "":
            self.previousCue = None
        elif "text" in addr:
            self.previousCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updateActiveCueHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0 or args[0] == "":
            self.activeCue = None
        elif "text" in addr:
            self.activeCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updatePendingCueHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0 or args[0] == "":
            self.pendingCue = None
        elif "text" in addr:
            self.pendingCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def record_cue(self, cue: Cue) -> None:
        self.blind()
        if cue.part != 0:
            raise ValueError("cue must have part zero")
        try:
            self.cue.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
            time.sleep(0.05)
        # Otherwise, cue already exists!

    def record_part(self, cue: Cue, part) -> Cue:
        # TODO: how to do this not in blind too, or at least restore state?
        self.blind()
        cue.part = part
        try:
            self.cue.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
            time.sleep(0.05)

        return cue

    def intensity_block_cue(self, cue: Cue) -> None:
        props = self.cue.get_cue(cue)
        if "I" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Intensity Block #")

    def block_cue(self, cue: Cue) -> None:
        props = self.cue.get_cue(cue)
        if "B" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Block #")

    def assert_cue(self, cue: Cue) -> None:
        props = self.cue.get_cue(cue)
        if "A" in props.assertstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Assert #")

    def mark_cue(self, cue: Cue) -> None:
        props = self.cue.get_cue(cue)
        if "M" in props.markstr or "m" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark #")

    def mark_high_cue(self, cue: Cue) -> None:
        # TODO check if "Mark" is in softkeys to see if Automark on
        props = self.cue.get_cue(cue)
        if "Mh" in props.markstr or "mh" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark High_Priority #")

    def mark_low_cue(self, cue: Cue) -> None:
        props = self.cue.get_cue(cue)
        if "Ml" in props.markstr or "ml" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark Low_Priority #")

    def label_cue(self, cue: Cue, label: str) -> None:
        props = self.cue.get_cue(cue)
        if props.label != label:
            logging.info(
                f"Updating cue {cue.cue_format()} label from {props.label} to {label}"
            )
            self.send_command(f"Cue {cue.cue_format()} Label {label}")
            self.enter()

    def set_time(self, cue: Cue, cuetime: float) -> None:
        self.send_command(f"Cue {cue.cue_format()} Time {cuetime} #")

    def add_scene(self, cue: Cue, scene: str) -> None:
        props = self.cue.get_cue(cue)
        if props.scene != "" and props.scene != scene:
            logging.warning(f"Renaming scene on {cue.cue_format()} ({props.scene})")
        self.send_command(f"Cue {cue.cue_format()} Scene {scene}")
        self.enter()
