import logging
import time
from typing import Any, List

from eos.base import EosBase
from eos.types import EosException, EosTab, GroupProperties

logger = logging.getLogger(__name__)


class EosGroups(EosBase):
    def get_group(self, group: float) -> GroupProperties:
        group_data_count = 0
        group_chans = None
        group_props = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal group_data_count
            group_data_count += 1

            if "channels" in addr:
                nonlocal group_chans
                group_chans = args[2:]
            else:
                nonlocal group_props
                group_props = args

        filter = self.dispatcher.map(f"/eos/out/get/group/{group:g}*", handler)
        self.write(f"/eos/get/group/{group:g}")
        self.handle_messages()

        if group_data_count != 2:
            raise EosException(
                f"Didn't receive all data for group ({group_data_count})"
            )

        self.dispatcher.unmap(f"/eos/out/get/group/{group:g}*", filter)
        return GroupProperties.from_list(group, group_props, group_chans)

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
