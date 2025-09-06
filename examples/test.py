import logging
import time

from eos import EosSLIP
from eos.types import Cue

logging.basicConfig(level="DEBUG")

eos = EosSLIP("localhost", 3032)
eos.ping("reid")
for cp in eos.iter_cues():
    print(cp)

while(1):
    eos.handle_messages()
    pass
