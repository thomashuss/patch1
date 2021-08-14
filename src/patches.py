import re
from pathlib import Path
from typing import Type, Union
from numpy import nan
from src.common import FILE_ENC

META_COLS = ['patch_name', 'bank', 'tags']


class PatchSchema:
    """Abstract definition of a synthesizer patch specification."""

    synth_name: str  # Name of the synth that follows this schema
    vst_id: int  # Numerical ID of the VST plugin
    file_pattern: str  # Regex pattern of a patch file
    file_base: str  # What to put to the left of the "." in a temporary patch file name
    file_ext: str = None  # Extension of a patch file, if the synth stores patches in a native format

    metas: list[str]  # Names of all metadata types specific to this schema, not including the patch's name.
    defaults: list  # Ordered default values of metadata
    # Possible values for any ranged metadata values
    possibilites: dict[str, list]

    params: list[str]  # Names of parameters
    param_dtype: Type  # Data type of parameter values
    # This will be filled automatically; total number of parameters
    num_params: int
    values: list  # Ordered defaults for parameters

    # Basic fstring-like syntax of a patch file, must contain {patch_name} and {params} along with any other metadata
    # (NOTE: for right now, {params} must be at the end of the file, and each value must contain
    # a name or index corresponding to its parameter; an order is not yet supported.)
    file_syntax: str
    # Basic fstring-like syntax of a parameter within a patch file, must contain either {name} or {index},
    # along with a {value}
    file_param: str
    # Character(s) that separate parameters within a patch file
    param_delimiter: str

    def __init__(self):
        self.num_params = len(self.params)
        if getattr(self, 'file_base', None) is None:
            self.file_base = 'patch'

        brackets_re = re.compile(r'[{}]')
        self.__file_layout = brackets_re.split(self.file_syntax)
        self.__param_layout = brackets_re.split(self.file_param)
        if not (len(self.__file_layout) % 2 and len(self.__param_layout) % 2):
            raise ValueError('Improperly formatted patch file syntax')

        self.meta_cols = self.metas + ['patch_name', 'tags', 'bank']

    def write_patchfile(self, patch, path):
        """Writes the patch in original format at the path."""

        to_write = {col: patch[col] for col in META_COLS}
        to_write.update({col: patch[col] for col in self.metas})

        to_write['params'] = self.param_delimiter.join(map(
            self.file_param.format_map,
            ({'name': self.params[i], 'index': i, 'value': self.param_dtype(value)}
             for i, value in zip(range(self.num_params), patch[self.params]))))

        with open(path, mode='w', encoding=FILE_ENC) as f:
            f.write(self.file_syntax.format_map(to_write))

    def sanity_check(self, file: str) -> Union[str, bool]:
        """TBD. This function should correct an improperly formatted patch file, or return `False` if the file
        can't be formatted. """
        return file

    def __unformat(self, s: str, param: bool = False) -> dict:
        """Internal use only. Un-formats a string formatted according to `self.file_syntax`."""

        if param:
            layout = self.__param_layout
        else:
            layout = self.__file_layout

        vals = dict()
        f_index = 0
        for i in range(0, len(layout) - 2, 2):
            ind = s.index(layout[i], f_index) + len(layout[i])
            if layout[i + 2] == '':
                f_index = None
            else:
                f_index = s.index(layout[i + 2], ind)
            vals[layout[i + 1]] = s[ind:f_index]

        return vals

    def read_patchfile(self, path: Path) -> Union[dict, bool]:
        """Reads the properly formatted patch file into a `dict`. Returns `False` if the file is improperly
        formatted."""

        with open(path, mode='r', encoding=FILE_ENC, errors='replace') as f:
            patchfile = self.sanity_check(f.read())

        if patchfile:
            try:
                vals = self.__unformat(patchfile)
                raw_params = vals['params'].split(self.param_delimiter)
                params = [nan] * self.num_params

                for p in raw_params:
                    pdict = self.__unformat(p, param=True)
                    if pdict.get('index') is None:
                        ind = self.params.index(pdict['name'])
                    else:
                        ind = int(pdict['index'])
                    params[ind] = self.param_dtype(pdict['value'])
            except:
                raise ValueError(
                    'Patch file %s is not properly formatted.' % str(path))

            rdict = {key: value for key, value in vals.items() if key !=
                     'params' and key != 'name'}
            # need to replace the params string with list of params
            rdict['params'] = params
            rdict['bank'] = path.parent.name
            return rdict
        else:
            return False

    def make_fxp_chunk(self, patch) -> bytes:
        """TBD. This function should return a chunk of opaque data for the VST plugin."""
        pass

    def make_fxp_params(self, params) -> list:
        """TBD. This function should convert a list of parameter values in original format to FXP parameter values
        (0-1 float). """
        pass


__all__ = ['PatchSchema']
