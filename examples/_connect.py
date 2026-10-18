import os

from tcsoapy.teamcenter import Teamcenter


def connect() -> Teamcenter:
    """Connects using TC_HOST, TC_USER and TC_PASS from the environment.

    TC_HOST is the SOA services URL, e.g. http://tc-server:7001/tc/services
    """
    return Teamcenter(os.environ["TC_HOST"], os.environ["TC_USER"], os.environ["TC_PASS"])
