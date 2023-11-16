import numpy as np
from typing import Union
from pandas import Series
from src.patches import PatchSchema
from sys import platform
from xdrlib import Packer
from struct import pack
from io import BytesIO


def s1_chunk_header(ver: int): return ('>21s11xB527xB4xB2xB',
                                       b'Synth1 VST Chunk Data', 0x2, ver, 0x1, 0x1)


def s1_chunk_footer(ver: int): return ('>1207xB3xB3xB7xB15xB3xB19x',
                                       0x1, ver, 0x1, 0x1, 0x1, 0x40)


# Parameters in synth1 chunk data are an ordered xdr list, for the most part
# ...with two exceptions. Exhibit A: these parameters do not conform to the structure of a xdr list, ignore them,
# they're not critical anyway. A proper implementation, rather than a cheap workaround, is on my maybe-to-do list.
S1_IGNORE_PARAMS = ('midi ctrl src1', 'midi ctrl assign1',
                    'midi ctrl src2', 'midi ctrl assign2')

# Manually insert this value instead, it is the default values of those params
S1_IGNORED_FILLER = bytearray(
    b'\x00\x00\x00\x01\x00\x00\x00\x01\xb0\x00\x00\x01\x00\x00\x00\x2c\x00\x00\x00\x01\x00\x00\x00\x01\xb0\x00\x00'
    b'\x01\x00\x00\x00\x2b')

# Where missing params are expected in the xdr buffer
S1_IGNORED_OFFSET = 0x2AC

# Maximum value of each parameter; 0 is assumed minimum, though it isn't always in practice.
# In some cases a nonzero minimum can be safely ignored...
PARAM_RANGE = (4, 3, 127, 127, 1, 127, 1, 1, 127, 48, 1, 127, 127, 127, 3, 127, 127, 127, 127, 127, 127, 127, 127, 127,
               1, 127, 127, 127, 127, 127, 127, 3, 3, 18, 127, 19, 127, 127, 2, 127, 24, 6, 5, 127, 127, 127, 6, 5, 127,
               127, 127, 127, 127, 127, 127, 127, 127, 1, 1, 1, 127, 127, 127, 127, 3, 1, 1, 1, 1, 1, 1, 2, 127, 1, 1,
               127, 127, 1, 9, 127, 127, 127, 2, 127, 127, 48, 65536, 99, 65536, 99, 127, 127, 127, 6, 31, 127, 3, 1,
               127)
# ...and when they can't, add these values where index == dict key.
PARAM_SNOWFLAKES = {1: -1, 9: 24, 31: -1, 41: -1, 46: -1, 64: -1, 87: 1, 89: 1, 93: -2, 94: -1}


