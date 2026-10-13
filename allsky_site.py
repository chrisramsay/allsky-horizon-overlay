"""
Shared settings loader for the allsky horizon tools.

Reads site.toml from the repo directory, falling back to site.example.toml.
Set ALLSKY_SITE to use a different file.
"""
import os
import sys

try:
    import tomllib                  # Python 3.11+
except ModuleNotFoundError:         # older Python: pip install tomli
    import tomli as tomllib

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path=None):
    path = path or os.environ.get("ALLSKY_SITE")
    if not path:
        path = os.path.join(HERE, "site.toml")
        if not os.path.exists(path):
            path = os.path.join(HERE, "site.example.toml")
            print("Note: site.toml not found - using site.example.toml", file=sys.stderr)
    with open(path, "rb") as f:
        cfg = tomllib.load(f)
    cfg["_path"] = path
    return cfg
