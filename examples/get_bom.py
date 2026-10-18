"""Expand a full BOM under a revision rule and print every line's item id."""
import sys
import time

from tcsoapy.response import Response

from _connect import connect

item_id, rev_id, rule_name = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Latest Working"

tc = connect()
item_uid, rev_uid = tc.tools.get_item_uid_revision_uid(item_id, rev_id)
rule_uid = tc.tools.get_rule_uid_by_name(rule_name) or ""

start = time.time()
raw = tc.request.get_bom_optimized(item_uid, rev_uid, revision_rule_uid=rule_uid)
bom = Response(raw)
print(f"{bom.do_count()} objects in {time.time() - start:.1f} s")

for line in bom.get_data_objects_by_type("BOMLine"):
    prop = line.get_property("bl_item_item_id")
    print(prop.get_value() if prop else line.get_uid())
