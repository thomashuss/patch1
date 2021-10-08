# Patch1

![patch1](https://user-images.githubusercontent.com/45053302/135959491-83fc93dc-621d-4299-b94d-11fd3664b08d.png)

Patch1 is a preset manager for virtual synthesizers, namely [Synth1](https://daichilab.sakura.ne.jp/softsynth/index.html). Written in Python and built on [`pandas`](https://pandas.pydata.org/), and providing a graphical frontend through [`tkinter`](https://docs.python.org/3/library/tkinter.html), it is designed to be modular and hackable.

## Features

- Intuitive three-pane layout
- Organize your library with tags
  - **Programatically** using regular expressions (built-in or user-defined)
  - **Automatically** using machine learning
  - **Manually** using the tag editor
- Export patches in the synth's native file format, or VST standard FXP (AUPreset support coming soon)
- Drag-and-drop patches directly into your DAW (if supported) or file manager
- API for patch file schemas -- you can modify the program for use with other synths
- Fast and efficient thanks to the highly optimized `pandas` library
- Cross-platform -- it even runs on Linux for those who use Synth1 with Wine

## Installation

### Requirements

- Python 3.8 or newer

### Basic install

First, clone the repository if you have Git installed, or download the zip file from the project page and extract it to a folder called "patch1". Install the dependencies for the program by running
```
python3 -m pip install -r requirements.txt
```
Then, to open Patch1, just run
```
python3 .
```
in the "patch1" directory.

Depending on how you have Python installed on your system, you may need to adjust the `python3` command.

### Python package

Patch1 can be installed as a Python package, which allows you to simply run the command `patch1` to launch it. This may make it a little more annoying to customize the code, though. If you prefer a Python package, clone the repository, then run
```
python3 setup.py install --user
```

### Pre-built package

In the future, Patch1 may be distributed as a pre-built package (through [PyInstaller](https://www.pyinstaller.org/)) for those who don't have Python on their computer, aren't planning on customizing their installation, and want a pre-configured environment ideal for Patch1. The obvious downside to this is the large download size due to the inclusion of Python and all dependencies. If you'd like to build your own PyInstaller package of Patch1, you can use the `build_win.ps1` or `build_mac.sh` scripts.
### Drag-and-drop support (optional)

Patch1 offers a drag-and-drop feature which allows you to seamlessly drag a patch from the program into your DAW or file manager. To take advantage of this, install the [`tkinterdnd2`](https://github.com/pmgagne/tkinterdnd2) package. It's not in the PyPI, so it is optional. (Patch1 will politely inform you via the console that drag-and-drop is disabled if it isn't installed.)

Clone the `tkinterdnd2` repository:
```
git clone https://github.com/pmgagne/tkinterdnd2.git
```

Here's where it's a bit tricky. The Python package itself isn't actually named `tkinterdnd2`, so you'll need to rename it yourself. Open the `setup.py` file and change the line that reads
```
name="tkinterdnd2-pmgagne", # Replace with your own username
```
to
```
name="tkinterdnd2",
```

Then just run
```
python3 setup.py install --user
```
in the `tkinterdnd2` directory.

## Use

### Getting started

When you first launch Patch1, you'll need to create a database. Select `File -> Create new database` and select a directory containing your Synth1 banks; in other words, a directory containing directories containing `.sy1` files. After a few seconds, assuming the files and directory structure are formatted properly, you'll have a new database, as evidenced by the bank names in the lower-left box.

A first step after creating a new database may be tagging some of your patches. A good starting point is the built-in tag definitions, which tags your patches based on their names. Select `Edit -> Run name-based tagging with... -> built-in definitions`, and after a few seconds, you'll notice some tag names in the upper-left box.