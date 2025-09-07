from abc import ABC
from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum
from typing import Any, Callable, List, Optional, Union

import itertools
# TODO: how to make changing the attributes in CueProperties actually affect the cue?
# Then we could get rid of setters entirely, which would be nice
# Make a custom @property tag that allows for a keycommand or something passed to it

# Use namedtuple for immutable data, like Cue (?) or freeze the dataclass.


class EosException(Exception):
    pass


class EosTimeout(EosException):
    pass


@dataclass
class ReceivedOSC:
    address: str
    typetags: str
    data: List[Any]


class EosChanSelection:
    """Stores ranges as individual channels"""

    def __init__(self, chans: Union[List[Decimal], set[Decimal]]):
        self.chans: set[Decimal] = set(chans)

    def __repr__(self):
        return str(self.chans)

    def __iter__(self):
        for i in self.chans:
            yield i

    def __eq__(self, other):
        if isinstance(other, EosChanSelection):
            return self.chans == other.chans
        return False

    @classmethod
    def from_eos_arg(cls, eos_arg: List[Any]):
        chan_list = []
        for i in eos_arg:
            if isinstance(i, (Decimal, int, float)):
                chan_list += [Decimal(i)]
            elif isinstance(i, str):
                start_num, end_num = i.split("-")
                if start_num.isdecimal() and end_num.isdecimal():
                    chan_list += [Decimal(i) for i in list(range(int(start_num), int(end_num) + 1))]
                else:
                    raise NotImplementedError("Point channels not supported yet")
            else:
                raise NotImplementedError(f"Can't convert type {type(i)}")

        return cls(sorted(chan_list))

    @classmethod
    def from_active_chans(cls, active_chans: str):
        split_str = active_chans.split(",")
        chan_list = []
        for i in split_str:
            chan_list.append(Decimal(i))
        return cls(sorted(chan_list))

    def to_ranges(self) -> list[tuple[Decimal, Decimal]]:
        sorted_chans = sorted(set(self.chans))

        def ranges(i):
            for key, group in itertools.groupby(enumerate(i), lambda t: t[1] - t[0]):
                group = list(group)
                yield group[0][1], group[-1][1]

        return list(ranges(sorted_chans))

    def eos_command(self) -> str:
        """Returns an Eos cmd string that contains all channels in range"""
        command = ""
        for idx, val in enumerate(self.to_ranges()):
            if val[0] == val[1]:
                # Single value
                chanstr = str(val[0])
            else:
                # Range
                chanstr = f"{val[0]} Thru {val[1]}"

            if idx < len(self.chans) - 1:
                # Not the last channel
                chanstr += " +"

            command += " " + chanstr

        return command


@dataclass
class EosActiveChannel:
    """Stores information about the active channel"""
    chan: EosChanSelection
    intens: int
    fixture_type: str
    fixture_version: int

    @classmethod
    def from_args(cls, args: List[Any]):
        if args[0] == "":
            return None
        chan = EosChanSelection.from_active_chans(args[0].split("[")[0])
        intens = int(args[0].split("[")[1].split("]")[0])

        fixture = args[0].split("]")[1]
        fixture_type = fixture.split("@")[0].strip()
        fixture_version = int(fixture.split("@")[1])

        return cls(chan, intens, fixture_type, fixture_version)


@dataclass
class Cue:
    cuelist: int
    cue: Decimal
    part: int = 0
    duration: Optional[int] = None
    percentage: Optional[float] = None

    # Spaces around the / are MANDATORY
    # The :g is needed to print 10, not 10.0
    def cue_format(self) -> str:
        if self.part == 0:
            return f"{self.cuelist:g} / {self.cue:g}"
        else:
            return f"{self.cuelist:g} / {self.cue:g} Part {self.part:g}"

    # TODO: hint return self in 3.11
    @classmethod
    def empty_cue(cls):
        return cls(-1, -1, -1, -1)

    @classmethod
    def fromText(cls, text: str):
        fields = text.split(" ")
        cuelist = int(fields[0].split("/")[0])
        cue = Decimal(fields[0].split("/")[1])

        if len(fields) == 2:
            return cls(cuelist, cue, fields[1])
        else:
            return cls(cuelist, cue, fields[1], float(fields[-1].strip("%")) / 100.0)


