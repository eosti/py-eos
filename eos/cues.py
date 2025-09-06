import logging
import time
from typing import Any, List

from eos.base import EosBase
from eos.types import Cue, CueProperties, EosException

logger = logging.getLogger(__name__)


class EosCues(EosBase):
    def __init__(self):
        self.dispatcher.map("/eos/out/previous/cue*", self._updatePreviousCueHandler)
        self.dispatcher.map("/eos/out/active/cue*", self._updateActiveCueHandler)
        self.dispatcher.map("/eos/out/pending/cue*", self._updatePendingCueHandler)

    def get_cue(self, cue: Cue) -> CueProperties:
        query_str = f"get/cue/{cue.cuelist}/{cue.cue:g}/{cue.part}"
        return self._getCueQuery(query_str)

    def get_cue_by_uid(self, uid: str) -> CueProperties:
        query_str = f"get/cue/uid/{uid}"
        return self._getCueQuery(query_str)

    def get_cue_by_index(self, index: int, cuelist: int = 1) -> CueProperties:
        query_str = f"get/cue/{cuelist}/index/{index}"
        return self._getCueQuery(query_str)

    def _getCueQuery(self, query_str: str) -> CueProperties:
        cue_data_count = 0
        output_cue = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal cue_data_count
            nonlocal output_cue
            cue_data_count += 1

            if "fx" in addr:
                output_cue.fx = self._cueFXParser(addr, list(args))
            elif "links" in addr:
                output_cue.links2 = self._cueLinksParser(addr, list(args))
            elif "actions" in addr:
                output_cue.actions = self._cueActionsParser(addr, list(args))
            else:
                # Assume this one comes in first
                output_cue = self._cueInfoParser(addr, list(args))

        filter = self.dispatcher.map(f"/eos/out/{query_str}*", handler)
        self.write(f"/eos/{query_str}")
        self.handle_messages()
        if cue_data_count != 4:
            raise EosException(f"Didn't receive all data for cue ({cue_data_count})")
        self.dispatcher.unmap(f"/eos/out/{query_str}*", filter)
        return output_cue

    def _updatePreviousCueHandler(self, addr: str, *args: List[Any]) -> None:
        logger.debug(f"prev cue: {addr} {args}")
        if len(args) == 0 or args[0] == "":
            self.previousCue = None
        elif "text" in addr:
            self.previousCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updateActiveCueHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0 or args[0] == "":
            self.activeCue = None
        elif "text" in addr:
            self.activeCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _updatePendingCueHandler(self, addr: str, *args: List[Any]) -> None:
        if len(args) == 0 or args[0] == "":
            self.pendingCue = None
        elif "text" in addr:
            self.pendingCue = Cue.fromText(args[0])
        else:
            # Redundant info, skip it
            pass

    def _cueInfoParser(self, addr: str, args: List[Any]) -> CueProperties:
        cuelist = addr.split("/")[5]
        cue = addr.split("/")[6]
        cuepart = addr.split("/")[7]
        try:
            return CueProperties.from_list(cuelist, cue, cuepart, args)
        except IndexError:
            logger.error(args)
            raise EosException(f"Cue {cuelist}/{cue} Part {cuepart} does not exist!")

    def _cueFXParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse FX")

    def _cueLinksParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse Links")

    def _cueActionsParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse actions")

    def record_cue(self, cue: Cue) -> None:
        self.blind()
        if cue.part != 0:
            raise ValueError("cue must have part zero")
        try:
            self.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
            time.sleep(0.05)
        # Otherwise, cue already exists!

    def record_part(self, cue: Cue, part) -> Cue:
        # TODO: how to do this not in blind too, or at least restore state?
        self.blind()
        cue.part = part
        try:
            self.get_cue(cue)
        except EosException:
            self.send_command(f"Cue {cue.cue_format()} # #")
            time.sleep(0.05)

        return cue

    def intensity_block_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "I" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Intensity Block #")

    def block_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "B" in props.blockstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Block #")

    def assert_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "A" in props.assertstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Assert #")

    def mark_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "M" in props.markstr or "m" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark #")

    def mark_high_cue(self, cue: Cue) -> None:
        # TODO check if "Mark" is in softkeys to see if Automark on
        props = self.get_cue(cue)
        if "Mh" in props.markstr or "mh" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark High_Priority #")

    def mark_low_cue(self, cue: Cue) -> None:
        props = self.get_cue(cue)
        if "Ml" in props.markstr or "ml" in props.markstr:
            return
        self.send_command(f"Cue {cue.cue_format()} Mark Low_Priority #")

    def label_cue(self, cue: Cue, label: str) -> None:
        props = self.get_cue(cue)
        if props.label != label:
            logging.info(
                f"Updating cue {cue.cue_format()} label from {props.label} to {label}"
            )
            self.send_command(f"Cue {cue.cue_format()} Label {label}")
            self.enter()

    def set_time(self, cue: Cue, cuetime: float) -> None:
        self.send_command(f"Cue {cue.cue_format()} Time {cuetime} #")

    def add_scene(self, cue: Cue, scene: str) -> None:
        props = self.get_cue(cue)
        if props.scene != "" and props.scene != scene:
            logging.warning(f"Renaming scene on {cue.cue_format()} ({props.scene})")
        self.send_command(f"Cue {cue.cue_format()} Scene {scene}")
        self.enter()
