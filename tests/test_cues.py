from eos import Eos


class TestEosCues:
    test_cue_list = 12
    test_cue_num = 1234
    test_cue_label = "Testing Cue"

    def test_cue_creation(self, eos: Eos) -> None:
        """Test the creation of a cue."""
        return
        eos.cue.get_count()
