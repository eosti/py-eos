"""Generates a spot CSV from an Eos show file.

Requires a cuelist with labels that start with "FS", ex.
    "FS Up Glinda, midshot"
    "FS Out snap"
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from eos import EosSLIP

# Alternate idea: put character in FP, then poll channel for spot info
logger = logging.getLogger(__name__)


@dataclass
class FollowspotCue:
    """Container for followspot data in a single cue."""

    cue: float
    action: str
    time: float
    character: str | None = None
    notes: str | None = None

    def to_list(self) -> tuple:
        """Return data as an ordered tuple."""
        return (self.cue, self.action, self.time, self.character, self.notes)


def main() -> None:
    """Run main program logic."""
    logging.basicConfig(level=logging.INFO)

    eos = EosSLIP("localhost", 3032)

    cue_index = eos.get_cue_idx(1)
    fs_cues = []

    for i in range(cue_index):
        cue = eos.get_cue_by_idx(1, i)
        notes = ""
        if "FS" in cue.label:
            if "Up" in cue.label:
                if len(cue.label.split(" ")) == 2:
                    character = "idk"
                else:
                    cue_info = cue.label.split(" ", 2)[2].split(",")
                    character = cue_info[0]
                    if len(cue_info) > 1:
                        notes = cue_info[1]
                action = "Up"
            elif "Out" in cue.label:
                character = None
                action = "Out"
                if len(cue.label.split(" ")) > 2:
                    notes = cue.label.split(" ", 2)[2]
            else:
                character = None
                action = "-"
                if len(cue.label.split(" ")) > 1:
                    notes = cue.label.split(" ", 1)[1]

            fs_cues.append(FollowspotCue(cue.cue, action, cue.uptime / 1000, character, notes))

    logger.info("%s cues collected", len(fs_cues))

    with Path("fs_cues.csv").open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["Cue", "Action", "Time", "Character", "Notes"])
        for i in fs_cues:
            writer.writerow(i.to_list())


if __name__ == "__main__":
    main()
