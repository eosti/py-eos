from decimal import Decimal
import random
import time

import pytest

from eos import Cue, Eos
from eos.helpers import EosError

@pytest.fixture
def test_cue(eos: Eos):
    q = Cue(1, random.randint(1, 999))
    eos.cues.record(q)
    yield q
    eos.cues.delete(q)



@pytest.mark.parametrize(
        ("cue_list", "cue_num"),
        [
            (1, 1),
            (1, Decimal("1.7")),
            (2, 2),
            (2, Decimal("2.7"))
            ]
        )
class TestEosCuesCreationDeletion:

    @pytest.fixture(scope="class", autouse=True)
    def remove_cuelists(self, eos: Eos):
        yield
        eos.keys.live()
        eos.send_command("Delete Cue 1 / # #")
        eos.send_command("Delete Cue 2 / # #")

    def test_cue_creation_live(self, eos: Eos, cue_list, cue_num):
        eos.keys.live()
        start_num_cues = eos.cues.count(cue_list)
        assert type(start_num_cues) is int

        rec_cue = Cue(cue_list, cue_num)
        cue_props = eos.cues.record(rec_cue)
        end_num_cues = eos.cues.count(cue_list)
        assert start_num_cues == end_num_cues - 1

        assert cue_props.cuelist == rec_cue.cuelist
        assert cue_props.number == rec_cue.cue
        assert cue_props.part == 0

    def test_cue_deletion_live(self, eos: Eos, cue_list, cue_num):
        eos.keys.live()
        start_num_cues = eos.cues.count(cue_list)
        assert type(start_num_cues) is int

        del_cue = Cue(cue_list, cue_num)
        eos.cues.delete(del_cue)

        end_num_cues = eos.cues.count(cue_list)
        assert end_num_cues == start_num_cues - 1

    def test_cue_creation_blind(self, eos: Eos, cue_list, cue_num):
        eos.keys.blind()
        start_num_cues = eos.cues.count(cue_list)
        assert type(start_num_cues) is int

        rec_cue = Cue(cue_list, cue_num)
        cue_props = eos.cues.record(rec_cue)
        end_num_cues = eos.cues.count(cue_list)
        assert start_num_cues == end_num_cues - 1

        assert cue_props.cuelist == rec_cue.cuelist
        assert cue_props.number == rec_cue.cue
        assert cue_props.part == 0

    def test_cue_deletion_blind(self, eos: Eos, cue_list, cue_num):
        eos.keys.blind()
        start_num_cues = eos.cues.count(cue_list)
        assert type(start_num_cues) is int

        del_cue = Cue(cue_list, cue_num)
        eos.cues.delete(del_cue)

        end_num_cues = eos.cues.count(cue_list)
        assert end_num_cues == start_num_cues - 1

class TestEosCueModification:
    def test_cue_record_existing(self, eos: Eos, test_cue):
        with pytest.raises(EosError):
            eos.cues.record(test_cue)

    @pytest.mark.parametrize(
            ("cue_label"),
            [("pytest"), ("pytest new label"), ("label #3"), ("label # ! ?")]
            )
    def test_cue_label(self, eos: Eos, test_cue, cue_label):
        before_props = eos.cues.get_cue(test_cue)
        assert before_props.label == ""
        eos.cues.label(test_cue, cue_label)
        time.sleep(0.05)
        after_props = eos.cues.get_cue(test_cue)
        assert after_props.label == cue_label

    def test_cue_time(self, eos: Eos, test_cue):
        before_props = eos.cues.get_cue(test_cue)
        assert before_props.uptime < 0
        eos.cues.set_time(test_cue, 3)
        time.sleep(0.05)
        after_props = eos.cues.get_cue(test_cue)
        assert after_props.uptime == 3

    def test_cue_split_time(self, eos: Eos, test_cue):
        before_props = eos.cues.get_cue(test_cue)
        assert before_props.uptime < 0
        eos.cues.set_time(test_cue, 8, Decimal("7.9"))
        time.sleep(0.05)
        after_props = eos.cues.get_cue(test_cue)
        assert after_props.uptime == 8
        assert after_props.downtime == Decimal('7.9')

class TestEosCueExternalConnections:

    @pytest.fixture
    def target_cue(self, eos: Eos):
        q = Cue(1, random.randint(1000, 1999))
        eos.cues.record(q)
        yield q
        eos.cues.delete(q)

    def test_cue_external_link(self, eos: Eos, test_cue, target_cue):
        before_props = eos.cues.get_cue(test_cue)
        assert before_props.links is None
        assert before_props.links2 is None

        eos.cues.link_cue(test_cue, target_cue)
        eos.cues.link_cue(test_cue, test_cue)
        time.sleep(1)

        after_props = eos.cues.get_cue(test_cue)
        # Seemingly Eos doesn't do this anymore?

    def test_cue_external_actions_cue(self, eos: Eos, test_cue):
        before_props = eos.cues.get_cue(test_cue)
        assert before_props.links is None
        assert before_props.links2 is None

        eos.cues.execute_cue(test_cue, test_cue)
        time.sleep(1)

        after_props = eos.cues.get_cue(test_cue)
        assert after_props.actions is not None
        assert after_props.actions[0] == f"Q{test_cue.cuelist} / {test_cue.cue}"



class TestEosCueCurrentState:
    cue_list = (
            Cue(1, 1, label="Cue One", duration=Decimal(6)),
            Cue(1, 2, label="Cue Two", duration=Decimal("4.9")),
            Cue(1, 9, label="Cue Tres", duration=Decimal(3)),
            Cue(1, 999, label="Cue Last", duration=Decimal(2))
            )

    @pytest.fixture(scope="class", autouse=True)
    def setup_cuelist(self, eos: Eos):
        for q in self.cue_list:
            eos.cues.record(q)
            assert q.duration is not None
            eos.cues.set_time(q, q.duration)
            eos.cues.label(q, q.label)
        eos.keys.go_to_cue_zero()
        eos.osc.handle_messages()
        yield
        eos.keys.live()
        eos.send_command("Delete Cue 1 / # #")


    def test_current_cue(self, eos: Eos) -> None:
        assert eos.cues.previous_cue is None
        assert eos.cues.active_cue == Cue(0, 0, 0, "", Decimal("0.0"), Decimal(1))

        eos.keys.go_to_cue(Cue(1, 1))
        eos.osc.handle_messages()

        assert eos.cues.previous_cue is None
        assert eos.cues.active_cue is not None
        assert eos.cues.active_cue.cue == 1
        assert eos.cues.active_cue.cuelist == 1
        assert eos.cues.active_cue.duration == Decimal(6)
        assert eos.cues.active_cue.percentage == 1.00
        assert eos.cues.pending_cue is not None
        assert eos.cues.pending_cue.cue == 2

        eos.keys.go()
        eos.osc.handle_messages()
        time.sleep(0.1)

        assert eos.cues.previous_cue is not None
        assert eos.cues.previous_cue.cue == 1
        assert eos.cues.previous_cue.cuelist == 1
        assert eos.cues.previous_cue.duration == Decimal(6)
        assert eos.cues.previous_cue.percentage is None
        assert eos.cues.active_cue is not None
        assert eos.cues.active_cue.cue == 2
        assert eos.cues.active_cue.cuelist == 1
        assert eos.cues.active_cue.duration is not None
        assert eos.cues.active_cue.duration < 4.9
        assert eos.cues.active_cue.percentage is not None
        assert eos.cues.active_cue.percentage < 1.00
