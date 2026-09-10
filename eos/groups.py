"""Group-related functionality."""

import logging
from collections.abc import Sequence
from decimal import Decimal

from eos.helpers import (
    EosChanSelection,
    EosCmdLineError,
    EosError,
    EosTab,
    GroupProperties,
)
from eos.iterator import EosGroupIterator

logger = logging.getLogger(__name__)


class EosGroups(EosGroupIterator):
    """Mixin for group-related actions."""

    def _create(
        self,
        group_num: Decimal,
        chans: EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Create a new group without presence checks."""
        logger.info("Creating new group %g", group_num)
        self.eos.send_command(f"Group {group_num} #")
        if label is not None:
            self.eos.send_command(f"Group {group_num} Label {label} #")
        self.eos.send_command(chans.eos_command() + " #")

    def update(
        self,
        existing_group: GroupProperties,
        group_num: Decimal,
        chans: Sequence | EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Update an existing group with new properties."""
        if not isinstance(chans, EosChanSelection):
            chans = EosChanSelection(chans)
        if existing_group.label != label:
            logger.info("Updating group %f label to %s", group_num, label)
            self.eos.send_command(f"Group {group_num} Label {label} #")
        if existing_group.chans != chans:
            logger.info(
                "Updating group %f channels to %s (was %s)", group_num, chans, existing_group.chans
            )
            self.eos.send_command(f"Group {group_num} #")
            self.eos.send_command(chans.eos_command() + " # #")

    def record(
        self,
        group_num: Decimal,
        chans: Sequence | EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Record a group."""
        if not isinstance(chans, EosChanSelection):
            chans = EosChanSelection(chans)

        self.eos.keys.open_tab(EosTab.GROUPS)
        try:
            self.get(group_num)
        except EosError:
            self._create(group_num, chans, label)
        else:
            raise EosError("Group already exists!")

    def record_overwrite(
        self,
        group_num: Decimal,
        chans: Sequence | EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Records a group even if the group already exists."""
        if not isinstance(chans, EosChanSelection):
            chans = EosChanSelection(chans)

        self.eos.keys.open_tab(EosTab.GROUPS)
        try:
            grp = self.get(group_num)
        except EosError:
            self._create(group_num, chans, label)
        else:
            self.update(grp, group_num, chans, label)

    def delete(self, group_num: Decimal) -> None:
        """Delete a group."""
        self.eos.send_command(f"Delete Group {group_num} # #")
        self.eos.osc.handle_messages()
        if self.eos.system.cmd_line_error:
            raise EosCmdLineError(f"Group {group_num} does not exist")
