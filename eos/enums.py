from enum import IntEnum


class EosState(IntEnum):
    """Enum mapping Eos state to ints."""

    BLIND = 0
    LIVE = 1


class EosWheelCategory(IntEnum):
    """Enum mapping Eos wheel categories to ints."""

    UNASSIGNED = 0
    INTENSITY = 1
    FOCUS = 2
    COLOR = 3
    IMAGE = 4
    FORM = 5
    SHUTTER = 6


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
    """Enum mapping tab names to tab numbers."""

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
