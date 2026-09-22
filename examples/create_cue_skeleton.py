import argparse
import logging
from pathlib import Path
import time

from path import Path
from strictyaml import Bool, Float, Map, Optional, Seq, Str, load

from eos import Cue, Eos

# Before running this, make a Q1 with hard zeros and everything set to preset home


def text_file(path: str) -> str:
    """Check if a path is a text file."""
    if not Path(path).is_file():
        raise argparse.ArgumentTypeError("Path is not a valid file")

    return path


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml", help="YAML config file", type=text_file)

    args = parser.parse_args()
    logging.basicConfig(level="DEBUG")

    eos = Eos.tcp_slip("localhost", 3032)

    scene_schema = Map(
        {"name": Str(), "start": Float(), Optional("no_label", default=False): Bool()}
    )
    config_schema = Map({"blackout_offset": Float()})
    root_schema = Map({"scenes": Seq(scene_schema), "config": config_schema})

    input_data = load(Path(args.yaml).text(), root_schema)

    for i in input_data["scenes"].data:
        # Create blackout cue first
        blackout_cue = Cue(1, i["start"] + input_data["config"]["blackout_offset"].data)
        eos.cues.record(blackout_cue)
        time.sleep(0.05)
        eos.cues.intensity_block(blackout_cue)
        eos.cues.assert_flag(blackout_cue)
        # eos.send_command(f"Group {blackout_group} @ Preset {blackout_preset} #")
        eos.cues.label(blackout_cue, "Blackout")

        # Then, create lights up cue
        start_cue = Cue(1, i["start"])
        eos.cues.record(start_cue)
        time.sleep(0.05)
        eos.cues.block(start_cue)
        # eos.send_command(f"Group {blackout_group} Out #")
        # eos.send_command(f"Group {blackout_group} @ Preset 999 #")
        eos.cues.add_scene(start_cue, i["name"])

    time.sleep(0.1)
    eos.keys.live()


if __name__ == "__main__":
    main()
