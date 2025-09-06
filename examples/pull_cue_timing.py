from eos import EosSLIP, Cue

import argparse
import os
import logging
import csv
from dataclasses import dataclass
import time

def main():
    logging.basicConfig(level="DEBUG")

    cue_times = []

    eos = EosSLIP("localhost", 3032)
    for cue in range(eos.get_target_count("cue")):
        this_cue = eos.get_cue_by_index(cue)
        cue_times.append((f"{this_cue.cue} {this_cue.part}", this_cue.))

    
