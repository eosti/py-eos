"""Changes all cues with a specified duration to another."""

import logging
import time

from eos import Cue, EosSLIP

logger = logging.getLogger(__name__)

# Sorry for the mixed units...
DEFAULT_CUETIME_MS = 2900
NEW_CUETIME_S = 0.49


def main() -> None:  # noqa: D103
    logging.basicConfig(level=logging.INFO)
    eos = EosSLIP("localhost", 3032)

    cue_index = eos.get_cue_idx(1)

    for i in range(cue_index):
        cue = eos.get_cue_by_idx(1, i)
        if cue.uptime in (DEFAULT_CUETIME_MS, -1):
            # Default cue time, so we change it

            eos.set_time(Cue(1, float(cue.cue), part=int(cue.part)), NEW_CUETIME_S)
            logger.info("Changed cue %s/%s to new default time", cue.cue, cue.part)
        time.sleep(0.05)


if __name__ == "__main__":
    main()
