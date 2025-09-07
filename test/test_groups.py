import pytest
from eos import Eos, EosException
import time


class TestEosGroups:
    test_group_num = 1234
    test_group_chans = [14, 19, 39, 114, 1]
    test_group_label = "Testing Group"

    def test_group_creation(self, eos: Eos):
        start_num_group = eos.group.get_count()
        assert type(start_num_group) is int

        eos.record_group(self.test_group_num, self.test_group_chans, label=self.test_group_label)
        time.sleep(0.1)

        end_num_group = eos.group.get_count()
        assert start_num_group == end_num_group - 1

        created_group = eos.group.get(self.test_group_num)

        # Verify new group is what we expect it to be
        assert created_group.number == self.test_group_num
        assert created_group.label == self.test_group_label
        assert set(created_group.chans) == set(self.test_group_chans)

        # Try overwriting it without overwrite
        with pytest.raises(EosException):
            eos.record_group(self.test_group_num, self.test_group_chans, label=self.test_group_label)

        # Overwrite the label
        eos.record_group(self.test_group_num, self.test_group_chans, label=self.test_group_label + " NEW", overwrite=True)
        time.sleep(0.1)
        created_group = eos.group.get(self.test_group_num)

        assert created_group.number == self.test_group_num
        assert created_group.label == self.test_group_label + " NEW"
        assert set(created_group.chans) == set(self.test_group_chans)

        # Overwrite the channels
        eos.record_group(self.test_group_num, [5], label=self.test_group_label + " NEW", overwrite=True)
        time.sleep(0.1)
        created_group = eos.group.get(self.test_group_num)

        assert created_group.number == self.test_group_num
        assert created_group.label == self.test_group_label + " NEW"
        assert set(created_group.chans) == set([5])

        # Try to get it by uid
        uid_group = eos.group.get_by_uid(created_group.uid)
        assert uid_group == created_group

    def test_group_iteration(self, eos: Eos):
        created_group = eos.group.get(self.test_group_num)
        assert created_group in eos.group

    def test_group_deletion(self, eos: Eos):
        eos.delete_group(self.test_group_num)

        with pytest.raises(EosException):
            eos.group.get(self.test_group_num)

        with pytest.raises(EosException):
            eos.delete_group(self.test_group_num)
