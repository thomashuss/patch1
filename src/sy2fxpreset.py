import numpy as np
from collections.abc import Sequence
from xdrlib import Packer
from struct import pack
from io import BytesIO
from common import VER_DEF, PARAM_NAMES


def S1_CHUNK_HEADER(ver: int): return ('>21s11xB527xB4xB2xB',
                                       b'Synth1 VST Chunk Data', 0x2, ver, 0x1, 0x1)


def S1_CHUNK_FOOTER(ver: int): return ('>1207xB3xB3xB7xB15xB3xB19x',
                                       0x1, ver, 0x1, 0x1, 0x1, 0x40)


# Parameters in synth1 chunk data are an ordered xdr list, for the most part
# ...with two exceptions. Exhibit A: these parameters do not conform to the structure of a xdr list, ignore them,
# they're not critical anyway. A proper implementation, rather than a cheap workaround, is on my maybe-to-do list.
S1_IGNORE_PARAMS = ('midi ctrl src1', 'midi ctrl assign1',
                    'midi ctrl src2', 'midi ctrl assign2')

# Manually insert this value instead, it is the default values of those params
S1_IGNORED_FILLER = bytearray(
    b'\x00\x00\x00\x01\x00\x00\x00\x01\xb0\x00\x00\x01\x00\x00\x00\x2c\x00\x00\x00\x01\x00\x00\x00\x01\xb0\x00\x00\x01\x00\x00\x00\x2b')

# Where missing params are expected in the xdr buffer
S1_IGNORED_OFFSET = 0x2AC

# Maximum value of each parameter; 0 is assumed minimum, though it isn't always in practice.
# In some cases a nonzero minimum can be safely ignored...
PARAM_RANGE = (4, 4, 127, 127, 1, 127, 1, 1, 127, 48, 1, 127, 127, 127, 3, 127, 127, 127, 127, 127, 127, 127, 127, 127, 1, 127, 127, 127, 127, 127, 127, 4, 3, 18, 127, 19, 127, 127, 2, 127, 24, 7, 5, 127, 127, 127, 7, 5,
               127, 127, 127, 127, 127, 127, 127, 127, 127, 1, 1, 1, 127, 127, 127, 127, 4, 1, 1, 1, 1, 1, 1, 2, 127, 1, 1, 127, 127, 127, 9, 127, 127, 127, 2, 127, 127, 48, 65536, 99, 65536, 99, 127, 127, 127, 8, 32, 127, 3, 1, 127)
# ...and when they can't, add these values where index == dict key.
PARAM_SNOWFLAKES = {9: 24, 87: 1, 89: 1}


def make_fxp_chunk(params, ver: int = int(VER_DEF)) -> bytes:
    """Generates Synth1 chunk data from ordered parameters."""

    if not isinstance(params, np.ndarray):
        if isinstance(params, Sequence):
            # Cast params to ndarray if it isn't already.
            params = np.array(params)
        else:
            raise TypeError(
                'Expected a Sequence or numpy.ndarray, got %s' % type(params))
    if len(params) != 99:
        raise ValueError('Expected 99 parameters, got %i' % len(params))
    if params.dtype != np.dtype(int):
        raise TypeError(
            'Expected parameters as integers, got %s' % params.dtype)

    # Ignore the non-conforming parameters
    parms = np.delete(params, tuple(PARAM_NAMES.index(s)
                                    for s in S1_IGNORE_PARAMS))

    pak = Packer()
    # Pack parameters into xdr list.
    pak.pack_list(parms, pak.pack_int)
    # cast buffer to bytearray for some tweaking.
    list_buf = bytearray(pak.get_buffer())

    # FWIW, when reading a chunk, this is what you pass into xdrlib.Unpacker:
    # pack('>L', 1) + fxp.chunk[0x239:0x4e5] + fxp.chunk[0x505:]

    # Exhibit B: Synth1 uses its own magic value for start of list (but not end)
    # So get rid of initial 0x0001 flag from packer; the actual magic value is in the header, which
    # is packed before this in the final chunk.
    del list_buf[0x0:0x4]

    # insert filler bytes into the bytearray at offset
    list_buf[S1_IGNORED_OFFSET:S1_IGNORED_OFFSET] = S1_IGNORED_FILLER

    chunk = BytesIO()
    chunk.write(pack(*S1_CHUNK_HEADER(ver)))
    chunk.write(list_buf)
    chunk.write(pack(*S1_CHUNK_FOOTER(ver)))

    byts = chunk.getvalue()
    chunk.close()

    return byts


def make_fxp_params(params) -> list:
    """Converts ordered native Synth1 parameter values (arbitrary integers) to ordered FXP parameter values (0-1 float)."""

    fxparams = []

    for ind in range(len(params)):
        fxparams.append(
            max(0, min(1, (params[ind] + PARAM_SNOWFLAKES.get(ind, 0)) / PARAM_RANGE[ind])))

    return fxparams

__all__ = ['make_fxp_chunk', 'make_fxp_params']