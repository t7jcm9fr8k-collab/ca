"""
names.py — a name that becomes part of a file path has to stay a name.

A recipe's id and layer sources, mockup.py and qc.py's --design, and
render_plate.py's --slug are all joined into paths under out/ and sources/.
A "/" or ".." in one of them used to read or write outside those folders —
a recipe could overwrite any PNG the user can write. Refused here instead.
"""
import os


def safe_name(value, what):
    """`value` unchanged when it is a plain file name; ValueError otherwise."""
    s = str(value)
    if (not s or s in (".", "..") or s != os.path.basename(s)
            or "\\" in s or "\0" in s or os.path.isabs(s)):
        raise ValueError(f"{what} {s!r} is not a plain file name — no '/', '\\\\' or '..'")
    return s
