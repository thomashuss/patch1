"""Constants for the Patch1 program."""

from pathlib import Path
from sys import platform

APP_NAME = 'Patch1'
SYNTH_NAME = 'Synth1'
PATCH_FILE_EXT = 'sy1'
FXP_FILE_EXT = 'fxp'
DATA_DIR = Path.home() / ('.%s' % APP_NAME.lower())

# Some people like to put weird things in their files.
FILE_ENC = 'latin_1'

# Synth1 parameters as defined in Zoran Nikolic's unofficial manual.
# https://sound.eti.pg.gda.pl/student/eim/doc/Synth1.pdf
PARAM_NAMES = ['osc1 shape', 'osc2 shape', 'osc2 pitch', 'osc2 fine tune', 'osc2 kbd track', 'osc mix', 'osc2 sync', 'osc2 ring modulation', 'osc pulse width', 'osc key shift', 'osc mod env on/off', 'osc mod env amount', 'osc mod env attack', 'osc mod env decay', 'filter type', 'filter attack', 'filter decay', 'filter sustain', 'filter release', 'filter freq', 'filter resonance', 'filter amount', 'filter kbd track', 'filter saturation', 'filter velocity switch', 'amp attack', 'amp decay', 'amp sustain', 'amp release', 'amp gain', 'amp velocity sens', 'arpeggiator type', 'arpeggiator oct range', 'arpeggiator beat', 'arpeggiator gate', 'delay time', 'delay feedback', 'delay dry/wet', 'play mode type', 'portament time', 'pitch bend range', 'lfo1 destination', 'lfo1 type', 'lfo1 speed', 'lfo1 depth', 'osc1 FM', 'lfo2 destination', 'lfo2 type', 'lfo2 speed', 'lfo2 depth',
               'midi ctrl sens1', 'midi ctrl sens2', 'chorus delay time', 'chorus depth', 'chorus rate', 'chorus feedback', 'chorus level', 'lfo1 on/off', 'lfo2 on/off', 'arpeggiator on/off', 'equalizer tone', 'equalizer freq', 'equalizer level', 'equalizer Q', 'chorus type', 'delay on/off', 'chorus on/off', 'lfo1 tempo sync', 'lfo1 key sync', 'lfo2 tempo sync', 'lfo2 key sync', 'osc mod dest', 'osc1,2 fine tune', 'unison mode', 'portament auto mode', 'unison detune', 'osc1 detune', 'effect on/off', 'effect type', 'effect control1', 'effect control2', 'effect level/mix', 'delay type', 'delay time spread', 'unison pan spread', 'unison pitch', 'midi ctrl src1', 'midi ctrl assign1', 'midi ctrl src2', 'midi ctrl assign2', 'pan', 'osc phase shift', 'unison phase shift', 'unison voice num', 'polyphony', 'osc1 sub gain', 'osc1 sub shape', 'osc1 sub octave', 'delay tone']
PARAM_VALS = [2, 1, 64, 81, 1, 64, 0, 0, 64, 0, 0, 64, 0, 0, 1, 0, 64, 32, 64, 81, 14, 128, 64, 0, 1, 64, 64, 107, 64, 107, 64, 1, 0, 11, 64, 8, 40, 20, 0, 0, 12, 2, 1, 64, 0, 0, 5, 1, 64,
              64, 74, 74, 64, 64, 50, 64, 40, 1, 1, 0, 64, 64, 64, 64, 2, 1, 1, 0, 0, 0, 0, 0, 64, 0, 0, 22, 0, 0, 0, 64, 64, 64, 0, 66, 64, 24, 45057, 44, 45057, 43, 64, 0, 0, 2, 16, 0, 1, 1, 64]
NUM_PARAMS = len(PARAM_VALS)

# Create a properly formatted string (ex: '012') for each possible patch number 1-128.
PATCH_NUMS = tuple(map(lambda n: '{:0>3}'.format(n), range(1, 129)))

# Synth1 patch metadata also from the unofficial manual.
COLORS = ('red', 'blue', 'green', 'yellow', 'magenta', 'cyan', 'default')
COLOR_DEF = COLORS[6]
VER_DEF = '112'
NAME_DEF = 'initial sound'

# The unique ID of the Synth1 VST plugin
# Only explicity mentioned platform is darwin, as the other Synth1 release is win32, which,
# either natively or through a compat layer (Wine), will run on all other platforms.
VST_ID = 1450726194 if platform == 'darwin' else 1395742323

STATUS_READY = 'ready'
STATUS_IMPORT = 'importing'
STATUS_NAME_TAG = 'name_tag'
STATUS_SIM_TAG = 'similar_tag'
STATUS_OPEN = 'opening'
STATUS_SEARCH = 'searching'
STATUS_WAIT = 'wait'