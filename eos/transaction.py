from typing import Any

from eos.helpers import EosError
from eos.osc import OscConnection


class Transaction:
    def __init__(
        self,
        osc_conn: OscConnection,
        query_path: str,
        query_data: list[str | int | float | bool] | None,
        resp_filter: str,
        num_resps: int,
    ) -> None:
        self.osc = osc_conn
        self.query_path = query_path
        self.query_data = query_data
        self.resp_filter = resp_filter
        self.num_resps = num_resps

        self.resp = []

    def send(self) -> None:
        self.osc.write(self.query_path, self.query_data)

    def _resp_handler(self, addr: str, *args: list[Any]) -> None:
        self.resp.append((addr, args))

    def query(self, timeout: float = 0.1) -> list[tuple[str, Any]]:
        osc_filter = self.osc.dispatcher.map(self.resp_filter, self._resp_handler)
        self.send()
        # Do I need to add a delay here? or otherwise keep querying?
        self.osc.handle_messages(timeout=timeout)
        self.osc.dispatcher.unmap(self.resp_filter, osc_filter)

        if len(self.resp) < self.num_resps:
            raise EosError(
                f"Didn't receive all data for query {self.query_path} (got {len(self.resp)}, expected {self.num_resps})"
            )

        return self.resp
