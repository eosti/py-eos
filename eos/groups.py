"""Group-related functionality."""

import logging
from collections.abc import Sequence
from decimal import Decimal

from eos.helpers import (
    EosChanSelection,
    EosCmdLineError,
    EosError,
    GroupProperties,
)
from eos.iterator import EosGroupIterator

logger = logging.getLogger(__name__)


class EosGroups(EosGroupIterator):
    """Mixin for group-related actions."""

    def _create(
        self,
        group_num: int | Decimal,
        chans: EosChanSelection,
        label: str | None = None,
    ) -> None:
        """Create a new group without presence checks."""
        if label is not None:
            self.eos.send_command(f"{chans.eos_command()} Record Group {group_num} Label {label}#")
        else:
            self.eos.send_command(f"{chans.eos_command()} Record Group {group_num} #")

    def edit_chans(
        self,
        existing_group: GroupProperties,
        chans: Sequence | EosChanSelection,
    ) -> GroupProperties:
        """Replace an existing group selection with new channels."""
        if not isinstance(chans, EosChanSelection):
            chans = EosChanSelection(chans)

        grp = self.get_by_uid(existing_group.uid)

        if grp.chans != chans:
            logger.debug("Updating group %f channels to %s (was %s)", grp.number, chans, grp.chans)
            self.eos.send_command(f"{chans.eos_command()} Record Group {grp.number} # #")

        return self.get_by_uid(grp.uid)

    def record(
        self,
        group_num: int | Decimal,
        chans: Sequence | EosChanSelection,
        label: str | None = None,
    ) -> GroupProperties:
        """Record a group."""
        if not isinstance(chans, EosChanSelection):
            chans = EosChanSelection(chans)

        try:
            self.get(group_num)
        except EosError:
            self._create(group_num, chans, label)
        else:
            raise EosError("Group already exists!")

        return self.get(group_num)

    def delete(self, group_num: int | Decimal) -> None:
        """Delete a group."""
        self.eos.send_command(f"Delete Group {group_num} # #")
        if self.eos.system.cmd_line_error:
            raise EosCmdLineError(f"Group {group_num} does not exist")
