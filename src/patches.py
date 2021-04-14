import re
from pathlib import Path
from typing import Type
from numpy import nan
from common import *

META_COLS = ['patch_name', 'bank', 'tags']


class PatchSchema:
    """Abstract definition of a synthesizer patch specification."""

    synth_name: str  # Name of the synth that follows this schema
    vst_id: int  # Numerical ID of the VST plugin
    file_pattern: str  # Regex pattern of a patch file
    file_base: str  # What to put to the left of the "." in a temporary patch file name
    file_ext: str  # Extension of a patch file

    metas: list[str]  # Names of all metadata types
    defaults: list  # Ordered default values of metadata
    # Possible values for any ranged metadata values
    possibilites: dict[str, list]

    params: list[str]  # Names of parameters
    param_dtype: Type  # Data type of parameter values
    # This will be set in __init__ ~~~ total number of parameters
    num_params: int
    values: list  # Ordered defaults for parameters

    # Basic fstring-like syntax of a patch file, must contain {name} and {params} along with any other metadata (NOTE: for right now, {params} must be at the end of the file)
    file_syntax: str
    # Basic fstring-like syntax of a parameter within a patch file, must contain either {name} or {index}, along with a {value}
    file_param: str
    # Character(s) that denote a parameter within a patch file
    param_delimiter: str

    def __init__(self):
        self.num_params = len(self.params)
        if getattr(self, 'file_base', None) is None:
            self.file_base = 'patch'

        brackets_re = re.compile(r'\{|\}')
        self._file_layout = brackets_re.split(self.file_syntax)
        self._param_layout = brackets_re.split(self.file_param)
        if not (len(self._file_layout) % 2 and len(self._param_layout) % 2):
            raise ValueError('Improperly formatted patch file syntax')

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

    def _unformat(self, s: str, param: bool = False) -> dict:
        """Un-formats a string formatted according to `self.file_syntax`."""

        if param:
            layout = self._param_layout
        else:
            layout = self._file_layout

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
            raise ValueError('Improperly formatted patch file')

        return vals

    def read_patchfile(self, path: Path) -> dict:
        """Reads the properly formatted patch file into a dictionary."""

        with open(path, mode='r', encoding=FILE_ENC, errors='replace') as f:
            patchfile = self.sanity_check(f.read().strip())

        if patchfile:
            try:
                vals = self._unformat(patchfile)
                raw_params = vals['params'].split(self.param_delimiter)
                params = [nan] * self.num_params

                for p in raw_params:
                    pdict = self._unformat(p, param=True)
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
