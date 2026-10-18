"""Show where an item revision is used, one level up."""
import sys

from tcsoapy.response import Response

from _connect import connect

tc = connect()
rev = tc.tools.get_revision_uid_by_item_id(sys.argv[1], sys.argv[2])
response = Response(tc.request.get_where_used(rev["uid"]))
for obj in response.data_objects:
    print(obj.get_type(), obj.get_uid())
