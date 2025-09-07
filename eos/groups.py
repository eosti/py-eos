"""Group-related functionality"""
import logging
import time
from abc import ABC
from typing import Optional, Union
from decimal import Decimal

from eos.base import EosBase
from eos.helpers import EosException, EosTab, EosChanSelection
from eos.iterator import EosGroupIterator

logger = logging.getLogger(__name__)


class EosGroups(ABC, EosBase):
    """Mixin for group-related actions"""

    def __init__(self):
        self.group = EosGroupIterator(self)
        super().__init__()

    def record_group(self, group_num: Decimal, chans: Union[list, EosChanSelection], label: Optional[str] = None, overwrite: bool = False) -> None:
        """Record a group"""
        self.open_tab(EosTab.GROUPS)
        if isinstance(chans, list):
            chans = EosChanSelection(chans)

        try:
            grp = self.group.get(group_num)
        except EosException:
            logging.info("Creating new group %g", group_num)
            self.send_command(f"Group {group_num} #")
            if label is not None:
                self.send_command(f"Group {group_num} Label {label} #")
            self.send_command(chans.eos_command() + " #")
        else:
            if overwrite:
                if grp.label != label:
                    logging.info(
                        "Updating group %f label to %s", group_num, label)
                    self.send_command(f"Group {group_num} Label {label} #")
                if grp.chans != chans:
                    logging.info(
                        "Updating group %f channels to %s (was %s)", group_num, chans, grp.chans
                    )
                    self.send_command(f"Group {group_num} #")
                    self.send_command(chans.eos_command() + " # #")
            else:
                raise EosException("Existing group differs from desired group!")

    def delete_group(self, group_num: Decimal):
        self.send_command(f"Delete Group {group_num} # #")
        time.sleep(0.01)
        self.handle_messages()
        if self.cmd_line_error:
            raise EosException(f"Group {group_num} does not exist")
