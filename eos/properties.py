from abc import ABC
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Self

from eos.helpers import Cue, EosChanSelection


@dataclass
class EosProperties(ABC):
    number: Decimal
    # Ignore this field in equality since Eos sometimes doesn't give this value
    index: int | None = field(compare=False)
    uid: str
    label: str

    def __post_init__(self) -> None:
        if self.index == -1:
            # Eos may "optimize" out the index number to -1 unless you query by index
            self.index = None
        if not isinstance(self.number, Decimal):
            self.number = Decimal(self.number)


@dataclass
class CueProperties(EosProperties):
    cuelist: int
    part: int

    # Order matches Eos output
    uptime: Decimal
    updelay: Decimal
    downtime: Decimal
    downdelay: Decimal
    focustime: Decimal
    focusdelay: Decimal
    colortime: Decimal
    colordelay: Decimal
    beamtime: Decimal
    beamdelay: Decimal

    preheat: bool
    curve: float
    rate: int

    markstr: str
    blockstr: str
    assertstr: str
    links: str | float

    followtime: Decimal
    hangtime: Decimal
    allfade: bool
    numloops: int
    solo: bool
    timecode: str
    partcount: int
    notes: str
    scene: str
    scene_end: bool
    cuepartindex: int

    fx: list[str] | None = None
    actions: list[str] | None = None
    links2: list[Cue] | None = None

    @classmethod
    def from_list(cls, cuelist: int, cue: Decimal, part: int, msg: list[Any]) -> Self:
        return cls(
            cue,
            msg[0],
            msg[1],
            msg[2],
            cuelist=cuelist,
            part=part,
            uptime=Decimal(msg[3]) / Decimal(1000),
            updelay=Decimal(msg[4]) / Decimal(1000),
            downtime=Decimal(msg[5]) / Decimal(1000),
            downdelay=Decimal(msg[6]) / Decimal(1000),
            focustime=Decimal(msg[7]) / Decimal(1000),
            focusdelay=Decimal(msg[8]) / Decimal(1000),
            colortime=Decimal(msg[9]) / Decimal(1000),
            colordelay=Decimal(msg[10]) / Decimal(1000),
            beamtime=Decimal(msg[11]) / Decimal(1000),
            beamdelay=Decimal(msg[12]) / Decimal(1000),
            preheat=msg[13],
            curve=msg[14],
            rate=msg[15],
            markstr=msg[16],
            blockstr=msg[17],
            assertstr=msg[18],
            links=msg[19],
            followtime=Decimal(msg[20]) / Decimal(1000),
            hangtime=Decimal(msg[21]) / Decimal(1000),
            allfade=msg[22],
            numloops=msg[23],
            solo=msg[24],
            timecode=msg[25],
            partcount=msg[26],
            notes=msg[27],
            scene=msg[28],
            scene_end=msg[29],
            cuepartindex=msg[30],
        )


@dataclass
class GroupProperties(EosProperties):
    chans: EosChanSelection | None = None

    @classmethod
    def from_list(cls, grp: Decimal, props: list) -> Self:
        return cls(grp, props[0], props[1], props[2])


@dataclass
class MacroProperties(EosProperties):
    mode: str
    command: list[str] | None = None

    @classmethod
    def from_list(cls, macro: Decimal, props: list) -> Self:
        return cls(macro, props[0], props[1], props[2], props[3])


@dataclass
class RefDataProperties(EosProperties):
    """Collection of properties for referenced data."""

    absolute: bool
    locked: bool

    chans: EosChanSelection | None = None
    bytype: EosChanSelection | None = None
    fx: str | None = None

    @classmethod
    def from_list(cls, number: Decimal, props: tuple[Any, ...]) -> Self:
        """Create a RefDataProperties from a list of properties."""
        return cls(number, *props)


@dataclass
class CueListProperties(EosProperties):
    """Collection of properties from a cue list."""

    playback_mode: str
    fader_mode: str
    independent: bool
    htp: bool
    assert_state: bool
    block: bool
    background: bool
    solo_mode: bool
    timecode_list: int
    oos_sync: bool

    links: list[int] | None = None

    @classmethod
    def from_list(cls, number: Decimal, props: tuple[Any, ...]) -> Self:
        """Create a CueListProperties from a list of properties."""
        return cls(number, *props)
