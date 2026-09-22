"""Eos connection classes."""

import logging
import sys
from typing import Any, Self

from eos.cues import EosCues
from eos.groups import EosGroups
from eos.helpers import EosCmdLineError, EosError
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
from eos.transaction import Transaction

logger = logging.getLogger(__name__)


class Eos:
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

        self.osc.dispatcher.set_default_handler(self._unhandled_message_handler)
        try:
            logger.info("Connected to Eos v%s", self.system.get_version())
        except EosError as e:
            raise RuntimeError("Unable to connect to Eos") from e
        self.osc.write(f"/eos/sc/Connected from {sys.argv[0]}")

    def send_command(self, commandline: str) -> None:
        """Send a full command to Eos."""
        Transaction(
            self.osc,
            query_addr="/eos/newcmd",
            query_data=[commandline],
            resp_filter="/eos/out/cmd",
            num_resps=1,
        ).query()

        if self.system.cmd_line_error:
            self.keys.clear_cmd_line()
            raise EosCmdLineError

    @classmethod
    def tcp_packet_length(cls, ip: str, port: int) -> Self:
        osc = PacketLengthTcpOscConnection(ip=ip, port=port)
        return cls(osc)

    @classmethod
    def tcp_slip(cls, ip: str, port: int) -> Self:
        osc = SlipTcpOscConnection(ip=ip, port=port)
        return cls(osc)

    @classmethod
    def udp(cls, ip: str, rx_port: int, tx_port: int) -> Self:
        osc = UdpOscConnection(ip=ip, rx_port=rx_port, tx_port=tx_port)
        return cls(osc)

    def _unhandled_message_handler(self, addr: str, *args: list[Any]) -> None:
        """Hande messages that are not otherwise handled."""
        logger.debug("Unhandled message: %s, %s", addr, args)
