try:
    from tkinterdnd2 import Tk
    DND_SUPPORT = True
except ImportError:
    print('Drag and drop support is disabled. To enable it, install tkinterdnd2:',
          'https://github.com/pmgagne/tkinterdnd2')
    print('Be sure to rename the package to "tkinterdnd2" by editing the setup.py file.')
    from tkinter import Tk
    DND_SUPPORT = False

import multiprocessing
from src.gui import AppGui


def main():
    multiprocessing.freeze_support()
    root = Tk()
    AppGui(root)
    root.mainloop()
