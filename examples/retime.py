"""Changes all cues with a specified duration to another."""

import logging
import time
from decimal import Decimal

from eos import Cue, Eos

logger = logging.getLogger(__name__)

DEFAULT_CUETIME = Decimal("2.9")
NEW_CUETIME = Decimal("0.49")


def main() -> None:  # noqa: D103
    logging.basicConfig(level=logging.DEBUG)
    eos = Eos.tcp_slip("localhost", 3032)

    cue_index = eos.cues.count(1)

    for i in range(cue_index):
        cue = eos.cues.get_by_idx(i, cuelist=1)
        if cue.uptime == DEFAULT_CUETIME or cue.uptime < 0:
            # Default cue time, so we change it

            eos.cues.set_time(Cue(1, Decimal(cue.number), part=int(cue.part)), NEW_CUETIME)
            logger.info("Changed cue %s/%s to new default time", cue.number, cue.part)
        time.sleep(0.05)


if __name__ == "__main__":
    main()
