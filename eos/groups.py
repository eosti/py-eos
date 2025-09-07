import logging
import time
from typing import Any, List

from eos.base import EosBase
from eos.types import EosException, EosTab, GroupProperties

logger = logging.getLogger(__name__)


class EosGroups(EosBase):
    def record_group(self, group: GroupProperties, overwrite: bool = False) -> None:
        self.open_tab(EosTab.GROUPS)
        try:
            grp = self.get_group(group.number)
        except EosException:
            logging.info(f"Creating new group {group.number}")
            self.send_command(f"Group {group.number} #")
            self.send_command(f"Group {group.number} Label {group.label} #")
            self.send_command(group.chanCommand())
        else:
            if overwrite:
                if grp.label != group.label:
                    logging.info(
                        f"Updating group {group.number} label to {group.label}"
                    )
                    self.send_command(f"Group {group.number} Label {group.label} #")
                if grp.channels != group.channels:
                    logging.info(
                        f"Updating group {group.number} channels to {group.channels} (was {grp.channels})"
                    )
                    self.send_command(f"Group {group.number} #")
                    self.send_command(group.chanCommand() + "#")
            else:
                raise EosException("Existing group differs from desired group!")
