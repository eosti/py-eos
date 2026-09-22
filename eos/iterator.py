"""OSC synch and subscription functionality."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from decimal import Decimal
from typing import TYPE_CHECKING

from eos.transaction import OscResponse, Transaction

if TYPE_CHECKING:
    from eos.eos import Eos

from eos.enums import EosTargets
from eos.helpers import (
    Cue,
    EosChanSelection,
    EosError,
    EosParsingError,
)
from eos.properties import (
    CueListProperties,
    CueProperties,
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
        """Get the number of targets of a particular type."""
        if self.target == "cue":
            raise NotImplementedError

        resp = Transaction(
            osc_conn=self.eos.osc,
            query_addr=f"/eos/get/{self.target}/count",
            query_data=None,
            resp_filter=f"/eos/out/get/{self.target}/count",
            num_resps=1,
        ).query()

        if not isinstance(resp[0].args[0], int):
            logger.warning("Uncertain target count conversion %s", resp[0].args[0])
            target_count = int(resp[0].args[0])
        else:
            target_count = resp[0].args[0]

        logger.debug("Got %i of %s", target_count, self.target)
        return target_count

    def get(self, num: int | Decimal) -> T:
        """Get a target from the Eos number."""
        query_str = f"get/{self.target}/{num}"
        return self._get_query(query_str)

    def get_by_idx(self, idx: int) -> T:
        """Get a target from its index number."""
        query_str = f"get/{self.target}/index/{idx}"
        return self._get_query(query_str)

    def get_by_uid(self, uid: str) -> T:
        """Get a target from its UID."""
        query_str = f"get/{self.target}/uid/{uid}"
        return self._get_query(query_str)

    def label(self, num: Decimal | int, label: str) -> None:
        """Label a target.

        This function returns immediately, before the label may have applied.
        Avoid `get`ting a target immediately after labelling, or use a GENERIC_DELAY
            before `get`ting to ensure sync.
        """
        self.get(num)
        self.eos.osc.write(f"/eos/set/{self.target}/{num}/label", args=[label])

    @abstractmethod
    def _handle_response(self, resp: list[OscResponse]) -> T:
        """Handle the results of a query function."""

    def _get_query(self, query_str: str) -> T:
        """Query Eos for a data and handle the multi-line result."""
        resp = Transaction(
            osc_conn=self.eos.osc,
            query_addr=f"/eos/{query_str}",
            query_data=None,
            resp_filter=f"/eos/out/get/{self.target}/*",
            num_resps=EosTargets[self.target],
        ).query()

        return self._handle_response(resp)

    def _generic_chan_parser(self, resp: OscResponse) -> EosChanSelection:
        """Generic parser for arguments that contain a list of channels."""
        if len(resp.args) <= 2:
            return EosChanSelection(chans=[])

        return EosChanSelection.from_eos_arg(resp.args[2:])

    def _generic_links_parser(self, resp: OscResponse) -> list[str] | None:
        """Generic parser for arguments that contain a list of links."""
        if len(resp.args) <= 2:
            return None

        return resp.args[2:]


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

    def _handle_response(self, resp: list[OscResponse]) -> RefDataProperties:
        chans: EosChanSelection | None = None
        bytype: EosChanSelection | None = None
        fx: list | None = None
        refdata: RefDataProperties | None = None

        for r in resp:
            if "channel" in r.addr:
                chans = self._generic_chan_parser(r)
            elif "byType" in r.addr:
                bytype = self._generic_chan_parser(r)
            elif "fx" in r.addr:
                # Presets only
                fx = self._refdata_fx_parser(r)
            else:
                refdata = self._refdata_info_parser(r)

        if refdata is None or chans is None or fx is None:
            raise EosError(f"Not all data present for {self.target}")

        refdata.chans = chans
        refdata.bytype = bytype
        refdata.fx = None
        return refdata

    def _refdata_info_parser(self, resp: OscResponse) -> RefDataProperties:
        """Parses the info (first packet) for referenced data."""
        if len(resp.args) <= 2:
            logger.debug(resp.args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(resp.addr.split("/")[5])
        try:
            return RefDataProperties.from_list(number, resp.args)
        except IndexError:
            logger.exception(resp.args)
            raise EosError(f"Referenced data {self.target} {number} does not exist!") from None

    def _refdata_fx_parser(self, resp: OscResponse) -> list | None:
        if len(resp.args) <= 2:
            return None

        return resp.args[2:]


class EosGroupIterator(EosIterator[GroupProperties]):
    """Iterator class for groups."""

    def __init__(self, eos: "Eos") -> None:
        super().__init__(eos, "group")

    def _handle_response(self, resp: list[OscResponse]) -> GroupProperties:
        chans: EosChanSelection | None = None
        group: GroupProperties | None = None

        for r in resp:
            if "channels" in r.addr:
                chans = self._generic_chan_parser(r)
            else:
                group = self._group_info_parser(r)

        if group is None or chans is None:
            raise EosError(f"Not all data present for {self.target}")

        group.chans = chans
        return group

    def _group_info_parser(self, resp: OscResponse) -> GroupProperties:
        """Parses the info (first packet) for groups."""
        if len(resp.args) <= 2:
            logger.debug(resp.args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(resp.addr.split("/")[5])
        try:
            return GroupProperties.from_list(number, resp.args)
        except IndexError as e:
            logger.exception(resp.args)
            raise EosError(f"{self.target.capitalize()} {number} does not exist!") from e


class EosMacroIterator(EosIterator[MacroProperties]):
    """Iterator class for macros."""

    def __init__(self, eos: "Eos") -> None:
        super().__init__(eos, "macro")

    def _handle_response(self, resp: list[OscResponse]) -> MacroProperties:
        command: str | None = None
        macro: MacroProperties | None = None

        for r in resp:
            if "text" in r.addr:
                command = self._macro_text_parser(r)
            else:
                macro = self._macro_info_parser(r)

        if macro is None or command is None:
            raise EosError(f"Not all data present for {self.target}")

        macro.command = [command]
        return macro

    def _macro_text_parser(self, resp: OscResponse) -> str:
        """Parses a text argument for macros."""
        if len(resp.args) <= 2:
            logger.debug(resp.args)
            raise EosError("Not able to parse refdata properties")

        return "".join(resp.args[2:])

    def _macro_info_parser(self, resp: OscResponse) -> MacroProperties:
        """Parses the info (first packet) for macros."""
        if len(resp.args) <= 2:
            logger.debug(resp.args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(resp.addr.split("/")[5])
        try:
            return MacroProperties.from_list(number, resp.args)
        except IndexError as e:
            logger.exception(resp.args)
            raise EosError(f"{self.target.capitalize()} {number} does not exist!") from e


class EosCueListIterator(EosIterator[CueListProperties]):
    """Iterator class for cue lists."""

    def __init__(self, eos: "Eos") -> None:
        super().__init__(eos, "cuelist")

    def _handle_response(self, resp: list[OscResponse]) -> CueListProperties:
        cuelist: CueListProperties | None = None
        links: str | None = None

        for r in resp:
            if "links" in r.addr:
                links = self._generic_links_parser(r)
            else:
                cuelist = self._cuelist_info_parser(r)

        if cuelist is None or links is None:
            raise EosError(f"Not all data present for {self.target}")

        cuelist.links = None
        return cuelist

    def _cuelist_info_parser(self, resp: OscResponse) -> CueListProperties:
        """Parses the info (first packet) for cue lists."""
        if len(resp.args) <= 2:
            logger.debug(resp.args)
            raise EosError("Not able to parse refdata properties")

        number = Decimal(resp.addr.split("/")[5])
        try:
            return CueListProperties.from_list(number, resp.args)
        except IndexError as e:
            logger.exception(resp.args)
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

    def _get_query(self, query_str: str) -> CueProperties:
        """Query Eos for a data and handle the multi-line result."""
        resp = Transaction(
            osc_conn=self.eos.osc,
            query_addr=f"/eos/{query_str}",
            query_data=None,
            resp_filter="/eos/out/get/cue/*",
            num_resps=EosTargets["cue"],
        ).query()
        return self._handle_response(resp)

    def count(self, cuelist: int | None = None) -> int:
        if cuelist is None:
            if self.cuelist is None:
                raise ValueError("No cuelist defined")
            cuelist = self.cuelist

        resp = Transaction(
            osc_conn=self.eos.osc,
            query_addr=f"/eos/get/cue/{cuelist}/count",
            query_data=None,
            resp_filter=f"/eos/out/get/cue/{cuelist}/count",
            num_resps=1,
        ).query()

        if not isinstance(resp[0].args[0], int):
            logger.warning("Uncertain target count conversion %s", resp[0].args[0])
            target_count = int(resp[0].args[0])
        else:
            target_count = resp[0].args[0]

        logger.debug("Got %i of cues", target_count)
        return target_count

    def get(self, cue: Decimal) -> CueProperties:
        """Get a cue from a cuelist by number.

        Probably won't handle parts gracefully.
        """
        if self.cuelist is None:
            raise ValueError("No default cuelist set")

        full_cue = Cue(self.cuelist, cue)
        return self.get_cue(full_cue)

    def get_cue(self, cue: Cue) -> CueProperties:
        """Get a cue with explicit cue list/cue number/part number."""
        query_str = f"get/cue/{cue.cuelist}/{cue.cue:g}/{cue.part}"
        return self._get_query(query_str)

    def get_by_uid(self, uid: str) -> CueProperties:
        """Get a target from its UID."""
        query_str = f"get/cue/uid/{uid}"
        return self._get_query(query_str)

    def get_by_idx(self, idx: int, cuelist: int | None = None) -> CueProperties:
        """Get a cue from a cuelist by index."""
        if cuelist is None and self.cuelist is None:
            raise ValueError("No cuelist defined")

        if cuelist is None:
            query_str = f"get/cue/{self.cuelist}/index/{idx}"
        else:
            query_str = f"get/cue/{cuelist}/index/{idx}"

        return self._get_query(query_str)

    def _handle_response(self, resp: list[OscResponse]) -> CueProperties:
        cue: CueProperties | None = None
        fx: list[str] | None = None
        links: list[str] | None = None
        actions: list[str] | None = None

        for r in resp:
            if "fx" in r.addr:
                fx = self._cue_fx_parser(r)
            elif "links" in r.addr:
                links = self._cue_links_parser(r)
            elif "actions" in r.addr:
                actions = self._cue_actions_parser(r)
            else:
                # Assume this one comes in first
                cue = self._cue_info_parser(r)

        if cue is None:
            raise EosParsingError("Not all data present for cue")

        cue.fx = fx
        cue.links = links
        cue.actions = actions
        return cue

    def _cue_info_parser(self, resp: OscResponse) -> CueProperties:
        """Parse the info (first packet) for cues."""
        cuelist = int(resp.addr.split("/")[5])
        cue = Decimal(resp.addr.split("/")[6])
        cuepart = int(resp.addr.split("/")[7])
        try:
            return CueProperties.from_list(cuelist, cue, cuepart, resp.args)
        except IndexError as e:
            logger.exception(resp.addr)
            logger.exception(resp.args)
            raise EosError(f"Cue {cuelist}/{cue} Part {cuepart} does not exist!") from e

    def _cue_fx_parser(self, resp: OscResponse) -> list[str] | None:
        """Parse the FX present in a cue."""
        if len(resp.args) <= 2:
            # No links
            return None

        return resp.args[2:]

    def _cue_links_parser(self, resp: OscResponse) -> list[str] | None:
        """Parse the links present in a cue."""
        if len(resp.args) <= 2:
            # No links
            return None

        return resp.args[2:]

    def _cue_actions_parser(self, resp: OscResponse) -> list[str] | None:
        """Parse the actions present in a cue."""
        if len(resp.args) <= 2:
            # No links
            return None

        return resp.args[2:]
