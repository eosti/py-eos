"""Group-related functionality."""

import logging
from abc import ABC
from decimal import Decimal

from eos.base import EosBase
from eos.helpers import EosChanSelection, EosCmdLineException, EosException, EosTab
from eos.iterator import EosGroupIterator

logger = logging.getLogger(__name__)


class EosGroups(ABC, EosBase):
    """Mixin for group-related actions."""

    def __init__(self) -> None:
        """Initialize group iterator."""
        self.group = EosGroupIterator(self)
        super().__init__()

    def record_group(
        self,
        group_num: Decimal,
        chans: list | EosChanSelection,
        label: str | None = None,
        *,
        overwrite: bool = False,
    ) -> None:
        """Record a group."""
        self.open_tab(EosTab.GROUPS)
        if isinstance(chans, list):
            chans = EosChanSelection(chans)

        try:
            grp = self.group.get(group_num)
        except EosException:
            logger.info("Creating new group %g", group_num)
            self.send_command(f"Group {group_num} #")
            if label is not None:
                self.send_command(f"Group {group_num} Label {label} #")
            self.send_command(chans.eos_command() + " #")
        else:
            if overwrite:
                if grp.label != label:
                    logger.info("Updating group %f label to %s", group_num, label)
                    self.send_command(f"Group {group_num} Label {label} #")
                if grp.chans != chans:
                    logger.info(
                        "Updating group %f channels to %s (was %s)", group_num, chans, grp.chans
                    )
                    self.send_command(f"Group {group_num} #")
                    self.send_command(chans.eos_command() + " # #")
            else:
                raise EosException("Existing group differs from desired group!")

    def delete_group(self, group_num: Decimal) -> None:
        """Delete a group."""
        self.send_command(f"Delete Group {group_num} # #")
        self.handle_messages()
        if self.cmd_line_error:
            raise EosCmdLineException(f"Group {group_num} does not exist")
