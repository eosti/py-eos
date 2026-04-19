import argparse
import csv
import logging
import os
import time
from dataclasses import dataclass

from eos import Cue, EosSLIP

# Before running this, make a Q1 with hard zeroes and everything set to preset home


@dataclass
class CuelistCue:
    number: int
    label: str
    flags: list[str]


def text_file(path: str) -> str:
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError("Path is not a valid file")

    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="CSV cue list", type=text_file)
    parser.add_argument("start_row", help="first row with cue data", type=int)

    args = parser.parse_args()
    logging.basicConfig(level="DEBUG")

    all_cues = []

    with open(args.csv) as f:
        csvfile = csv.reader(f)
        for i, line in enumerate(csvfile):
            if i < args.start_row:
                continue

            # Ingest assuming Q#, page #, placement, notes, flags, flags
            cue_label = f"Pg. {line[1]}: {line[2]}"
            if line[3] != "":
                cue_label += f" ({line[3]})"
            flags = line[4].split(" ")
            flags.append(line[5])
            flags = list(filter(None, flags))

            all_cues.append(CuelistCue(float(line[0]), cue_label, flags))

    logging.info("Parsed %i cues", len(all_cues))

    eos = EosSLIP("localhost", 3032)

    for i in all_cues:
        this_cue = Cue(1, i.number)
        eos.record_cue(this_cue)
        time.sleep(0.05)
        eos.label_cue(this_cue, i.label)

        if "I" in i.flags:
            eos.intensity_block_cue(this_cue)
        if "B" in i.flags:
            eos.block_cue(this_cue)
        if "A" in i.flags:
            eos.assert_cue(this_cue)
        if "M" in i.flags:
            mark_part = eos.record_part(this_cue, 20)
            eos.mark_cue(mark_part)
            eos.label_cue(mark_part, "--- MARK ---")
        if "Mh" in i.flags:
            mark_part = eos.record_part(this_cue, 20)
            eos.mark_high_cue(mark_part)
            eos.label_cue(mark_part, "--- MARK ---")
        if "Ml" in i.flags:
            mark_part = eos.record_part(this_cue, 20)
            eos.mark_low_cue(mark_part)
            eos.label_cue(mark_part, "--- MARK ---")
        if next((s for s in i.flags if "Sc" in s), None):
            scene_marker = next(s for s in i.flags if "Sc" in s).split(" ", 1)[1]
            eos.add_scene(this_cue, scene_marker)


if __name__ == "__main__":
    main()