class Synth1(PatchSchema):
    synth_name = 'Synth1'
    # The unique ID of the Synth1 VST plugin
    # Only explicity mentioned platform is darwin, as the other Synth1 release is win32, which,
    # either natively or through a compat layer (Wine), will run on all other platforms.
    vst_id = 1450726194 if platform == 'darwin' else 1395742323
    file_pattern = r'^[0-9]{3}\.[s|S][y|Y]1$'
    file_base = '001'
    file_ext = 'sy1'

    # Synth1 parameters as defined in Zoran Nikolic's unofficial manual.
    # https://sound.eti.pg.gda.pl/student/eim/doc/Synth1.pdf
    metas = ['color', 'ver']
    defaults = ['default', '113']
    possibilites = {
        'color': ['red', 'blue', 'green', 'yellow', 'magenta', 'cyan', 'default'],
        'ver': list(map(str, range(100, 114)))
    }

    params = ['osc1 shape', 'osc2 shape', 'osc2 pitch', 'osc2 fine tune', 'osc2 kbd track', 'osc mix', 'osc2 sync',
              'osc2 ring modulation', 'osc pulse width', 'osc key shift', 'osc mod env on/off', 'osc mod env amount',
              'osc mod env attack', 'osc mod env decay', 'filter type', 'filter attack', 'filter decay',
              'filter sustain', 'filter release', 'filter freq', 'filter resonance', 'filter amount',
              'filter kbd track', 'filter saturation', 'filter velocity switch', 'amp attack', 'amp decay',
              'amp sustain', 'amp release', 'amp gain', 'amp velocity sens', 'arpeggiator type',
              'arpeggiator oct range', 'arpeggiator beat', 'arpeggiator gate', 'delay time', 'delay feedback',
              'delay dry/wet', 'play mode type', 'portament time', 'pitch bend range', 'lfo1 destination', 'lfo1 type',
              'lfo1 speed', 'lfo1 depth', 'osc1 FM', 'lfo2 destination', 'lfo2 type', 'lfo2 speed', 'lfo2 depth',
              'midi ctrl sens1', 'midi ctrl sens2', 'chorus delay time', 'chorus depth', 'chorus rate',
              'chorus feedback', 'chorus level', 'lfo1 on/off', 'lfo2 on/off', 'arpeggiator on/off', 'equalizer tone',
              'equalizer freq', 'equalizer level', 'equalizer Q', 'chorus type', 'delay on/off', 'chorus on/off',
              'lfo1 tempo sync', 'lfo1 key sync', 'lfo2 tempo sync', 'lfo2 key sync', 'osc mod dest',
              'osc1,2 fine tune', 'unison mode', 'portament auto mode', 'unison detune', 'osc1 detune', 'effect on/off',
              'effect type', 'effect control1', 'effect control2', 'effect level/mix', 'delay type',
              'delay time spread', 'unison pan spread', 'unison pitch', 'midi ctrl src1', 'midi ctrl assign1',
              'midi ctrl src2', 'midi ctrl assign2', 'pan', 'osc phase shift', 'unison phase shift', 'unison voice num',
              'polyphony', 'osc1 sub gain', 'osc1 sub shape', 'osc1 sub octave', 'delay tone']
    param_dtype = int
    values = [2, 1, 64, 81, 1, 64, 0, 0, 64, 0, 0, 64, 0, 0, 1, 0, 64, 32, 64, 81, 14, 128, 64, 0, 1, 64, 64, 107, 64,
              107, 64, 1, 0, 11, 64, 8, 40, 20, 0, 0, 12, 2, 1, 64, 0, 0, 5, 1, 64, 64, 74, 74, 64, 64, 50, 64, 40, 1,
              1, 0, 64, 64, 64, 64, 2, 1, 1, 0, 0, 0, 0, 0, 64, 0, 0, 22, 0, 0, 0, 64, 64, 64, 0, 66, 64, 24, 45057, 44,
              45057, 43, 64, 0, 0, 2, 16, 0, 1, 1, 64]

    file_syntax = '{patch_name}\ncolor={color}\nver={ver}\n{params}'

    file_param = '{index},{value}'
    param_delimiter = '\n'

    def sanity_check(self, file: str) -> Union[str, bool]:
        lst = file.split('\n')

        if len(lst) >= 4:
            color = lst[1].lower()
            if color[:5] == 'color':
                lst[1] = color
            else:
                lst[1:1] = ['color=' +
                            self.defaults[self.metas.index('color')]]

            ver = lst[2].lower()
            if ver[:3] == 'ver':
                lst[2] = ver
            else:
                lst[2:2] = ['ver=' + self.defaults[self.metas.index('ver')]]

            # Remove trailing newline
            if lst[-1] == '':
                del lst[-1]

            return '\n'.join(lst)
        else:
            return False

    def make_fxp_chunk(self, patch: Series) -> bytes:
        """Generates Synth1 chunk data from a patch."""

        ver = int(patch['ver'])
        params = patch[self.params].to_numpy(dtype=int)

        if len(params) != 99:
            raise ValueError('Expected 99 parameters, got %i' % len(params))

        # Ignore the non-conforming parameters
        parms = np.delete(params, tuple(self.params.index(s)
                                        for s in S1_IGNORE_PARAMS))

        pak = Packer()
        # Pack parameters into xdr list.
        pak.pack_list(parms, pak.pack_int)
        # cast buffer to bytearray for some tweaking.
        list_buf = bytearray(pak.get_buffer())

        # Exhibit B: Synth1 uses its own magic value for start of list (but not end)
        # So get rid of initial 0x0001 flag from packer; the actual magic value is in the header, which
        # is packed before this in the final chunk.
        del list_buf[0x0:0x4]

        # FWIW, when reading a chunk, this is what you pass into xdrlib.Unpacker:
        # pack('>L', 1) + fxp.chunk[0x239:0x4e5] + fxp.chunk[0x505:]

        # insert filler bytes into the bytearray at offset
        list_buf[S1_IGNORED_OFFSET:S1_IGNORED_OFFSET] = S1_IGNORED_FILLER

        # Exhibit C: For some reason, the key shift is little endian... unlike the rest of the parameters!
        # Swap these 7 bytes.
        list_buf[0x48:0x4F] = list_buf[0x4E:0x47:-1]

        chunk = BytesIO()
        chunk.write(pack(*s1_chunk_header(ver)))
        chunk.write(list_buf)
        chunk.write(pack(*s1_chunk_footer(ver)))

        byts = chunk.getvalue()
        chunk.close()

        return byts

    def make_fxp_params(self, params) -> list:
        """Converts ordered native Synth1 parameter values (arbitrary integers) to ordered FXP parameter values (0-1
        float)."""

        print('NOTICE: This export method does not work nearly as well as exporting a FXP chunk.')

        fxparams = []

        for ind in range(len(params)):
            fxparams.append(
                max(0, min(1, (params[ind] + PARAM_SNOWFLAKES.get(ind, 0)) / PARAM_RANGE[ind])))

        return fxparams


__all__ = ['Synth1']
