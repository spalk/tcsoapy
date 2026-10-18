# tcsoapy

A small Python client for **Siemens Teamcenter SOA** web services (WSDL/SOAP), built on [zeep](https://docs.python-zeep.org/).

You can talk to Teamcenter from plain Python: read and set properties, expand BOMs, resolve
revision rules, find where an item is used and create datasets. You don't need Java, the ITK
or the official .NET/Java SOA client libraries.

> **SOA/WSDL is slow. Prefer REST when you can.**
> Every SOAP call carries heavy XML envelopes, and zeep parses the WSDL of every service
> it touches. In practice this is noticeably slower than the equivalent REST/JSON calls.
> If your Teamcenter version exposes REST services (Teamcenter 12+ / Active Workspace
> gateway), use REST. tcsoapy is for older installations, such as TC 11, and for places
> where only the SOA endpoint is reachable.

## Install

```bash
pip install git+https://github.com/spalk/tcsoapy.git
```

Python 3.10+.

## Quick start

```python
from tcsoapy.teamcenter import Teamcenter
from tcsoapy.response import Response

tc = Teamcenter("http://tc-server:7001/tc/services", "user", "password")

# Item ID + revision → UIDs
item_uid, rev_uid = tc.tools.get_item_uid_revision_uid("000123", "A")

# Properties
for prop in tc.get_properties(rev_uid, ["object_name", "last_mod_date"]):
    print(prop.name, prop.get_value())

# Full BOM under a revision rule, using batched level-by-level expansion
rule_uid = tc.tools.get_rule_uid_by_name("Latest Working")
bom = Response(tc.request.get_bom_optimized(item_uid, rev_uid, revision_rule_uid=rule_uid))
print(bom.do_count(), "objects")
```

More in [`examples/`](examples/). They read `TC_HOST`, `TC_USER` and `TC_PASS` from the environment.

## What's inside

| Module | What it does |
|---|---|
| `Teamcenter` | Entry point: logs in, holds the session, exposes `request` and `tools` |
| `TCRequest` | Thin wrappers over SOA operations: properties, BOM windows and expansion, where-used / where-referenced, saved queries, datasets, property policies |
| `Response` / `DataObject` / `Property` | Wraps zeep responses so you can find objects by UID or type and read values and UI values |
| `Tools` | Multi-call helpers: revision rules, a rule's end item and status entries, Item ID → UID |

### Fast BOM expansion

`get_bom_optimized()` expands a structure breadth-first. It batches many parent lines into
one `expandPSOneLevel` call (like the rich client does) and skips lines whose
`bl_has_children` is false. On large assemblies this is much faster than one
`expandPSAllLevels` call or a line-by-line expansion. Remember to call `close_bom_window()`.

## Notes

- SOAP requests are sent without an XML declaration. Some Teamcenter servers return an
  empty 200 response otherwise.
- Sessions use the `Core-2006-03-Session` login. Supply credentials through environment
  variables or a secret store, never in code.
- Tested against Teamcenter 11 and 13.

## Status

A personal tool that I use for data export and checks. The API is small and may change
before 1.0. Issues and PRs are welcome.

## License

[MIT](LICENSE)
