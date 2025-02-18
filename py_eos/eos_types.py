from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, List, Optional, Union


@dataclass
class ReceivedOSC:
    address: str
    typetags: str
    data: List[Any]


@dataclass
class Cue:
    cuelist: int
    cue: Union[float, int]
    part: int = 0
    duration: Optional[int] = None
    percentage: Optional[float] = None

    # Spaces around the / are MANDATORY
    # The :g is needed to print 10, not 10.0
    def cue_format(self) -> str:
        return f"{self.cuelist:g} / {self.cue:g}"

    # TODO: hint return self in 3.11
    @classmethod
    def empty_cue(cls):
        return cls(-1, -1, -1, -1)

    @classmethod
    def fromText(cls, text: str):
        fields = text.split(" ")
        cuelist = fields[0].split("/")[0]
        cue = fields[0].split("/")[1]

        if len(fields) == 2:
            return cls(cuelist, cue, fields[1])
        else:
            return cls(cuelist, cue, fields[1], float(fields[2].strip("%")) / 100.0)


@dataclass
class CueProperties:
    cuelist: int
    cue: int
    part: int

    # Order matches Eos output
    cueindex: int
    uid: str
    label: str

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
    def from_list(cls, cuelist: int, cue: int, part: int, msg: List[Any]):
        return cls(
            cuelist,
            cue,
            part,
            msg[0],
            msg[1],
            msg[2],
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
class GroupProperties:
    number: float
    uid: str
    label: str
    channels: List[str]

    @classmethod
    def from_list(cls, grp, props: List, chans: List[str]):
        return cls(grp, props[1], props[2], [str(x) for x in chans])

    def chanCommand(self) -> str:
        command = ""
        for idx, val in enumerate(self.channels):
            expandchan = val.replace("-", " Thru ")
            if idx < len(self.channels) - 1:
                expandchan += " + "
            command += " " + expandchan

        return command + " #"


@dataclass
class MacroProperties:
    number: float
    uid: Optional[str]
    label: str
    mode: str
    command: List[str]

    @classmethod
    def from_list(cls, macro: float, props: List, command: List[str]):
        return cls(macro, props[1], props[2], props[3], [str(x) for x in command])


@dataclass
class EosState:
    user: int
    previous_cue: Cue
    active_cue: Cue
    softkeys: List[str]
    showname: str

    @classmethod
    def empty_state(cls):
        return cls(0, Cue.empty_cue(), Cue.empty_cue(), [""], "")


@dataclass
class OSCFilter:
    filter_str: str
    callback: Optional[Callable[[ReceivedOSC], Any]] = None

    def do_callback(self, data: ReceivedOSC) -> Any:
        if self.callback is not None:
            return self.callback(data)
        else:
            return data


EosTargets = (
    "patch",
    "cuelist",
    "cue",
    "group",
    "macro",
    "sub",
    "preset",
    "ip",
    "fp",
    "cp",
    "bp",
    "curve",
    "fx",
    "snap",
    "pixmap",
    "ms",
)


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
