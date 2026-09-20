from decimal import Decimal

from eos import Cue, Eos


class TestEosCues:
    test_cue_list = 12
    test_cue_num = 1234
    test_cue_label = "Testing Cue"

    def test_current_cue(self, eos: Eos) -> None:
        eos.keys.go_to_cue(Cue(1, 1))

        assert eos.cues.previous_cue is None
        assert eos.cues.active_cue is not None
        assert eos.cues.active_cue.cue == 1
        assert eos.cues.active_cue.cuelist == 1
        assert eos.cues.active_cue.duration == Decimal("4.2")
        assert eos.cues.active_cue.percentage == 1.00
        assert eos.cues.pending_cue is not None
        assert eos.cues.pending_cue.cue == 2

        eos.keys.go()
        eos.osc.handle_messages()

        assert eos.cues.previous_cue is not None
        assert eos.cues.previous_cue.cue == 1
        assert eos.cues.previous_cue.cuelist == 1
        assert eos.cues.previous_cue.duration == Decimal("4.2")
        assert eos.cues.previous_cue.percentage is None
        assert eos.cues.active_cue is not None
        assert eos.cues.active_cue.cue == 2
        assert eos.cues.active_cue.cuelist == 1
        assert eos.cues.active_cue.duration is not None
        assert eos.cues.active_cue.duration < 6
        assert eos.cues.active_cue.percentage is not None
        assert eos.cues.active_cue.percentage < 1.00

    def test_cue_creation(self, eos: Eos) -> None:
        """Test the creation of a cue."""
        eos.cues.count(1)
