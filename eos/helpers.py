"""Collection of helpers for various Eos things."""

import itertools
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Self, TypeGuard

from eos.enums import EosWheelCategory

# TODO: how to make changing the attributes in CueProperties actually affect the cue?
# Then we could get rid of setters entirely, which would be nice
# Make a custom @property tag that allows for a keycommand or something passed to it

# Use namedtuple for immutable data, like Cue (?) or freeze the dataclass.


class EosError(Exception):
    """Generic Eos exception."""


class EosTimeoutError(EosError):
    """Timeout communicating with Eos."""


class EosCmdLineError(EosError):
    """Command line error exception."""


class EosParsingError(EosError):
    """Error with parsing received data."""


class EosChanSelection:
    """Stores ranges as individual channels."""

    def __init__(self, chans: Sequence[int | Decimal | str]) -> None:
        """Create a new channel selection from list of individual channels."""
        dec_chans = [Decimal(x) for x in chans]
        self.chans: list[Decimal] = sorted(set(dec_chans))

    def __repr__(self) -> str:
        str_chans = [str(x) for x in self.chans]
        return str(str_chans)

    def __iter__(self) -> Iterator[Decimal]:
        yield from self.chans

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EosChanSelection):
            return self.chans == other.chans
        return False

    def __hash__(self) -> int:
        return hash(self.chans)

    @classmethod
    def from_eos_arg(cls, eos_arg: list[Any]) -> Self:
        """Generate a Eos channel selection from an Eos range.

        ex. "1-4 7 9 12-24"
        """
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
    def from_active_chans(cls, active_chans: str) -> Self:
        """Generate an Eos channel selection from the Eos active channels."""
        split_str = active_chans.split(",")
        chan_list = []
        for i in split_str:
            if "-" in i:
                start_val, end_val = i.split("-")
                chan_list.extend(Decimal(x) for x in range(int(start_val), int(end_val) + 1))
            else:
                chan_list.append(Decimal(i))
        return cls(sorted(chan_list))

    def to_ranges(self) -> list[tuple[Decimal, Decimal]]:
        """Convert a list of channels to a list of tuples with inclusive ranges."""
        sorted_chans = sorted(set(self.chans))

        def ranges(i: list) -> Iterator[tuple[Decimal, Decimal]]:
            for _key, group in itertools.groupby(enumerate(i), lambda t: t[1] - t[0]):
                group_list = list(group)
                yield group_list[0][1], group_list[-1][1]

        return list(ranges(sorted_chans))

    def eos_repr(self) -> str:
        """Return the channel selection in an Eos-formatted way."""
        printstr = ""
        for _idx, val in enumerate(self.to_ranges()):
            if val[0] == val[1]:
                # Single value
                printstr += str(val[0])
            else:
                # Range
                printstr += f"{val[0]}>{val[1]}"

            printstr += " "

        return printstr.strip()

    def eos_command(self) -> str:
        """Returns an Eos cmd string that contains all channels in range."""
        command = ""
        ranges = self.to_ranges()
        for idx, val in enumerate(ranges):
            chanstr = str(val[0]) if val[0] == val[1] else f"{val[0]} Thru {val[1]}"
            if idx < len(ranges) - 1:
                # Not the last channel
                chanstr += " +"

            command += " " + chanstr

        return command


@dataclass
class EosActiveChannel:
    """Stores information about the active channel."""

    chan: EosChanSelection
    intens: int
    fixture_type: str
    fixture_version: int

    @classmethod
    def from_args(cls, args: tuple[Any, ...]) -> Self | None:
        if args[0] == "":
            return None
        chan = EosChanSelection.from_active_chans(args[0].split("[")[0])
        intens = int(args[0].split("[")[1].split("]")[0])

        fixture = args[0].split("]")[1]
        if fixture == "":
            fixture_type = "Unpatched"
            fixture_version = -1
        else:
            fixture_type = fixture.split("@")[0].strip()
            try:
                fixture_version = int(fixture.split("@")[1])
            except IndexError:
                fixture_version = -1

        return cls(
            chan=chan, intens=intens, fixture_type=fixture_type, fixture_version=fixture_version
        )


@dataclass
class Cue:
    cuelist: int
    cue: int | Decimal
    part: int = 0
    label: str = ""
    duration: Decimal | None = None
    percentage: Decimal | None = None

    # Spaces around the / are MANDATORY
    # The :g is needed to print 10, not 10.0
    def cue_format(self) -> str:
        if self.part == 0:
            return f"{self.cuelist:g} / {self.cue:g}"
        return f"{self.cuelist:g} / {self.cue:g} Part {self.part:g}"

    @classmethod
    def empty_cue(cls) -> Self:
        return cls(cuelist=-1, cue=-1, part=-1, duration=None, percentage=None)

    @classmethod
    def from_active_cue(cls, text: str) -> Self:
        """Parse cue data from OSC active cue status message."""
        fields = text.split(" ")
        if "/" not in fields[0]:
            cuelist = 0
            cue = 0
        else:
            cuelist = int(fields[0].split("/")[0])
            cue = Decimal(fields[0].split("/")[1])

        return cls(
            cuelist=cuelist,
            cue=cue,
            label=" ".join(fields[1:-2]),
            duration=Decimal(fields[-2]),
            percentage=Decimal(fields[-1].strip("%")) / Decimal(100),
        )

    @classmethod
    def from_nonactive_cue(cls, text: str) -> Self:
        """Parse cue data from OSC active cue status message."""
        fields = text.split(" ")
        duration = Decimal(0) if len(fields) == 1 else Decimal(fields[-1])
        cuelist = int(fields[0].split("/")[0])
        cue = Decimal(fields[0].split("/")[1])

        return cls(cuelist=cuelist, cue=cue, label=" ".join(fields[1:-2]), duration=duration)

    @classmethod
    def from_text(cls, text: str, default_cuelist: int = 0) -> Self:
        """Parse cue data from a passed string like `47` or `4/97`."""
        if "/" in text:
            cuelist = int(text.split("/", maxsplit=1)[0])
            cuenum = Decimal(text.split("/")[1])
        else:
            cuelist = default_cuelist
            cuenum = Decimal(text)

        return cls(cuelist=cuelist, cue=cuenum)


@dataclass
class EosWheel:
    """Eos Wheel dataclass."""

    number: int
    name: str
    pretty_value: int
    value: Decimal
    category: EosWheelCategory

    @classmethod
    def from_args(cls, num: int, args: tuple[Any, ...]) -> Self:
        """Create an EosWheel from OSC arguments."""
        name = args[0].split("[")[0].strip()
        pretty_value = int(args[0].split("[")[1].replace("]", ""))

        return cls(
            number=num,
            name=name,
            pretty_value=pretty_value,
            value=Decimal(args[2]),
            category=EosWheelCategory(int(args[1])),
        )


def is_str_sequence(values: tuple) -> TypeGuard[tuple[str, ...]]:
    """Typing helper to check if all items in a list are strs."""
    return all(isinstance(val, str) for val in values)


def is_decimal_sequence(values: tuple) -> TypeGuard[tuple[str | int | float, ...]]:
    """Typing helper to check if all items in a list are Decimal-able."""
    return all(isinstance(val, str | int | float) for val in values)
