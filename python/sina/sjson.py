"""
Standardize JSON calls across versions.

JSON processing makes up a not-insignificant portion of Sina's time. Orjson is
the fastest JSON library we've found, but isn't available for all versions. We
fall back to ujson (still faster than the default json) when we're outside of
orjson's version range.

Sina's json needs are currently simple; if that changes, hopefully it'll be in
time with dropping Py2 support. It should be safe to delete this module and
import orjson in its place.
"""

try:
    import orjson as json  # pylint: disable=import-error
except ImportError:
    try:
        import ujson as json  # pylint: disable=import-error
    except ImportError:
        import json


def loads(*args, **kwargs):
    """Pass loading through to the desired json library."""
    return json.loads(*args, **kwargs)


def dumps(*args, **kwargs):
    """Pass dumping through to the desired json library."""
    return json.dumps(*args, **kwargs)
