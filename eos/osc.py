import logging
import time
from abc import ABC, abstractmethod
from typing import override

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_packet import OscPacket
from pythonosc.osc_tcp_server import MODE_1_1
from pythonosc.tcp_client import SimpleTCPClient
from pythonosc.udp_client import SimpleUDPClient

logger = logging.getLogger(__name__)


class OscConnection(ABC):
    @property
    def dispatcher(self):
        return self._dispatcher

    @abstractmethod
    def write(self, path: str, args: list[str | int | float | bool] | None = None) -> None:
        """Write an OSC string to Eos."""

    @abstractmethod
    def read_next(self, timeout: int = 30) -> OscPacket:
        """Read the next message in the queue."""

    @abstractmethod
    def handle_messages(self, timeout: float = 0.1) -> None:
        """Read all messages in queue and execute associated handlers."""


class UdpOscConnection(OscConnection):
    """Eos connections over UDP."""

    def __init__(self, ip: str, rx_port: int, tx_port: int, generic_delay: float = 0) -> None:
        """Connect to an Eos session over UDP.

        Arguments:
            ip: IP of Eos instance
            rx_port: the RX port as described by Eos
            tx_port: the TX port as described by Eos

        """
        self.ip_address = ip
        self.rx_port = rx_port
        self.tx_port = tx_port
        self.generic_delay = generic_delay
        self._dispatcher = Dispatcher()

        # Doesn't seem to work?
        # but I need to use two ports in Eos?
        self.client = SimpleUDPClient(self.ip_address, self.rx_port)

        logger.info("Connected to %s (TX:%s, RX:%s)", self.ip_address, self.tx_port, self.rx_port)
        # Confusion, client only takes one port?
        raise NotImplementedError

        super().__init__()

    @override
    def write(self, path: str, args: list[str | int | float | bool] | None = None) -> None:
        logger.debug(path)
        if args is not None:
            logger.warning("Seemingly don't support arguments for UDP??")
        self.client.send_message(path, args)


class TcpOscConnection(OscConnection):
    """Eos connections over TCP."""

    def __init__(self, ip: str, port: int, generic_delay: float = 0) -> None:
        """Connect to an Eos session over TCP."""
        self.ip_address = ip
        self.port = port
        self.generic_delay = generic_delay
        self._dispatcher = Dispatcher()

        if not hasattr(self, "client"):
            # TODO(eosti): Implement mode detection
            self.client: SimpleTCPClient
            raise NotImplementedError("Mode detection TBD")

        super().__init__()

    @override
    def write(self, path: str, args: list[str | int | float | bool] | None = None) -> None:
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
    def handle_messages(self, timeout: float = 0.1) -> None:
        msgs = []

        start_time = time.perf_counter()
        msg = self.client.receive(timeout)
        while msg:
            for i in msg:
                self.dispatcher.call_handlers_for_packet(i, (self.ip_address, self.port))

            time_left = timeout - (time.perf_counter() - start_time)
            if time_left < 0:
                break
            msg = self.client.receive(time_left)


class PacketLengthTcpOscConnection(TcpOscConnection):
    """Eos connections over TCP v1.0 Packet Length."""

    def __init__(self, ip: str, port: int) -> None:
        """Connect to an Eos session over TCP v1.0."""
        self.client = SimpleTCPClient(ip, port)
        logger.info("Connected to %s:%s (TCP v1.0 Packet Length)", ip, port)

        super().__init__(ip, port)


class SlipTcpOscConnection(TcpOscConnection):
    """Eos connections over TCP v1.1 SLIP."""

    def __init__(self, ip: str, port: int) -> None:
        """Connect to an Eos session over TCP v1.1."""
        self.client = SimpleTCPClient(ip, port, mode=MODE_1_1)
        logger.info("Connected to %s:%s (TCP v1.1 SLIP)", ip, port)

        super().__init__(ip, port)
