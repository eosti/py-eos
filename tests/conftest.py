import pytest

from eos import Eos


@pytest.fixture(scope="session", autouse=True)
def eos():
    eos = Eos.tcp_slip("localhost", 3032)
    yield eos
    eos.keys.live()
    eos.keys.clear_cmd_line()
