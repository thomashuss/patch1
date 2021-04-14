"""Constants for the Patch1 program."""

from pathlib import Path

APP_NAME = 'Patch1'
APP_NAME_INLINE = APP_NAME.lower()
APP_WEBSITE = 'https://github.com/intrlocutr/' + APP_NAME_INLINE
FXP_FILE_EXT = 'fxp'
DATA_DIR = Path.home() / ('.%s' % APP_NAME_INLINE)

# Some people like to put weird things in their files.
FILE_ENC = 'latin_1'

STATUS_READY = 'ready'
STATUS_IMPORT = 'importing'
STATUS_NAME_TAG = 'name_tag'
STATUS_SIM_TAG = 'similar_tag'
STATUS_OPEN = 'opening'
STATUS_SEARCH = 'searching'
STATUS_WAIT = 'wait'