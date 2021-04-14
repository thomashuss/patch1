import re
from pathlib import Path
from typing import Type
from numpy import nan
from common import *

META_COLS = ['patch_name', 'bank', 'tags']


def unformat(fmt: str, s: str) -> dict:
    """Un-formats a string `s` conforming to format `fmt`."""

    layout = re.split(r'\{|\}', fmt)

    if not len(layout) % 2:
        raise ValueError

    vals = dict()
    f_index = 0
    try:
        for i in range(0, len(layout) - 2, 2):
            ind = s.index(layout[i], f_index) + len(layout[i])
            if layout[i + 2] == '':
                f_index = None
            else:
                f_index = s.index(layout[i + 2], ind)
            vals[layout[i + 1]] = s[ind:f_index]
    except:
        raise ValueError

    return vals


class PatchSchema:
    """Abstract definition of a synthesizer patch specification."""

    synth_name: str
    vst_id: str
    file_pattern: str
    file_base: str
    file_ext: str

    metas: list
    defaults: list
    possibilites: dict[str, list]

    params: list
    param_dtype: Type
    num_params: int
    values: list

    file_syntax: str
    file_param: str
    param_delimiter: str

    def __init__(self):
        self.num_params = len(self.params)
        if getattr(self, 'file_base', None) is None:
            self.file_base = 'patch'

    def write_patchfile(self, patch, path):
        """Writes the patch in original format at the path."""

        to_write = {col: patch[col] for col in META_COLS}
        to_write.update({col: patch[col] for col in self.metas})

        param_spec = self.file_param + self.param_delimiter

        to_write['params'] = map(param_spec.format_map,
                                 ({'name': self.params[i], 'index': i, 'value': value}
                                  for i, value in zip(range(self.num_params), patch[self.params])))

        with open(path, mode='w', encoding=FILE_ENC) as f:
            f.write(self.file_syntax % to_write)

    def sanity_check(self, file: str) -> str:
        """TBD. This function should correct and return an improperly formatted patch file, or `False` if the file can't be formatted."""

        return file

    def read_patchfile(self, path: Path) -> dict:
        """Reads the properly formatted patch file into a dictionary."""

        with open(path, mode='r', encoding=FILE_ENC, errors='replace') as f:
            patchfile = self.sanity_check(f.read().strip())

        if patchfile:
            try:
                vals = unformat(self.file_syntax, patchfile)
                raw_params = vals['params'].split(self.param_delimiter)
                params = [nan] * self.num_params

                for p in raw_params:
                    pdict = unformat(self.file_param, p)
                    if pdict.get('index') is None:
                        ind = self.params.index(pdict['name'])
                    else:
                        ind = int(pdict['index'])
                    params[ind] = self.param_dtype(pdict['value'])
            except ValueError:
                raise ValueError(
                    'Patch file %s is not properly formatted.' % str(path))

            rdict = {key: value for key, value in vals.items() if key !=
                    'params' and key != 'name'}
            # need to replace the params string with list of params
            rdict['params'] = params
            rdict['patch_name'] = vals['name']
            rdict['bank'] = path.parent.name
            return rdict
        else:
            return False

    def make_fxp_chunk(self, patch) -> bytes:
        """TBD. This function should return a chunk of opaque data for the VST plugin."""
        pass

    def make_fxp_params(self, params) -> list:
        """TBD. This function should convert a list of parameter values in original format to FXP parameter values (0-1 float)."""
        pass
