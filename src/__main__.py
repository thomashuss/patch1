from tkinterdnd2 import Tk
import multiprocessing
from gui import AppGui

if __name__ == '__main__':
    multiprocessing.freeze_support()
    root = Tk()
    AppGui(root)
    root.mainloop()
