try:
    from tkinterdnd2 import Tk
    DND_SUPPORT = True
except ImportError:
    print('Drag and drop support is disabled. Consult the README for more information.')
    from tkinter import Tk
    DND_SUPPORT = False

from src.gui import AppGui


def main():
    root = Tk()
    AppGui(root)
    root.mainloop()
