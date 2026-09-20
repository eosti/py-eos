"""Tests relating to Eos groups."""

import random
import time
from decimal import Decimal

import pytest

from eos import Eos, EosError
from eos.helpers import EosChanSelection

# TODO: if a test crashes, the group remains left over.


@pytest.fixture
def test_group(eos: Eos, request):
    number = request.param
    test_group_chans = random.sample(range(1, 999), 10)
    test_group_label = f"pytest group {number}"
    eos.groups.record(number, test_group_chans, test_group_label)
    yield (number, test_group_chans, test_group_label)
    eos.groups.delete(number)


@pytest.mark.parametrize(
    ("group_num", "group_chans", "group_label"),
    [
        (1234, (14, 19, 39, 114, 1), "pytest int"),
        (Decimal("12.34"), (14, 114, 1), "pytest decimal"),
        (12, (), "pytest empty"),
    ],
)
class TestEosGroupsCreationDeletion:
    """Tests relating to Eos groups."""

    def test_group_creation(self, eos: Eos, group_num, group_chans, group_label) -> None:
        """Test the creation of a group with integer index."""
        start_num_group = eos.groups.count()
        assert type(start_num_group) is int

        eos.groups.record(group_num, group_chans, label=group_label)

        end_num_group = eos.groups.count()
        assert start_num_group == end_num_group - 1

        created_group = eos.groups.get(group_num)

        # Verify new group is what we expect it to be
        assert created_group.number == group_num
        assert created_group.label == group_label
        if created_group.chans is None:
            assert group_chans == ()
        else:
            assert set(created_group.chans) == set(group_chans)

    def test_group_deletion(self, eos: Eos, group_num, group_chans, group_label) -> None:
        start_num_group = eos.groups.count()
        assert type(start_num_group) is int

        eos.groups.delete(group_num)

        end_num_group = eos.groups.count()
        assert end_num_group == start_num_group - 1


@pytest.mark.parametrize(
    ("test_group"),
    [
        (2345),
        (Decimal("12.67")),
    ],
    indirect=True,
)
class TestEosGroupsModification:
    def test_group_record_existing(self, eos: Eos, test_group):
        # Try overwriting it without overwrite
        group_num, _, _ = test_group
        with pytest.raises(EosError):
            eos.groups.record(group_num, (1, 2, 3, 4), label="pytest existing group")

    def test_group_update_chans(self, eos: Eos, test_group):
        group_num, group_chans, group_label = test_group
        existing_group = eos.groups.get(group_num)
        assert existing_group.chans == EosChanSelection(group_chans)

        modified_group = eos.groups.edit_chans(existing_group, (1, 2, 3, 4))
        assert modified_group.uid == existing_group.uid
        assert modified_group.label == group_label
        assert modified_group.chans == EosChanSelection((1, 2, 3, 4))

    def test_group_modify_nonexistent(self, eos: Eos, test_group):
        group_num, _, _ = test_group
        existing_group = eos.groups.get(group_num)

        existing_group.number = Decimal(1234)
        existing_group.uid = "notauid"
        with pytest.raises(EosError):
            eos.groups.edit_chans(existing_group, (1, 2, 3, 4))

        with pytest.raises(EosError):
            eos.groups.label(Decimal(1224), "hello")

        with pytest.raises(EosError):
            eos.groups.delete(1234)

    def test_group_update_label(self, eos: Eos, test_group):
        group_num, _, group_label = test_group
        existing_group = eos.groups.get(group_num)
        assert existing_group.label == group_label

        eos.groups.label(group_num, group_label + " EDITED")
        time.sleep(0.1)  # Wait for sync
        modified_group = eos.groups.get(group_num)
        assert modified_group.uid == existing_group.uid
        assert modified_group.label == group_label + " EDITED"
        assert modified_group.chans == existing_group.chans

    def test_group_get_by_uid(self, eos: Eos, test_group):
        group_num, _, _ = test_group
        by_number = eos.groups.get(group_num)
        by_uid = eos.groups.get_by_uid(by_number.uid)
        assert by_number == by_uid
