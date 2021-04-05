try:
    from tkinterdnd2 import Tk
    DND_SUPPORT = True
except ImportError:
    # D&D is optional because tkinterdnd2 can have issues. This shouldn't matter for the pre-packaged version.
    print('Drag and drop support will be disabled, as the tkinterdnd2 Python module was not found or is improperly installed.')
    DND_SUPPORT = False
    from tkinter import Tk

import multiprocessing
from src.gui import AppGui

if __name__ == '__main__':
    multiprocessing.freeze_support()
    root = Tk()
    AppGui(root)
    root.mainloop()
