"""OSC synch and subscription functionality."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from eos.transaction import Transaction

if TYPE_CHECKING:
    from eos.eos import Eos

from eos.helpers import (
    Cue,
    CueListProperties,
    CueProperties,
    EosChanSelection,
    EosError,
    EosTargets,
    GroupProperties,
    MacroProperties,
    RefDataProperties,
)

logger = logging.getLogger(__name__)


class EosIterator[T](ABC):
    """Abstract class for a category of data to sync and subscribe to."""

    def __init__(self, eos: "Eos", target: str) -> None:
        """Creates an iterator for a specified target."""
        self.eos = eos
        if target not in EosTargets:
            raise ValueError("%s is not a valid target", target)
        self.target = target

    def __iter__(self) -> Iterator[T]:
        num_items = self.count()
        for i in range(num_items):
            yield self.get_by_idx(i)

    def count(self) -> int:
        """Get count/max index of target."""
        cnt = self.eos.get_target_count(self.target)
        logger.debug("Got %i of %s", cnt, self.target)
        return cnt

    def get(self, num: int | Decimal) -> T:
        """Get a target from the Eos number."""
        query_str = f"get/{self.target}/{num}"
        return self._getQuery(query_str)

    def get_by_idx(self, idx: int) -> T:
        """Get a target from its index number."""
        query_str = f"get/{self.target}/index/{idx}"
        return self._getQuery(query_str)

    def get_by_uid(self, uid: str) -> T:
        """Get a target from its UID."""
        query_str = f"get/{self.target}/uid/{uid}"
        return self._getQuery(query_str)

    def label(self, num: Decimal | int, label: str) -> None:
        """Label a target.

        This function returns immediately, before the label may have applied.
        Avoid `get`ting a target immediately after labelling, or use a GENERIC_DELAY
            before `get`ting to ensure sync.
        """
        self.get(num)
        self.eos.osc.write(f"/eos/set/{self.target}/{num}/label", args=[label])

    @abstractmethod
    def _handle_response(self, resp: list[tuple[str, Any]]) -> T:
        """Handle the results of a query function."""

    def _getQuery(self, query_str: str) -> T:
        """Query Eos for a data and handle the multi-line result."""
        resp = Transaction(
            osc_conn=self.eos.osc,
            query_path=f"/eos/{query_str}",
            query_data=None,
            resp_filter=f"/eos/out/get/{self.target}/*",
            num_resps=EosTargets[self.target],
        ).query()

        return self._handle_response(resp)

    def _genericChanParser(self, _: str, args: list[Any]) -> EosChanSelection:
        """Generic parser for arguments that contain a list of channels."""
        if len(args) <= 2:
            return EosChanSelection(chans=[])

        return EosChanSelection.from_eos_arg(args[2:])

    def _genericLinksParser(self, _: str, args: list[Any]) -> str:
        """Generic parser for arguments that contain a list of links."""
        logger.error("...I didn't think we'd get this far!")
        logger.info(args)
        return ""


class EosRefDataIterator(EosIterator[RefDataProperties]):
    """Iterator class for referenced data (palletes, presets)."""

    def __init__(self, eos: "Eos", target: str) -> None:
        if target not in ["ip", "cp", "bp", "fp", "preset"]:
            raise ValueError(f"Unknown reference data target {target}")

        super().__init__(eos, target)

    def select(self, num: Decimal) -> None:
        """Select the referenced data."""
        self.eos.osc.write(f"/eos/{self.target}={num}")

    def fire(self, num: Decimal) -> None:
        """Fire the referenced data."""
        self.eos.osc.write(f"/eos/{self.target}/fire={num}")

    def _handle_response(self, resp: list[tuple[str, Any]]) -> RefDataProperties:
        chans: EosChanSelection | None = None
        bytype: EosChanSelection | None = None
        fx: list | None = None
        refdata: RefDataProperties | None = None

        for addr, args in resp:
            if "channel" in addr:
                chans = self._genericChanParser(addr, list(args))
            elif "byType" in addr:
                bytype = self._genericChanParser(addr, list(args))
            elif "fx" in addr:
                # Presets only
                fx = self._refDataFXParser(addr, list(args))
            else:
                refdata = self._refDataInfoParser(addr, list(args))

        if refdata is None or chans is None or fx is None:
            raise EosError(f"Not all data present for {self.target}")

        refdata.chans = chans
        refdata.bytype = bytype
        refdata.fx = None
        return refdata

    def _refDataInfoParser(self, addr: str, args: list[Any]) -> RefDataProperties:
        """Parses the info (first packet) for referenced data."""
        if len(args) <= 2:
            logger.debug(args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(addr.split("/")[5])
        try:
            return RefDataProperties.from_list(number, args)
        except IndexError:
            logger.exception(args)
            raise EosError(f"Referenced data {self.target} {number} does not exist!") from None

    def _refDataFXParser(self, _addr: str, args: list[Any]) -> list | None:
        if len(args) <= 2:
            return None

        logger.warning("No logic to parse fx!")
        logger.info(args)
        return None


class EosGroupIterator(EosIterator[GroupProperties]):
    """Iterator class for groups."""

    def __init__(self, eos: "Eos") -> None:
        super().__init__(eos, "group")

    def _handle_response(self, resp: list[tuple[str, Any]]) -> GroupProperties:
        chans: EosChanSelection | None = None
        group: GroupProperties | None = None

        for addr, args in resp:
            if "channels" in addr:
                chans = self._genericChanParser(addr, list(args))
            else:
                group = self._groupInfoParser(addr, list(args))

        if group is None or chans is None:
            raise EosError(f"Not all data present for {self.target}")

        group.chans = chans
        return group

    def _groupInfoParser(self, addr: str, args: list[Any]) -> GroupProperties:
        """Parses the info (first packet) for groups."""
        if len(args) <= 2:
            logger.debug(args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(addr.split("/")[5])
        try:
            return GroupProperties.from_list(number, args)
        except IndexError as e:
            logger.exception(args)
            raise EosError(f"{self.target.capitalize()} {number} does not exist!") from e


class EosMacroIterator(EosIterator[MacroProperties]):
    """Iterator class for macros."""

    def __init__(self, eos: "Eos") -> None:
        super().__init__(eos, "macro")

    def _handle_response(self, resp: list[tuple[str, Any]]) -> MacroProperties:
        command: str | None = None
        macro: MacroProperties | None = None

        for addr, args in resp:
            if "text" in addr:
                command = self._macroTextParser(addr, list(args))
            else:
                macro = self._macroInfoParser(addr, list(args))

        if macro is None or command is None:
            raise EosError(f"Not all data present for {self.target}")

        macro.command = [command]
        return macro

    def _macroTextParser(self, _addr: str, args: list[Any]) -> str:
        """Parses a text argument for macros."""
        if len(args) <= 2:
            logger.debug(args)
            raise EosError("Not able to parse refdata properties")

        return "".join(args[2:])

    def _macroInfoParser(self, addr: str, args: list[Any]) -> MacroProperties:
        """Parses the info (first packet) for macros."""
        if len(args) <= 2:
            logger.debug(args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(addr.split("/")[5])
        try:
            return MacroProperties.from_list(number, args)
        except IndexError as e:
            logger.exception(args)
            raise EosError(f"{self.target.capitalize()} {number} does not exist!") from e


class EosCueListIterator(EosIterator[CueListProperties]):
    """Iterator class for cue lists."""

    def __init__(self, eos: "Eos") -> None:
        super().__init__(eos, "cuelist")

    def _handle_response(self, resp: list[tuple[str, Any]]) -> CueListProperties:
        cuelist: CueListProperties | None = None
        links: str | None = None

        for addr, args in resp:
            if "links" in addr:
                links = self._genericLinksParser(addr, list(args))
            else:
                cuelist = self._cueListInfoParser(addr, list(args))

        if cuelist is None or links is None:
            raise EosError(f"Not all data present for {self.target}")

        cuelist.links = None
        return cuelist

    def _cueListInfoParser(self, addr: str, args: list[Any]) -> CueListProperties:
        """Parses the info (first packet) for cue lists."""
        if len(args) <= 2:
            logger.debug(args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(addr.split("/")[5])
        try:
            return CueListProperties.from_list(number, args)
        except IndexError as e:
            logger.exception(args)
            raise EosError(f"{self.target.capitalize()} {number} does not exist!") from e


class EosCueIterator:
    """Iterator class for cues.

    Note that in most cases, you need to specify a cue list.
    This can be more easily achieved by using `EosCuesIterator`
    """

    def __init__(self, eos: "Eos") -> None:
        self.eos = eos
        self.cuelist = None

    def __iter__(self) -> Iterator[CueProperties]:
        if self.cuelist is None:
            raise ValueError("No cuelist defined.")

        num_items = self.count()
        cuelist = self.cuelist
        for i in range(num_items):
            yield self.get_by_idx(i, cuelist=cuelist)

    def __call__(self, cuelist: int) -> None:
        self.cuelist = cuelist

    def _getQuery(self, query_str: str) -> CueProperties:
        """Query Eos for a data and handle the multi-line result."""
        resp = Transaction(
            osc_conn=self.eos.osc,
            query_path=f"/eos/{query_str}",
            query_data=None,
            resp_filter="/eos/out/get/cue/*",
            num_resps=EosTargets["cue"],
        ).query()
        return self._handle_response(resp)

    def count(self, cuelist: int | None = None) -> int:
        if cuelist is None:
            if self.cuelist is None:
                raise ValueError("No cuelist defined")
            cnt = self.eos.get_target_count("cue", cuelist=self.cuelist)
        else:
            cnt = self.eos.get_target_count("cue", cuelist=cuelist)

        logger.debug("Got %i of cues", cnt)
        return cnt

    def get(self, cue: Decimal) -> CueProperties:
        """Get a cue from a cuelist by number.

        Probably won't handle parts gracefully.
        """
        query_str = f"get/cue/{self.cuelist}/{cue}"
        return self._getQuery(query_str)

    def get_cue(self, cue: Cue, retry: int = 4) -> CueProperties:
        """Get a cue with explicit cue list/cue number/part number."""
        query_str = f"get/cue/{cue.cuelist}/{cue.cue:g}/{cue.part}"
        return self._getQuery(query_str)

    def get_by_uid(self, uid: str) -> CueProperties:
        """Get a target from its UID."""
        query_str = f"get/cue/uid/{uid}"
        return self._getQuery(query_str)

    def get_by_idx(self, idx: int, cuelist: int | None = None) -> CueProperties:
        """Get a cue from a cuelist by index."""
        if cuelist is None and self.cuelist is None:
            raise ValueError("No cuelist defined")

        if cuelist is None:
            query_str = f"get/cue/{self.cuelist}/index/{idx}"
        else:
            query_str = f"get/cue/{cuelist}/index/{idx}"

        return self._getQuery(query_str)

    def _handle_response(self, resp: list[tuple[str, Any]]) -> CueProperties:
        cue: CueProperties | None = None
        fx: list | None = None
        links: list | None = None
        actions: list | None = None

        for addr, args in resp:
            if "fx" in addr:
                fx = self._cueFXParser(addr, list(args))
            elif "links" in addr:
                links = self._cueLinksParser(addr, list(args))
            elif "actions" in addr:
                actions = self._cueActionsParser(addr, list(args))
            else:
                # Assume this one comes in first
                cue = self._cueInfoParser(addr, list(args))

        if cue is None:
            raise EosError("Not all data present for cue")

        cue.fx = fx
        cue.links = links
        cue.actions = actions
        return cue

    def _cueInfoParser(self, addr: str, args: list[Any]) -> CueProperties:
        """Parse the info (first packet) for cues."""
        cuelist = int(addr.split("/")[5])
        cue = Decimal(addr.split("/")[6])
        cuepart = int(addr.split("/")[7])
        try:
            return CueProperties.from_list(cuelist, cue, cuepart, args)
        except IndexError as e:
            logger.exception(addr)
            logger.exception(args)
            raise EosError(f"Cue {cuelist}/{cue} Part {cuepart} does not exist!") from e

    def _cueFXParser(self, _addr: str, args: list[Any]) -> list | None:
        """Parse the FX present in a cue."""
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse FX")
        return None

    def _cueLinksParser(self, _addr: str, args: list[Any]) -> list | None:
        """Parse the links present in a cue."""
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse Links")
        return None

    def _cueActionsParser(self, _addr: str, args: list[Any]) -> list | None:
        """Parse the actions present in a cue."""
        if len(args) <= 2:
            # No links
            return None

        logger.warning("No logic to parse actions")
        return None