@dataclass
class EosProperties(ABC):
    number: Decimal
    # Ignore this field in equality since Eos sometimes doesn't give this value
    index: Optional[int] = field(compare=False)
    uid: str
    label: str

    def __post_init__(self):
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
    uptime: float
    updelay: float
    downtime: float
    downdelay: float
    focustime: float
    focusdelay: float
    colortime: float
    colordelay: float
    beamtime: float
    beamdelay: float

    preheat: bool
    curve: float
    rate: int

    markstr: str
    blockstr: str
    assertstr: str
    links: Union[str, float]

    followtime: float
    hangtime: float
    allfade: bool
    numloops: int
    solo: bool
    timecode: str
    partcount: int
    notes: str
    scene: str
    scene_end: bool
    cuepartindex: int

    fx: Optional[str] = None
    actions: Optional[str] = None
    links2: Optional[str] = None

    @classmethod
    def from_list(cls, cuelist: int, cue: Decimal, part: int, msg: List[Any]):
        return cls(
            cue,
            msg[0],
            msg[1],
            msg[2],
            cuelist,
            part,
            msg[3],
            msg[4],
            msg[5],
            msg[6],
            msg[7],
            msg[8],
            msg[9],
            msg[10],
            msg[11],
            msg[12],
            msg[13],
            msg[14],
            msg[15],
            msg[16],
            msg[17],
            msg[18],
            msg[19],
            msg[20],
            msg[21],
            msg[22],
            msg[23],
            msg[24],
            msg[25],
            msg[26],
            msg[27],
            msg[28],
            msg[29],
            msg[30],
        )


@dataclass
class GroupProperties(EosProperties):
    chans: Optional[EosChanSelection] = None

    @classmethod
    def from_list(cls, grp: Decimal, props: List):
        return cls(grp, props[0], props[1], props[2])


@dataclass
class MacroProperties(EosProperties):
    mode: str
    command: Optional[List[str]] = None

    @classmethod
    def from_list(cls, macro: Decimal, props: List):
        return cls(macro, props[0], props[1], props[2], props[3])


@dataclass
class RefDataProperties(EosProperties):
    absolute: bool
    locked: bool

    chans: Optional[EosChanSelection] = None
    bytype: Optional[EosChanSelection] = None
    fx: Optional[str] = None

    @classmethod
    def from_list(cls, number: Decimal, msg: List[Any]):
        return cls(number, msg[0], msg[1], msg[2], msg[3], msg[4])


@dataclass
class OSCFilter:
    filter_str: str
    callback: Optional[Callable[[ReceivedOSC], Any]] = None

    def do_callback(self, data: ReceivedOSC) -> Any:
        if self.callback is not None:
            return self.callback(data)
        else:
            return data


class EosState(IntEnum):
    BLIND = 0
    LIVE = 1


class EosWheelCategory(IntEnum):
    UNASSIGNED = 0
    INTENSITY = 1
    FOCUS = 2
    COLOR = 3
    IMAGE = 4
    FORM = 5
    SHUTTER = 6


@dataclass
class EosWheel:
    number: int
    name: str
    pretty_value: int
    value: Decimal
    category: EosWheelCategory

    @classmethod
    def from_args(cls, num: int, args: List[Any]):
        name = args[0].split("[")[0].strip()
        pretty_value = int(args[0].split("[")[1].replace("]", ""))

        return cls(
            num, name, pretty_value, Decimal(args[2]), EosWheelCategory(int(args[1]))
        )


"""
Valid iterator targets.
Dict value represents # of OSC messages to get full data
"""
EosTargets = {
    "patch": 0,
    "cuelist": 0,
    "cue": 4,
    "group": 2,
    "macro": 2,
    "sub": 0,
    "preset": 4,
    "ip": 3,
    "fp": 3,
    "cp": 3,
    "bp": 3,
    "curve": 0,
    "fx": 0,
    "snap": 0,
    "pixmap": 0,
    "ms": 0,
}


class EosTab(IntEnum):
    AUGMENT3D = 38
    BEAM_PALATTES = 25
    CHANNELS_TABLE = 1
    CHANNELS_IN_USE = 32
    COLOR_PALETTES = 24
    COLOR_PATHS = 33
    CUES = 16
    CURVES = 21
    CUSTOM_DIRECT_SELECTS = 39
    EFFECT_CHANNELS = 8
    EFFECTS = 13
    ENCODER_MAPS = 40
    FADER_LIST_DISPLAY = 35
    FOCUS_PALETTES = 23
    GROUPS = 17
    INTENSITY_PALETTES = 22
    MACROS = 18
    MAGIC_SHEET = 3
    MAGIC_SHEET_LIST = 14
    MANUAL = 100
    PARK = 20
    PATCH = 12
    PIXEL_MAPS = 9
    PRESETS = 26
    PSD = 2
    SACN_OUTPUT_VIEWER = 37
    SHOW_CONTROL = 11
    SNAPSHOTS = 19
    SUBMASTERS = 15
    ABOUT = 29
    COLOR_PICKER = 27
    COMMAND_HISTORY = 30
    DIRECT_SELECTS = 4
    EFFECT_STATUS = 6
    FADER_CONFIG = 36
    FADERS = 28
    LAMP_CONTROLS = 31
    ML_CONTROLS = 5
    PIXEL_MAP_PREVIEW = 10
    VIRTUAL_KEYBOARD = 7
    DIAGNOSTICS = 99
