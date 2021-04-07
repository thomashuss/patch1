from common import *
from pathlib import Path
from numpy import nan
import re

# These regex are for finding certain parts of the patch file
RE_NAME = re.compile(r'^[^=,]+$', flags=re.MULTILINE)  # the patch's name
RE_META = re.compile(r'^(.+)(?:=)(.+)$', flags=re.MULTILINE)  # metadata
RE_PARAM = re.compile(r'^([0-9]{1,2})(?:,)([0-9]+)$',
                      flags=re.MULTILINE)  # all parameters

# Syntax of a patch file.
META_SYNTAX = '%s\ncolor=%s\nver=%s\n'
PARAM_SYNTAX = '%i,%i\n'

def write_patchfile(patch, path):
    """Writes the patch to disk in original format at the path."""

    with open(path, mode='w', encoding=FILE_ENC) as f:
        f.write(META_SYNTAX % (patch['name'], patch['color'], patch['ver']))
        for i in range(len(PARAM_NAMES)):
            f.write(PARAM_SYNTAX % (i, patch[PARAM_NAMES[i]]))


def read_patchfile(path: Path) -> tuple:
    """Reads the properly formatted patch file into a 2-tuple: ((bank, num, name, color, ver,), [parameter] * total # of parameters).
    Parameters which are their default values are replaced with `numpy.nan`."""

    with open(path, mode='r', encoding=FILE_ENC, errors='replace') as f:
        patchfile = f.read()

    name = RE_NAME.search(patchfile)
    name = NAME_DEF if name == None else name.group().strip()

    raw_meta = RE_META.findall(patchfile)
    raw_params = RE_PARAM.findall(patchfile)

    # Convert metadata into a dict, just makes it easier to grab specific things
    meta = {m[0]: m[1] for m in (mtup for mtup in raw_meta)}
    color = meta.get('color', COLOR_DEF)
    ver = meta.get('ver', VER_DEF)

    bank = path.parent.name  # Parent dir of current patch should be the bank's name
    num = path.name[:3] # First 3 chars of patch file name should be the number

    params = [nan] * NUM_PARAMS

    for p in raw_params:
        # The regex re_param returns each match as a 2-tuple (num, value)
        # Cast to int because it's currently a str.
        p = tuple(map(int, p))

        # Only include parameters which aren't their defaults. It's quicker to fill in
        # nan values with a pre-defined series of defaults later on.
        if PARAM_VALS[p[0]] != p[1]:
            params[p[0]] = p[1]

    return ((bank, num, name, color, ver), params)
