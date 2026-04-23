"""Group-related functionality."""

import logging
from abc import ABC
from decimal import Decimal

from eos.base import EosBase
from eos.helpers import EosChanSelection, EosCmdLineException, EosException, EosTab, GroupProperties
from eos.iterator import EosGroupIterator

logger = logging.getLogger(__name__)


class EosGroups(ABC, EosBase):
    """Mixin for group-related actions."""

    def __init__(self) -> None:
        """Initialize group iterator."""
        self.group = EosGroupIterator(self)
        super().__init__()

    def new_group(
        self,
        group_num: Decimal,
        chans: list | EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Create a new group without presence checks."""
        logger.info("Creating new group %g", group_num)
        self.send_command(f"Group {group_num} #")
        if label is not None:
            self.send_command(f"Group {group_num} Label {label} #")
        self.send_command(chans.eos_command() + " #")

    def update_group(
        self,
        existing_group: GroupProperties,
        group_num: Decimal,
        chans: list | EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Update an existing group with new properties."""
        if existing_group.label != label:
            logger.info("Updating group %f label to %s", group_num, label)
            self.send_command(f"Group {group_num} Label {label} #")
        if existing_group.chans != chans:
            logger.info(
                "Updating group %f channels to %s (was %s)", group_num, chans, existing_group.chans
            )
            self.send_command(f"Group {group_num} #")
            self.send_command(chans.eos_command() + " # #")

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
            self.group.get(group_num)
        except EosException:
            self.new_group(group_num, chans, label)
        else:
            raise EosException("Group already exists!")

    def record_group_overwrite(
        self,
        group_num: Decimal,
        chans: list | EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Records a group even if the group already exists."""
        self.open_tab(EosTab.GROUPS)
        if isinstance(chans, list):
            chans = EosChanSelection(chans)
        try:
            grp = self.group.get(group_num)
        except EosException:
            self.new_group(group_num, chans, label)
        else:
            self.update_group(grp, group_num, chans, label)

    def delete_group(self, group_num: Decimal) -> None:
        """Delete a group."""
        self.send_command(f"Delete Group {group_num} # #")
        self.handle_messages()
        if self.cmd_line_error:
            raise EosCmdLineException(f"Group {group_num} does not exist")
