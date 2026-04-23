from lighting_paperwork.vectorworks_xml import VWExport
import argparse
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
import pandas as pd
from decimal import Decimal
from eos.helpers import EosChanSelection, GroupProperties, EosException
from eos import Eos, EosSLIP

logger = logging.getLogger(__name__)

GROUP_CUTOFF_VALUE = 2


def main(argv = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="CSV or XML from Vectorworks")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    eos = EosSLIP("localhost", 3032)

    vw_export = VWExport(args.file).export_df()

    filter_fields = [
        "Purpose",
        "Channel"
    ]

    df = pd.DataFrame(vw_export[filter_fields], columns=filter_fields)

    df = df.sort_values(
        by=["Purpose", "Channel"],
    )
    group_list = generate_groups(df)

    # dummy check: any duplicate numbers?
    group_numbers = [x.number for x in group_list]
    if len(group_numbers) != len(set(group_numbers)):
        logger.debug(group_numbers)
        raise RuntimeError("Duplicate group numbers detected!")

    group_list.sort(key=lambda x: x.number)

    # Pretty print
    table = Table(title="Generated Groups")

    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Label", justify="left", style="green", no_wrap=True)
    table.add_column("Channels", justify="left", style="magenta", no_wrap=True)

    for i in group_list:
        table.add_row(str(i.number), i.label, i.chans.eos_repr())

    console = Console()
    console.print(table)

    resp = Confirm.ask("Create these groups?")
    if not resp:
        return

    # Make the groups

    for grp in group_list:
        if check_for_existing_group(eos, console, grp):
            continue
        eos.record_group_overwrite(grp.number, grp.chans, grp.label)


def check_for_existing_group(eos: Eos, console: Console, group: GroupProperties) -> bool:
    """Checks if a group already exists in Eosself.

    Returns:
        True if the group already exists and the user does not want to overwrite
        True if the group already exists and the group is identical
        False if the group already exists and the user does want to overwrite
        False if the group does not already exist
    """

    try:
        grp = eos.group.get(group.number)
    except EosException:
        # Group does not exist
        return False
    else:
        print(grp)
        table = Table(title=f"Conflicting Group {group.number}")
        table.add_column("Field", justify="left", no_wrap=True)
        table.add_column("Eos", justify="left", style="red")
        table.add_column("group_generator", justify="left", style="green")

        if grp.label != group.label:
            table.add_row("Label", grp.label, group.label)

        if grp.chans != group.chans:
            if grp.chans is None:
                table.add_row("Channels", "None", group.chans.eos_repr())
            else:
                table.add_row("Channels", grp.chans.eos_repr(), group.chans.eos_repr())

        if not table.rows:
            console.print(f"Group {group.number} exists but no differences found.")
            return True
        
        console.print(table)
        resp = Confirm.ask("Overwrite Eos?")
        if resp:
            return False
        else:
            return True



def generate_groups(df) -> list[GroupProperties]:
    group_list = []

    purposes = df["Purpose"].unique()
    for purp in purposes:
        purpose_df = df.loc[df["Purpose"] == purp]
        if len(purpose_df) < GROUP_CUTOFF_VALUE:
            logger.debug("Dropping %s", purp)
            continue
        if purp == "":
            continue

        group_chans = purpose_df["Channel"].tolist()

        group_num = min([Decimal(x) for x in group_chans])

        group_list.append(GroupProperties(number=group_num, index=None, uid="", label=purp, chans=EosChanSelection(group_chans)))

    # Second pass: "super-groups" for SR/SL pairs

    sr_sl_purposes = [x for x in purposes if any(xs in x for xs in ("SR", "SL"))]
    super_purposes = [(purp.replace("SR", "").replace("SL", "").strip(), purp) for purp in sr_sl_purposes]
    while len(super_purposes) > 0:
        super_purp, purp = super_purposes.pop(0)
        purpose_group = [purp]
        # Do we have a matching super purpose?
        purpose_group.extend(i[1] for i in super_purposes if i[0] == super_purp)

        if len(purpose_group) > 1:
            # We do!

            # Remove these matching groups to prevent duplicates
            super_purposes = [x for x in super_purposes if x[1] not in purpose_group]

            # Find all channels in this super group
            super_purpose_df = df.loc[df["Purpose"].isin(purpose_group)]
            if len(super_purpose_df) < GROUP_CUTOFF_VALUE:
                # oops too small
                continue
            group_chans = super_purpose_df["Channel"].tolist()
            group_num = min([Decimal(x) for x in group_chans]) - 1
            group_list.append(GroupProperties(number=group_num, index=None, uid="", label=super_purp, chans=EosChanSelection(group_chans)))

    return group_list


if __name__ == "__main__":
    main()
