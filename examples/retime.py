import logging
import time

from eos import Cue, EosSLIP

# Sorry for the mixed units...
DEFAULT_CUETIME_MS = 2900
NEW_CUETIME_S = 0.49

logging.basicConfig(level=logging.INFO)

eos = EosSLIP("localhost", 3032)

cue_index = eos.get_cue_idx(1)

for i in range(cue_index):
    cue = eos.get_cue_by_idx(1, i)
    if cue.uptime == DEFAULT_CUETIME_MS or cue.uptime == -1:
        # Default cue time, so we change it

        eos.set_time(Cue(1, float(cue.cue), part=int(cue.part)), NEW_CUETIME_S)
        logging.info(f"Changed cue {cue.cue}/{cue.part} to new default time")
    time.sleep(0.05)
