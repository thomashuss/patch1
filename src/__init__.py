from tkinterdnd2 import Tk
import multiprocessing
from src.gui import AppGui


def main():
    multiprocessing.freeze_support()
    root = Tk()
    AppGui(root)
    root.mainloop()
