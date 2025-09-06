import logging
import time
from decimal import Decimal
from typing import Any, List

from eos.base import EosBase
from eos.types import (
    Cue,
    CueProperties,
    EosException,
    EosRange,
    EosTargets,
    RefDataProperties,
)

logger = logging.getLogger(__name__)


class EosRefDataGenerator:
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

    def select(self, num: Decimal) -> None:
        self.eos.write(f"/eos/{self.target}={num}")

    def fire(self, num: Decimal) -> None:
        self.eos.write(f"/eos/{self.target}/fire={num}")

    def label(self, num: Decimal, label: str) -> None:
        self.eos.write(f"/eos/set/{self.target}/{num}/label='{label}'")

    def get_count(self) -> int:
        cnt = self.eos.get_target_count(self.target)
        logger.debug(f"Got {cnt} of {self.target}")
        return cnt

    def get(self, num: Decimal):
        query_str = f"get/{self.target}/{num}"
        return self._getRefDataQuery(query_str)

    def get_by_idx(self, idx: int):
        query_str = f"get/{self.target}/index/{idx}"
        return self._getRefDataQuery(query_str)

    def get_by_uuid(self, uid: str):
        query_str = f"get/{self.target}/uid/{uid}"
        return self._getRefDataQuery(query_str)

    def _getRefDataQuery(self, query_str: str) -> RefDataProperties:
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
