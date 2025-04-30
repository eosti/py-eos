import logging
import time

from eos import EosSLIP
from eos.types import Cue

logging.basicConfig(level="DEBUG")

eos = EosSLIP("localhost", 3032)
eos.ping("reid")
this_cue = Cue(1, 2, 3)
eos.live()
eos.mark_cue(this_cue)
eos.enter()

while(1):
    eos.handle_messages()
    pass
