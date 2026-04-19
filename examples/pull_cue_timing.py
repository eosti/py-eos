import logging

from eos import EosSLIP


def main():
    logging.basicConfig(level="DEBUG")

    cue_times = []

    eos = EosSLIP("localhost", 3032)
    for cue in range(eos.get_target_count("cue")):
        this_cue = eos.get_cue_by_index(cue)
        cue_times.append(f"{this_cue.cue} {this_cue.part}")
