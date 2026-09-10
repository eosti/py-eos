"""Tests relating to Eos groups."""

import time

import pytest

from eos import Eos, EosError

# TODO: if a test crashes, the group remains left over.

class TestEosGroups:
    """Tests relating to Eos groups."""

    test_group_num = 1234
    test_group_chans = (14, 19, 39, 114, 1)
    test_group_label = "Testing Group"

    def test_group_creation(self, eos: Eos) -> None:
        """Test the creation of a group."""
        start_num_group = eos.groups.count()
        assert type(start_num_group) is int

        eos.groups.record(self.test_group_num, self.test_group_chans, label=self.test_group_label)
        time.sleep(0.1)

        end_num_group = eos.groups.count()
        assert start_num_group == end_num_group - 1

        created_group = eos.groups.get(self.test_group_num)

        # Verify new group is what we expect it to be
        assert created_group.number == self.test_group_num
        assert created_group.label == self.test_group_label
        assert set(created_group.chans) == set(self.test_group_chans)

        # Try overwriting it without overwrite
        with pytest.raises(EosError):
            eos.groups.record(
                self.test_group_num, self.test_group_chans, label=self.test_group_label
            )

        # Overwrite the label
        eos.groups.record_overwrite(
            self.test_group_num,
            self.test_group_chans,
            label=self.test_group_label + " NEW",
        )
        time.sleep(0.1)
        created_group = eos.groups.get(self.test_group_num)

        assert created_group.number == self.test_group_num
        assert created_group.label == self.test_group_label + " NEW"
        assert set(created_group.chans) == set(self.test_group_chans)

        # Overwrite the channels
        eos.groups.record_overwrite(
            self.test_group_num, [5], label=self.test_group_label + " NEW", 
        )
        time.sleep(0.1)
        created_group = eos.groups.get(self.test_group_num)

        assert created_group.number == self.test_group_num
        assert created_group.label == self.test_group_label + " NEW"
        assert set(created_group.chans) == {5}

        # Try to get it by uid
        uid_group = eos.groups.get_by_uid(created_group.uid)
        assert uid_group == created_group

    def test_group_iteration(self, eos: Eos) -> None:
        """Test the group iterator."""
        created_group = eos.groups.get(self.test_group_num)
        assert created_group in eos.groups

    def test_group_deletion(self, eos: Eos) -> None:
        """Test the deletion of a group."""
        eos.groups.delete(self.test_group_num)

        with pytest.raises(EosError):
            eos.groups.get(self.test_group_num)

        with pytest.raises(EosError):
            eos.groups.delete(self.test_group_num)
