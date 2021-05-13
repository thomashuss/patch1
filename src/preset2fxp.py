# Using code from https://github.com/SpotlightKid/ardour2fxp, Copyright (c) 2018 - 2021 Christopher Arndt
# Originally released under the MIT License

from collections import namedtuple
from struct import calcsize, pack
from typing import Union

FXP_HEADER_FMT = '>4si4s4i28s'
FXP_PREAMBEL_SIZE = calcsize('>4si')
FXP_HEADER_SIZE = calcsize(FXP_HEADER_FMT)
FXP_FORMAT_VERSION = 1
CHUNK_MAGIC = b'CcnK'
FX_MAGIC_PARAMS = b'FxCk'
FX_MAGIC_CHUNK = b'FPCh'
FX_DEFAULT_VERSION = 1
PRESET_BASE_FIELDS = (
    'plugin_id',
    'plugin_version',
    'label',
    'num_params',
)

ChunkPreset = namedtuple('ChunkPreset', PRESET_BASE_FIELDS + ('chunk',))
Preset = namedtuple('Preset', PRESET_BASE_FIELDS + ('params',))


def write_fxp(preset: Union[Preset, ChunkPreset], path: str):
    """Writes the specified preset to a .fxp file at the `path`."""

    with open(path, 'wb') as fp:
        if preset.plugin_version is not None:
            fx_version = preset.plugin_version
        else:
            fx_version = FX_DEFAULT_VERSION

        if isinstance(preset, Preset):
            if preset.num_params is None:
                num_params = len(preset.params)
            else:
                num_params = preset.num_params

            params_fmt = '>{:d}f'.format(num_params)
            size = (FXP_HEADER_SIZE - FXP_PREAMBEL_SIZE +
                    calcsize(params_fmt))
            fx_magic = FX_MAGIC_PARAMS

        elif isinstance(preset, ChunkPreset):
            if preset.num_params is None:
                num_params = int(len(preset.chunk) / 4)
            else:
                num_params = preset.num_params

            chunk_len = len(preset.chunk)
            chunk_size = pack('>i', chunk_len)
            size = (FXP_HEADER_SIZE - FXP_PREAMBEL_SIZE +
                    len(chunk_size) + chunk_len)
            fx_magic = FX_MAGIC_CHUNK

        else:
            raise TypeError("Wrong preset type: {!r}".format(preset))

        header = pack(
            FXP_HEADER_FMT,
            CHUNK_MAGIC,
            size,
            fx_magic,
            FXP_FORMAT_VERSION,
            preset.plugin_id,
            fx_version,
            num_params,
            preset.label.encode('latin1', errors='replace')
        )
        fp.write(header)

        if isinstance(preset, Preset):
            data = pack(params_fmt, *preset.params)
            fp.write(data)

        elif isinstance(preset, ChunkPreset):
            fp.write(chunk_size)
            fp.write(preset.chunk)


__all__ = ['Preset', 'ChunkPreset', 'write_fxp']
