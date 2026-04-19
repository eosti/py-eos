import pytest

from eos import EosSLIP


@pytest.fixture(scope="session", autouse=True)
def eos():
    eos = EosSLIP("localhost", 3032)
    yield eos
    eos.live()
    eos.clear_cmd_line()
