"""Eos connection classes."""

import logging
import sys
import time
from typing import Any, override

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_packet import OscPacket
from pythonosc.osc_tcp_server import MODE_1_1
from pythonosc.tcp_client import SimpleTCPClient
from pythonosc.udp_client import SimpleUDPClient

from eos.cues import EosCues
from eos.groups import EosGroups
from eos.iterator import (
    EosRefDataIterator,
)
from eos.macros import EosMacros
from eos.system import EosSystem

logger = logging.getLogger(__name__)


class Eos(EosCues, EosSystem, EosGroups, EosMacros):
    """Generic Eos class.

    EosBase is the parent of all mixins, so it is implicity inherited here.
    """

    def __init__(self) -> None:
        """Connect to Eos session."""
        super().__init__()
        self.preset = EosRefDataIterator(self, "preset")
        self.ip = EosRefDataIterator(self, "ip")
        self.bp = EosRefDataIterator(self, "bp")
        self.fp = EosRefDataIterator(self, "fp")
        self.cp = EosRefDataIterator(self, "cp")

        self.write(f"/eos/sc/Connected from {sys.argv[0]}")

        self.dispatcher.set_default_handler(self._unhandledMessageHandler)

        logger.info("Connected to Eos v%s", self.get_version())

    def _unhandledMessageHandler(self, addr: str, *args: list[Any]) -> None:
        """Hande messages that are not otherwise handled."""
        logger.debug("Unhandled message: %s, %s", addr, args)


class EosUDP(Eos):
    """Eos connections over UDP."""

    def __init__(self, ip: str, rx_port: int, tx_port: int) -> None:
        """Connect to an Eos session over UDP.

        Arguments:
            ip: IP of Eos instance
            rx_port: the RX port as described by Eos
            tx_port: the TX port as described by Eos

        """
        self.ip_address = ip
        self.rx_port = rx_port
        self.tx_port = tx_port
        self.dispatcher = Dispatcher()

        # Doesn't seem to work?
        self.server = BlockingOSCUDPServer((self.ip, self.tx_port), self.dispatcher)
        self.client = SimpleUDPClient(self.ip, self.rx_port)

        logger.info("Connected to %s (TX:%s, RX:%s)", self.ip_address, self.tx_port, self.rx_port)
        # Confusion, client only takes one port?

        super().__init__()

    @override
    def write(self, path: str, args: list[str] | None = None) -> None:
        logger.debug(path)
        if args is not None:
            logger.warning("Seemingly don't support arguments for UDP??")
        self.client.send_message(path)


class EosTCP(Eos):
    """Eos connections over TCP."""

    def __init__(self, ip: str, port: int) -> None:
        """Connect to an Eos session over TCP."""
        self.ip_address = ip
        self.port = port
        self.dispatcher = Dispatcher()

        if self.client is None:
            # TODO(eosti): Implement mode detection # noqa: TD003
            raise NotImplementedError("Mode detection TBD")

        super().__init__()

    @override
    def write(self, path: str, args: list[str] | None = None) -> None:
        if args is None:
            logger.debug(path)
            self.client.send_message(path)
        else:
            logger.debug("%s %s", path, args)
            self.client.send_message(path, args)

    @override
    def read_next(self, timeout: int = 30) -> OscPacket:
        msg = self.client.receive(timeout)
        return OscPacket(msg)

    @override
    def handle_messages(self, timeout: float = 0.1, retries: int = 3) -> None:
        count = 0
        msg = self.client.receive(timeout)
        while msg:
            for i in msg:
                self.dispatcher.call_handlers_for_packet(i, (self.ip_address, self.port))
                count += 1
            msg = self.client.receive(timeout)

        if count == 0:
            if retries == 0:
                logger.warning("No messages received!")
            else:
                time.sleep(self.GENERIC_DELAY)
                self.handle_messages(timeout, retries - 1)
        else:
            logger.debug("Processed %i messages", count)


class EosPacketLength(EosTCP):
    """Eos connections over TCP v1.0 Packet Length."""

    def __init__(self, ip: str, port: int) -> None:
        """Connect to an Eos session over TCP v1.0."""
        self.client = SimpleTCPClient(ip, port)
        logger.info("Connected to %s:%s (TCP v1.0 Packet Length)", self.ip_address, self.port)

        super().__init__(ip, port)


class EosSLIP(EosTCP):
    """Eos connections over TCP v1.1 SLIP."""

    def __init__(self, ip: str, port: int) -> None:
        """Connect to an Eos session over TCP v1.1."""
        self.client = SimpleTCPClient(ip, port, mode=MODE_1_1)
        logger.info("Connected to %s:%s (TCP v1.1 SLIP)", ip, port)

        super().__init__(ip, port)
