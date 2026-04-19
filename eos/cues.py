"""Cue-related functionality."""

import logging
import time
from abc import ABC
from typing import Any

from eos.base import EosBase
from eos.helpers import Cue, EosException
from eos.iterator import EosCueIterator

logger = logging.getLogger(__name__)


class EosCues(ABC, EosBase):
    """Mixin for cue-related actions."""

    def __init__(self) -> None:
        """Map cue-related dispatchers."""
        self.previous_cue: Cue | None = None
        self.active_cue: Cue | None = None
        self.pending_cue: Cue | None = None
        self.cue = EosCueIterator(self)

        self.dispatcher.map("/eos/out/previous/cue*", self._updatePreviousCueHandler)
        self.dispatcher.map("/eos/out/active/cue*", self._updateActiveCueHandler)
        self.dispatcher.map("/eos/out/pending/cue*", self._updatePendingCueHandler)
        super().__init__()

    def _updatePreviousCueHandler(self, addr: str, *args: list[Any]) -> None:
        """Handle previous cue updates."""
        if len(args) == 0 or args[0] == "":
            self.previous_cue = None
        elif "text" in addr:
            self.previous_cue = Cue.fromText(str(args[0]))
            logger.debug("Previous cue: %s", self.previous_cue)
        else:
            # Redundant info, skip it
            pass

    def _updateActiveCueHandler(self, addr: str, *args: list[Any]) -> None:
        """Handle active cue updates."""
        if len(args) == 0 or args[0] == "":
            self.active_cue = None
        elif "text" in addr:
            self.active_cue = Cue.fromText(str(args[0]))
            logger.debug("Active cue: %s", self.active_cue)
        else:
            # Redundant info, skip it
            pass

    def _updatePendingCueHandler(self, addr: str, *args: list[Any]) -> None:
        """Handle pending cue updates."""
        if len(args) == 0 or args[0] == "":
            self.pending_cue = None
        elif "text" in addr:
            self.pending_cue = Cue.fromText(str(args[0]))
            logger.debug("Pending cue: %s", self.pending_cue)
        else:
            # Redundant info, skip it
            pass

    def record_cue(self, cue: Cue) -> None:
        """Record a cue."""
        self.blind()
        if cue.part != 0:
            raise ValueError("cue must have part zero")
        try:
            self.cue.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
            time.sleep(self.GENERIC_DELAY)
        # Otherwise, cue already exists!

    def record_part(self, cue: Cue, part: int) -> Cue:
        """Record a part of a cue."""
        # TODO(eosti): how to do this not in blind too, or at least restore state? # noqa: TD003
        self.blind()
        cue.part = part
        try:
            self.cue.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
            time.sleep(0.05)

        return cue

    def intensity_block_cue(self, cue: Cue) -> None:
        """Give a cue an Intensity Block flag."""
        props = self.cue.get_cue(cue)
        if "I" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Intensity Block #")

    def block_cue(self, cue: Cue) -> None:
        """Give a cue a Block flag."""
        props = self.cue.get_cue(cue)
        if "B" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Block #")

    def assert_cue(self, cue: Cue) -> None:
        """Give a cue an Assert flag."""
        props = self.cue.get_cue(cue)
        if "A" in props.assertstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Assert #")

    def mark_cue(self, cue: Cue) -> None:
        """Give a cue a normal-priority mark attribute."""
        props = self.cue.get_cue(cue)
        if "M" in props.markstr or "m" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark #")

    def mark_high_cue(self, cue: Cue) -> None:
        """Give a cue a high-priority mark attribute."""
        # TODO(eosti): check if "Mark" is in softkeys to see if Automark on # noqa: TD003
        props = self.cue.get_cue(cue)
        if "Mh" in props.markstr or "mh" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark High_Priority #")

    def mark_low_cue(self, cue: Cue) -> None:
        """Give a cue a low-priority mark attribute."""
        props = self.cue.get_cue(cue)
        if "Ml" in props.markstr or "ml" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark Low_Priority #")

    def label_cue(self, cue: Cue, label: str) -> None:
        """Label a cue."""
        props = self.cue.get_cue(cue)
        if props.label != label:
            logger.info("Updating cue %s label from %s to %s", cue.cue_format(), props.label, label)
            self.send_command(f"Cue {cue.cue_format()} Label {label}")
            self.enter()

    def set_time(self, cue: Cue, cuetime: float) -> None:
        """Set the time of a cue (i.e. intensity up if other values already set)."""
        self.send_command(f"Cue {cue.cue_format()} Time {cuetime} #")

    def add_scene(self, cue: Cue, scene: str) -> None:
        """Add a scene attribute to a cue."""
        props = self.cue.get_cue(cue)
        if props.scene not in ("", scene):
            logger.warning("Renaming scene on %s (%s)", cue.cue_format(), props.scene)
        self.send_command(f"Cue {cue.cue_format()} Scene {scene}")
        self.enter()
