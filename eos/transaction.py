import logging
import time
from dataclasses import dataclass
from typing import Any

from eos.helpers import EosError, EosTimeoutError
from eos.osc import OscConnection

logger = logging.getLogger(__name__)


@dataclass
class OscResponse:
    addr: str
    args: list[Any]


class Transaction:
    """Class that defines a single transaction over OSC.

    Attributes:
        osc: Instance of OscConnection, typically `eos.osc`
        query_addr: Address to send the data to
        query_data: Optional data to send
        resp_filter: String that matches what a response address would be
        num_resps: Number of expected response messages to receive

    """

    def __init__(
        self,
        osc_conn: OscConnection,
        query_addr: str,
        query_data: list[str | int | float | bool] | None,
        resp_filter: str,
        num_resps: int,
    ) -> None:
        self.osc = osc_conn
        self.query_addr = query_addr
        self.query_data = query_data
        self.resp_filter = resp_filter
        self.num_resps = num_resps

        self.resp: list[OscResponse] = []

    def send(self) -> None:
        """Send OSC message."""
        self.osc.write(self.query_addr, self.query_data)

    def _resp_handler(self, addr: str, *args: list[Any]) -> None:
        """Callback for received messages."""
        self.resp.append(OscResponse(addr, list(args)))

    def query(self, timeout: float = 0.2) -> list[OscResponse]:
        """Send OSC message and receive response."""
        osc_filter = self.osc.dispatcher.map(self.resp_filter, self._resp_handler)
        try:
            self.send()

            start_time = time.perf_counter()
            while len(self.resp) < self.num_resps:
                self.osc.handle_messages(timeout=timeout / 10)
                if time.perf_counter() - start_time > timeout:
                    raise EosTimeoutError(
                        f"Didn't receive all data for query {self.query_addr} "
                        "(got {len(self.resp)})"
                    )
        finally:
            self.osc.dispatcher.unmap(self.resp_filter, osc_filter)

        if len(self.resp) != self.num_resps:
            logger.debug(self.resp)

            raise EosError(
                f"Didn't receive all data for query {self.query_addr} "
                "(got {len(self.resp)}, expected {self.num_resps})"
            )

        return self.resp
