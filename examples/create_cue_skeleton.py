import argparse
import logging
import os
import time

from path import Path
from strictyaml import Bool, Float, Map, Optional, Seq, Str, load

from eos import Cue, EosSLIP

# Before running this, make a Q1 with hard zeros and everything set to preset home


def text_file(path: str) -> str:
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError("Path is not a valid file")

    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml", help="YAML config file", type=text_file)

    args = parser.parse_args()
    logging.basicConfig(level="DEBUG")

    eos = EosSLIP("localhost", 3032)

    scene_schema = Map(
        {"name": Str(), "start": Float(), Optional("no_label", default=False): Bool()}
    )
    config_schema = Map({"blackout_offset": Float()})
    root_schema = Map({"scenes": Seq(scene_schema), "config": config_schema})

    input_data = load(Path(args.yaml).bytes().decode("utf-8"), root_schema)

    blackout_group = 41
    blackout_preset = 0.1

    for i in input_data["scenes"].data:
        # Create blackout cue first
        blackout_cue = Cue(1, i["start"] + input_data["config"]["blackout_offset"].data)
        eos.record_blank_cue(blackout_cue)
        time.sleep(0.05)
        eos.intensity_block_cue(blackout_cue)
        eos.assert_cue(blackout_cue)
        # eos.send_command(f"Group {blackout_group} @ Preset {blackout_preset} #")
        eos.label_cue(blackout_cue, "Blackout")

        # Then, create lights up cue
        start_cue = Cue(1, i["start"])
        eos.record_blank_cue(start_cue)
        time.sleep(0.05)
        eos.block_cue(start_cue)
        # eos.send_command(f"Group {blackout_group} Out #")
        # eos.send_command(f"Group {blackout_group} @ Preset 999 #")
        eos.add_scene(start_cue, i["name"])

    time.sleep(0.1)
    eos.live()


if __name__ == "__main__":
    main()
