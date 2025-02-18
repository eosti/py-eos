import logging
import time

from eos import EosSLIP
from eos_types import Cue

logging.basicConfig(level="DEBUG")

eos = EosSLIP("localhost", 3032)
eos.ping("reid")
print(eos.get_cue(Cue(1, 1)))
print(eos.get_group(1))
time.sleep(1)
