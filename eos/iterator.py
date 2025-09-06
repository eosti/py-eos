from abc import ABC, abstractmethod
from eos.base import EosBase, EosTargets
from eos.types import EosProperties, RefDataProperties, EosException, EosRange, CueProperties, Cue
from decimal import Decimal
from typing import List, Any
import logging

logger = logging.getLogger(__name__)


class EosIterator(ABC):
    def __init__(self, eos: EosBase, target: str):
        self.eos = eos
        self.target = target
        assert self.target in EosTargets

    def __iter__(self):
        self.num_items = self.get_count()
        self.cur_item = 0
        return self

    def __next__(self):
        if self.cur_item >= self.num_items:
            raise StopIteration

        item = self.get_by_idx(self.cur_item)
        self.cur_item += 1
        return item

    def get_count(self) -> int:
        cnt = self.eos.get_target_count(self.target)
        logger.debug(f"Got {cnt} of {self.target}")
        return cnt

    def get(self, num: Decimal) -> EosProperties:
        """Get a target from the Eos number"""
        query_str = f"get/{self.target}/{num}"
        return self._getQuery(query_str)

    def get_by_idx(self, idx: int) -> EosProperties:
        """Get a target from its index number"""
        query_str = f"get/{self.target}/index/{idx}"
        return self._getQuery(query_str)

    def get_by_uuid(self, uid: str) -> EosProperties:
        """Get a target from its UID"""
        query_str = f"get/{self.target}/uid/{uid}"
        return self._getQuery(query_str)

    def label(self, num: Decimal, label: str) -> None:
        self.eos.write(f"/eos/set/{self.target}/{num}/label='{label}'")

    @abstractmethod
    def _getQuery(self, query_str: str) -> EosProperties:
        pass


class EosRefDataIterator(EosIterator):
    def __init__(self, eos: EosBase, target: str):
        if target not in ["ip", "cp", "bp", "fp", "preset"]:
            raise ValueError(f"Unknown reference data target {target}")

        super().__init__(eos, target)

    def select(self, num: Decimal) -> None:
        self.eos.write(f"/eos/{self.target}={num}")

    def fire(self, num: Decimal) -> None:
        self.eos.write(f"/eos/{self.target}/fire={num}")

    def _getQuery(self, query_str: str) -> RefDataProperties:
        data_count = 0
        output_data = None

        def handler(addr: str, *args: List[Any]) -> None:
            nonlocal data_count
            nonlocal output_data
            data_count += 1

            if "channel" in addr:
                output_data.chans = self._refDataChanParser(addr, list(args))
            elif "byType" in addr:
                output_data.bytype = self._refDataByTypeParser(addr, list(args))
            elif "fx" in addr:
                # Presets only
                output_data.fx = self._refDataFXParser(addr, list(args))
            else:
                output_data = self._refDataInfoParser(addr, list(args))

        filter = self.eos.dispatcher.map(f"/eos/out/get/{self.target}*", handler)
        self.eos.write(f"/eos/{query_str}")
        self.eos.handle_messages()
        if data_count < 3:
            raise EosException(
                f"Didn't receive all data for referenced data ({data_count})"
            )
        self.eos.dispatcher.unmap(f"/eos/out/get/{self.target}*", filter)
        return output_data

    def _refDataInfoParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            return None

        number = addr.split("/")[5]
        try:
            return RefDataProperties.from_list(number, args)
        except IndexError:
            logger.error(args)
            raise EosException(
                f"Referenced data {self.target} {number} does not exist!"
            )

    def _refDataChanParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            return None

        chan_list = []
        for i in args[2:]:
            chan_list += EosRange(i).to_individual()
        return chan_list

    def _refDataByTypeParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            return None

        chan_list = []
        for i in args[2:]:
            chan_list += EosRange(i).to_individual()
        return chan_list

    def _refDataFXParser(self, addr: str, args: List[Any]):
        if len(args) <= 2:
            return None

        logger.warning("No logic to parse fx!")
        logger.info(args)


class EosCueIterator(EosIterator):
    def __init__(self, eos: EosBase):
        super().__init__(eos, "cue")

    def get_count(self) -> int:
        raise NotImplementedError("Please use EosCuesIterator")

    def get(self, num: Decimal):
        raise NotImplementedError("Please use `get_cue` or use EosCuesIterator")

    def get_cue(self, cue: Cue) -> CueProperties:
        query_str = f"get/cue/{cue.cuelist}/{cue.cue:g}/{cue.part}"
        return self._getCueQuery(query_str)

    def get_by_idx(self, idx: int):
        raise NotImplementedError("Please use EosCuesIterator")

    def _getQuery(self, query_str: str) -> CueProperties:
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

        filter = self.eos.dispatcher.map("/eos/out/get/cue/*", handler)
        self.eos.write(f"/eos/{query_str}")
        self.eos.handle_messages()
        if cue_data_count != 4:
            raise EosException(f"Didn't receive all data for cue ({cue_data_count})")
        self.eos.dispatcher.unmap("/eos/out/get/cue/*", filter)
        return output_cue

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


class EosCuesIterator(EosCueIterator):
    def __init__(self, eos: EosBase, cuelist: int):
        self.cuelist = cuelist
        super().__init__(eos)

    def get_count(self) -> int:
        cnt = self.eos.get_target_count(self.target, cuelist=self.cuelist)
        logger.debug(f"Got {cnt} of {self.target}")
        return cnt

    def get(self, num: Decimal) -> CueProperties:
        # probably won't handle parts gracefully
        query_str = f"get/{self.target}/{self.cuelist}/{num}"
        return self._getQuery(query_str)

    def get_by_idx(self, idx: int) -> CueProperties:
        query_str = f"get/{self.target}/{self.cuelist}/index/{idx}"
        return self._getQuery(query_str)
