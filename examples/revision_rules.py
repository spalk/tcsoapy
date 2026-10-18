"""List revision rules, and show the entries of one rule."""
import sys

from _connect import connect

tc = connect()
for rule in tc.tools.get_rules():
    print(rule)

if len(sys.argv) > 1:
    print()
    for entry in tc.tools.get_statuses_from_rule(rule_name=sys.argv[1]):
        print(entry)
