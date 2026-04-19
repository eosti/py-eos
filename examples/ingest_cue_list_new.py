import argparse
import logging
import os
import time
from dataclasses import dataclass

import pandas as pd

from eos import Cue, EosSLIP

# Before running this, make a Q1 with hard zeroes and everything set to preset home


@dataclass
class SpotAction:
    intensity: int | None
    character: int | None
    notes: str | None


@dataclass
class CuelistCue:
    number: int
    label: str
    flags: list[str]
    cue_time: float | None = None
    spot_1: SpotAction | None = None
    spot_2: SpotAction | None = None


def text_file(path: str) -> str:
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError("Path is not a valid file")

    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("excel", help="Excel cue list", type=text_file)

    args = parser.parse_args()
    logging.basicConfig(level="DEBUG")

    all_cues = []
    all_characters = []

    with open(args.excel, mode="rb") as f:
        cuelist = pd.read_excel(f, header=[0, 1])

    cuelist = cuelist.rename(columns=lambda x: x if "Unnamed" not in str(x) else "")
    cuelist.columns = [" ".join(a).strip() for a in cuelist.columns.to_flat_index()]
    cuelist["Pg"] = pd.to_numeric(cuelist["Pg"], downcast="integer", errors="coerce")

    convert_dict = {"Pg": "Int64", "Cue": float, "Spot 1 Intens": "Int64", "Spot 2 Intens": "Int64"}
    cuelist = cuelist.astype(convert_dict)

    for idx, row in cuelist.iterrows():
        # Ingest assuming Q#, page #, placement, notes, flags, flags
        cue_label = f"Pg. {row['Pg']}: {row['Placement']}"
        if not pd.isna(row["Notes"]):
            cue_label += f" ({row['Notes']})"

        flags = []
        if not pd.isna(row["Flags Cue"]):
            flags += row["Flags Cue"].split(" ")
        if not pd.isna(row["Flags Scene"]):
            flags.append(f"Sc {row['Flags Scene']}")

        # flags = list(filter(None, flags))

        this_cue = CuelistCue(float(row["Cue"]), cue_label, flags)

        if not pd.isna(row["Time"]):
            this_cue.cue_time = row["Time"]

        for spotnum in [1, 2]:
            continue
            if (
                (not pd.isna(row[f"Spot {spotnum} Intens"]))
                or (not pd.isna(row[f"Spot {spotnum} Notes"]))
                or (not pd.isna(row[f"Spot {spotnum} Character"]))
            ):
                if pd.isna(row[f"Spot {spotnum} Intens"]):
                    intensity = None
                else:
                    intensity = row[f"Spot {spotnum} Intens"]

                if pd.isna(row[f"Spot {spotnum} Notes"]):
                    notes = None
                else:
                    intensity = row[f"Spot {spotnum} Notes"]

                if pd.isna(row[f"Spot {spotnum} Character"]):
                    character = None
                else:
                    character = row[f"Spot {spotnum} Character"]
                    all_characters.append(character)

                action = SpotAction(intensity, character, notes)
                setattr(this_cue, f"spot_{spotnum}", action)

        all_cues.append(this_cue)

    logging.info("Parsed %i cues", len(all_cues))

    all_characters = sorted(list(set(all_characters)))
    logging.info("Parsed %i characters", len(all_characters))

    eos = EosSLIP("localhost", 3032)
    eos.live()
    eos.clear_cmd_line()

    for idx, val in enumerate(all_characters):
        eos.send_command(f"Focus_Palette {400 + idx} Label {val} #")

    for i in all_cues:
        this_cue = Cue(1, i.number)
        eos.record_cue(this_cue)
        time.sleep(0.05)
        eos.label_cue(this_cue, i.label)

        if i.cue_time is not None:
            eos.set_time(this_cue, i.cue_time)

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

        for spotnum in [1, 2]:
            if getattr(i, f"spot_{spotnum}") is not None:
                spot_cue = Cue(400 + spotnum, i.number)
                eos.record_cue(spot_cue)
                cue_label = ""
                if getattr(i, f"spot_{spotnum}").character is not None:
                    fp = 400 + all_characters.index(getattr(i, f"spot_{spotnum}").character)
                    eos.send_command(f"40{spotnum} Focus_Palette {fp} #")
                    cue_label = getattr(i, f"spot_{spotnum}").character
                if getattr(i, f"spot_{spotnum}").intensity is not None:
                    eos.send_command(
                        f"40{spotnum} @ " + str(getattr(i, f"spot_{spotnum}").intensity) + " #"
                    )

                if i.cue_time is not None:
                    eos.set_time(spot_cue, i.cue_time)

                if getattr(i, f"spot_{spotnum}").notes is not None:
                    cue_label += " | " + getattr(i, f"spot_{spotnum}").notes

                eos.label_cue(spot_cue, cue_label)


if __name__ == "__main__":
    main()
