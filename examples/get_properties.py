"""Find an item revision by Item ID and print some of its properties."""
import sys

from _connect import connect

item_id, rev_id = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "A"

tc = connect()
rev = tc.tools.get_revision_uid_by_item_id(item_id, rev_id)
if not rev:
    sys.exit(f"{item_id}/{rev_id} not found")

for prop in tc.get_properties(rev["uid"], ["object_name", "object_desc", "last_mod_date"]):
    print(prop.name, "=", prop.get_value() if prop else None)
