"""This module isn't currently used, it'll have some use in the future."""

import os
from pathlib import Path
from pwd import getpwuid
from sys import platform

def get_synth_config_file():
    try:
        if platform == 'darwin':
            p = '~/Library/Preferences/jp.daichi.synth1.plist'
        elif platform == 'win32':
            p = os.path.expandvars('%APPDATA%/Daichi/Synth1/synth1.ini')
        else:
            p = '~/.wine/drive_c/users/%s/Application Data/Daichi/Synth1/synth1.ini' % getpwuid(os.getuid())[0]
        return Path(p).expanduser()
    except:
        return False
