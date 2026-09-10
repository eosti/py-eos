"""Eos connection classes."""

import logging
import sys
from typing import Any

from eos.cues import EosCues
from eos.groups import EosGroups
from eos.helpers import EosCmdLineError, EosError, EosTargets
from eos.iterator import (
    EosRefDataIterator,
)
from eos.keys import EosKeys
from eos.macros import EosMacros
from eos.osc import (
    OscConnection,
    PacketLengthTcpOscConnection,
    SlipTcpOscConnection,
    UdpOscConnection,
)
from eos.system import EosSystem

logger = logging.getLogger(__name__)


class Eos(EosCues, EosSystem, EosGroups, EosMacros):
    """Generic Eos class.

    EosBase is the parent of all mixins, so it is implicity inherited here.
    """

    GENERIC_DELAY = 0.02

    def __init__(self, osc: OscConnection) -> None:
        """Connect to Eos session."""
        self.osc = osc
        self.keys = EosKeys(self)
        self.cues = EosCues(self)
        self.groups = EosGroups(self)
        self.macros = EosMacros(self)
        self.system = EosSystem(self)

        self.preset = EosRefDataIterator(self, "preset")
        self.ip = EosRefDataIterator(self, "ip")
        self.bp = EosRefDataIterator(self, "bp")
        self.fp = EosRefDataIterator(self, "fp")
        self.cp = EosRefDataIterator(self, "cp")

        self.osc.dispatcher.set_default_handler(self._unhandledMessageHandler)
        try:
            logger.info("Connected to Eos v%s", self.system.get_version())
        except EosError as e:
            raise RuntimeError("Unable to connect to Eos") from e
        self.osc.write(f"/eos/sc/Connected from {sys.argv[0]}")

    def send_command(self, commandline: str) -> None:
        """Send a full command to Eos."""
        self.osc.write("/eos/newcmd", [commandline])
        self.osc.handle_messages()
        if self.system.cmd_line_error:
            raise EosCmdLineError

    @classmethod
    def tcp_packet_length(cls, ip: str, port: int) -> None:
        osc = PacketLengthTcpOscConnection(ip=ip, port=port)
        return cls(osc)

    @classmethod
    def tcp_slip(cls, ip: str, port: int) -> None:
        osc = SlipTcpOscConnection(ip=ip, port=port)
        return cls(osc)

    @classmethod
    def udp(cls, ip: str, rx_port: int, tx_port: int) -> None:
        osc = UdpOscConnection(ip=ip, rx_port=rx_port, tx_port=tx_port)
        return cls(osc)

    def _unhandledMessageHandler(self, addr: str, *args: list[Any]) -> None:
        """Hande messages that are not otherwise handled."""
        logger.debug("Unhandled message: %s, %s", addr, args)

    def get_target_count(self, target: str, **kwargs: int) -> int:
        """Get the number of targets of a particular type."""
        if target not in EosTargets:
            raise ValueError("Invalid target %s", target)

        if target == "cue":
            if "cuelist" not in kwargs:
                logger.warning("Cuelist not specified for target count; defaulting to 1")
            query_str = f"get/cue/{kwargs.get('cuelist', 1)}/count"
        else:
            query_str = f"get/{target}/count"

        target_count: int | None = None

        def handler(_: str, *args: list[Any]) -> None:
            nonlocal target_count
            if isinstance(args[0], int):
                target_count = args[0]
            else:
                logger.warning("Uncertain target count conversion %s", args[0])
                target_count = int(args[0])

        osc_filter = self.osc.dispatcher.map(f"/eos/out/{query_str}", handler)
        self.osc.write(f"/eos/{query_str}")
        self.osc.handle_messages()

        if target_count is None:
            raise EosError(f"Unable to get number of targets for {target}")

        self.osc.dispatcher.unmap(f"/eos/out/{query_str}", osc_filter)
        return target_count
