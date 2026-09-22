"""Cue-related functionality."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eos.eos import Eos

from eos.enums import EosState
from eos.helpers import Cue, EosCmdLineError, EosError
from eos.iterator import EosCueIterator
from eos.properties import CueProperties

logger = logging.getLogger(__name__)


class EosCues(EosCueIterator):
    def __init__(self, eos: "Eos") -> None:
        self.eos = eos
        """Map cue-related dispatchers."""
        self.previous_cue: Cue | None = None
        self.active_cue: Cue | None = None
        self.pending_cue: Cue | None = None
        self.iterator = EosCueIterator(self.eos)
        self._send_command = self.eos.send_command

        self.eos.osc.dispatcher.map("/eos/out/previous/cue*", self._updatePreviousCueHandler)
        self.eos.osc.dispatcher.map("/eos/out/active/cue*", self._updateActiveCueHandler)
        self.eos.osc.dispatcher.map("/eos/out/pending/cue*", self._updatePendingCueHandler)
        super().__init__(eos)

    def _updatePreviousCueHandler(self, addr: str, *args: list[Any]) -> None:
        """Handle previous cue updates."""
        if len(args) == 0 or args[0] == "":
            self.previous_cue = None
        elif "text" in addr:
            self.previous_cue = Cue.from_nonactive_cue(str(args[0]))
            logger.debug("Previous cue: %s", self.previous_cue)
        else:
            # Redundant info, skip it
            pass

    def _updateActiveCueHandler(self, addr: str, *args: list[Any]) -> None:
        """Handle active cue updates."""
        if len(args) == 0 or args[0] == "":
            self.active_cue = None
        elif "text" in addr:
            self.active_cue = Cue.from_active_cue(str(args[0]))
            logger.debug("Active cue: %s", self.active_cue)
        else:
            # Redundant info, skip it
            pass

    def _updatePendingCueHandler(self, addr: str, *args: list[Any]) -> None:
        """Handle pending cue updates."""
        if len(args) == 0 or args[0] == "":
            self.pending_cue = None
        elif "text" in addr:
            self.pending_cue = Cue.from_nonactive_cue(str(args[0]))
            logger.debug("Pending cue: %s", self.pending_cue)
        else:
            # Redundant info, skip it
            pass

    def record(self, cue: Cue) -> CueProperties:
        """Record a cue."""
        if cue.part != 0:
            raise ValueError("cue must have part zero")

        try:
            self.get_cue(cue)
        except EosError:
            pass
        else:
            raise EosError("Cue already exists")

        if self.eos.system.eos_state == EosState.BLIND:
            self._send_command(f"Cue {cue.cue_format()} # #")
        elif self.eos.system.eos_state == EosState.LIVE:
            self._send_command(f"Record Cue {cue.cue_format()} #")

        return self.get_cue(cue)

    def record_part(self, cue: Cue, part: int | None = None) -> CueProperties:
        """Record a part of a cue."""
        if part is not None:
            cue.part = part

        try:
            self.get_cue(cue)
        except EosError:
            pass
        else:
            raise EosError("Cue part already exists")

        if self.eos.system.eos_state == EosState.BLIND:
            self._send_command(f"Cue {cue.cue_format()} # #")
        elif self.eos.system.eos_state == EosState.LIVE:
            self._send_command(f"Record Cue {cue.cue_format()} #")

        return self.get_cue(cue)

    def delete(self, cue: Cue) -> None:
        self._send_command(f"Delete Cue {cue.cue_format()} # #")
        if self.eos.system.cmd_line_error:
            raise EosCmdLineError(f"Cue {cue} does not exist")

    def intensity_block(self, cue: Cue) -> None:
        """Give a cue an Intensity Block flag."""
        props = self.get_cue(cue)
        if "I" in props.blockstr:
            return
        self._send_command(f"Cue {cue.cue_format()} Intensity Block #")

    def block(self, cue: Cue) -> None:
        """Give a cue a Block flag."""
        props = self.get_cue(cue)
        if "B" in props.blockstr:
            return
        self._send_command(f"Cue {cue.cue_format()} Block #")

    def assert_flag(self, cue: Cue) -> None:
        """Give a cue an Assert flag."""
        props = self.get_cue(cue)
        if "A" in props.assertstr:
            return
        self._send_command(f"Cue {cue.cue_format()} Assert #")

    def mark(self, cue: Cue) -> None:
        """Give a cue a normal-priority mark attribute."""
        props = self.get_cue(cue)
        if "M" in props.markstr or "m" in props.markstr:
            return
        self._send_command(f"Cue {cue.cue_format()} Mark #")

    def mark_high(self, cue: Cue) -> None:
        """Give a cue a high-priority mark attribute."""
        # TODO(eosti): check if "Mark" is in softkeys to see if Automark on
        props = self.get_cue(cue)
        if "Mh" in props.markstr or "mh" in props.markstr:
            return
        self._send_command(f"Cue {cue.cue_format()} Mark High_Priority #")

    def mark_low(self, cue: Cue) -> None:
        """Give a cue a low-priority mark attribute."""
        props = self.get_cue(cue)
        if "Ml" in props.markstr or "ml" in props.markstr:
            return
        self._send_command(f"Cue {cue.cue_format()} Mark Low_Priority #")

    def label(self, cue: Cue, label: str) -> None:
        """Label a cue."""
        self._send_command(f"Cue {cue.cue_format()} Label {label} #")

    def set_time(
        self, cue: Cue, uptime: Decimal | int, downtime: Decimal | int | None = None
    ) -> None:
        """Set the time of a cue (i.e. intensity up if other values already set)."""
        if downtime is None:
            self._send_command(f"Cue {cue.cue_format()} Time {uptime} #")
        else:
            self._send_command(f"Cue {cue.cue_format()} Time {uptime} / {downtime} #")

    def add_scene(self, cue: Cue, scene: str) -> None:
        """Add a scene attribute to a cue."""
        props = self.get_cue(cue)
        if props.scene not in ("", scene):
            logger.warning("Renaming scene on %s (%s)", cue.cue_format(), props.scene)
        self._send_command(f"Cue {cue.cue_format()} Scene {scene}")
        self.eos.keys.enter()

    def link_cue(self, src_cue: Cue, dest_cue: Cue) -> None:
        if dest_cue.part != 0:
            raise ValueError("Unable to link to cue part")
        try:
            self._send_command(f"Cue {src_cue.cue_format()} Link {dest_cue.cue_format()} #")
        except EosCmdLineError as e:
            raise EosCmdLineError("Destination cue does not exist") from e

    def execute_cue(self, src_cue: Cue, dest_cue: Cue) -> None:
        if dest_cue.part != 0:
            raise ValueError("Unable to link to cue part")
        try:
            self._send_command(f"Cue {src_cue.cue_format()} Execute Cue {dest_cue.cue_format()} #")
        except EosCmdLineError as e:
            raise EosCmdLineError("Destination cue does not exist") from e

    def execute_macro(self, src_cue: Cue, macro: int | Decimal) -> None:
        try:
            self._send_command(f"Cue {src_cue.cue_format()} Execute Macro {macro} #")
        except EosCmdLineError as e:
            raise EosCmdLineError("Target macro does not exist") from e
