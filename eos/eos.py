import logging
import sys
import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import ArgValue, build_msg
from pythonosc.osc_packet import OscPacket
from pythonosc.osc_tcp_server import MODE_1_1
from pythonosc.tcp_client import SimpleTCPClient
from pythonosc.udp_client import SimpleUDPClient

from eos.cues import EosCues
from eos.system import EosSystem
from eos.groups import EosGroups
from eos.macros import EosMacros

from eos.types import (
    Cue,
    CueProperties,
    EosException,
)

logger = logging.getLogger(__name__)


# EosBase is a the parent of all mixins, so it is implicitly inherited
class Eos(ABC, EosCues, EosSystem, EosGroups, EosMacros):
    def __init__(self):
        self.write(f"/eos/sc/Connected from {sys.argv[0]}")

        self.dispatcher.set_default_handler(self._unhandledMessageHandler)

        logger.info("Connected to Eos v%s", self.get_version())

    def _unhandledMessageHandler(self, addr: str, *args: List[any]) -> None:
        logger.debug(f"Unhandled message: {addr} {args}")


class EosUDP(Eos):
    def __init__(self, ip: str, rx_port: int, tx_port: int):
        self.ip_address = ip
        self.rx_port = rx_port
        self.tx_port = tx_port
        self.dispatcher = Dispatcher()

        # self.server = BlockingOSCUDPServer((self.ip, self.tx_port), self.dispatcher)
        self.client = client = SimpleUDPClient(self.ip, self.rx_port)

        logger.info(
            f"Connected to {self.ip_address} (TX:{self.tx_port}, RX:{self.rx_port})"
        )
        # Confusion, client only takes one port?

        super().__init__()

    def write(self, path: str, args: Optional[List[str]] = None) -> None:
        self.client.send_message(path)


class EosTCP(Eos):
    def __init__(self, ip: str, port: int):
        self.ip_address = ip
        self.port = port
        self.dispatcher = Dispatcher()

        if self.client is None:
            # TODO
            raise NotImplementedError("Mode detection TBD")

        super().__init__()

    def write(self, path: str, args: Optional[List[str]] = None) -> None:
        if args is None:
            self.client.send_message(path)
        else:
            self.client.send_message(path, args)

    def read_next(self, timeout: int = 30):
        msg = self.client.receive(timeout)
        return OscPacket(msg)

    def handle_messages(self, timeout: float = 0.1):
        msg = self.client.receive(timeout)
        while msg:
            for i in msg:
                self.dispatcher.call_handlers_for_packet(
                    i, (self.ip_address, self.port)
                )
            msg = self.client.receive(timeout)


class EosPacketLength(EosTCP):
    def __init__(self, ip: str, port: int):
        self.client = SimpleTCPClient(ip, port)
        logger.info(
            f"Connected to {self.ip_address}:{self.port} (TCP v1.0 Packet Length)"
        )

        super().__init__(ip, port)


class EosSLIP(EosTCP):
    def __init__(self, ip: str, port: int):
        self.client = SimpleTCPClient(ip, port, mode=MODE_1_1)
        logger.info(f"Connected to {ip}:{port} (TCP v1.1 SLIP)")

        super().__init__(ip, port)
