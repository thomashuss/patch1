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

First, clone the repository if you have Git installed, or download the zip file from the project page and extract it to a folder called `patch1`. Install the dependencies for the program by running
```
python3 -m pip install -r requirements.txt
```
Then, to open Patch1, just run
```
python3 .
```
in the `patch1` directory.

Depending on how you have Python installed on your system, you may need to adjust the `python3` command.

### Python package

Patch1 can be installed as a Python package, which allows you to simply run the command `patch1` to launch it. This installation method may make it a little more annoying to customize the code, though. If you prefer a Python package, clone the repository, then run
```
python3 setup.py install --user
```

### Pre-built package

In the future, Patch1 may be distributed as a pre-built package (with [PyInstaller](https://www.pyinstaller.org/)) for those who don't have Python on their computer, aren't planning on customizing their installation, and want a pre-configured environment ideal for Patch1. The obvious downside to this is the large download size due to the inclusion of Python and all dependencies. If you'd like to build your own PyInstaller package of Patch1, you can use the `build_win.ps1` or `build_mac.sh` script.

### Drag-and-drop support (optional)

Patch1 offers a drag-and-drop feature which allows you to seamlessly drag a patch from the program into your DAW or file manager (see [Quick export](#quick-export)). To take advantage of this, install the [`tkinterdnd2`](https://github.com/pmgagne/tkinterdnd2) package. It's not in the PyPI, so it is optional. (Patch1 will politely inform you via the console that drag-and-drop is disabled if it isn't installed.)

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

The first step after creating a new database may be tagging some of your patches. A good starting point is the built-in tag definitions, which tags your patches based on their names. Select `Edit -> Run name-based tagging with... -> built-in definitions`, and after a few seconds, you'll notice some tag names in the upper-left box.

### Navigating the interface

The general layout of Patch1's user interface is shown below:
```
+-------------------------------------------------------------------------------------------+
|  Keyword Search         |                                       |                         |
|-------------------------|                                       |                         |
|                         |                                       |                         |
|  Tag Search             |                                       |                         |
|                         |            Patch List Pane            |        Meta Pane        |
|-------------------------|                                       |                         |
|                         |                                       |                         |
|  Bank Search            |                                       |-------------------------|
|                         |                                       |  Export Buttons         |
+-------------------------------------------------------------------------------------------+
```

The interface is laid out such that the process of finding a patch flows from left to right: narrow down your criteria on the left, find a patch in the middle, and view additional information ("metadata") on the right.

### Finding a patch

A patch can be found by conducting a keyword search, a tag search, or a bank search. When conducting a tag search, it's possible to select more than one tag in the list, by holidng the Shift key or clicking and dragging the mouse over the desired tags.

The results of your search will populate the Patch List Pane. Selecting a patch in the list will open it in the Meta Pane for editing and exporting.

### Organizing your library

The organization of a Patch1 library revolves around tags.

Once a patch has been selected in the Patch List Pane, you are able to edit its tags in the Meta Pane. To add a tag to the selected patch, click the `Add Tag` button and enter the desired tag in the prompt. To remove a tag, select it in the tag editor list and click the `Remove Tag` button.

Of course, it's impractical to manually add tags to tens or hundreds of thousands of patches. That's where name- and parameter-based tagging come in.

#### Name-based tagging

This method tags patches whose name matches a regular expression. All name-based tagging functionality is available in the `Edit -> Run name-based tagging with...` menu; Patch1 comes with its own reasonable definitions (the `built-in definitions` option), or you can define your own in a JSON file (the `custom definitions` option).

In a tagging definitions JSON file, the key should be the name of the tag, and the value should be a [Python regular expression](https://docs.python.org/3/howto/regex.html) (the expression will be interpreted as **case-insensitive**). For example, this JSON file will tag all arps as `Arp`, and all basses but not bassoons or bass drums as `Bass`:
```
{
    "Arp": "\\barp\\b",
    "Bass": "^((?!drum).)*bass(?!oon)"
}
```

#### Parameter-based tagging

Parameter-based tagging uses machine learning. It's designed to fill the gaps left by name-based tagging, as patches may not specify their timbre in the name.

This method trains a nearest neighbors classifier model on the database's existing tags, so you'll need to have a good number of patches tagged before attempting this. Note that this will apply tags just as any other method, so if they are horribly inaccurate, there is no way to remove them all in one click. Therefore, to make sure you have a big enough sample size, it's recommended to run name-based tagging first.

To activate this method, select `Edit -> Run parameter-based tagging`.

The model that is trained by this method will not be saved as it's not intended to be used again. This method should only be run again after a substantial change has been made to the tags in the database; otherwise, it will barely produce a different result.

### Using your patches

Of course, there's no reason to organize your library unless you're planning on using the patches. Patches can be exported from Patch1 in the native file format of the synth (`.sy1`), or in the VST preset (`.fxp`) file format, using the corresponding buttons in the lower right corner of the program's window.

#### Quick export

You can utilize the quick export functionality by dragging a patch from the patch list with your mouse. The patch will turn into a file as you're dragging it, and can be dropped into a file manager or a DAW. By default, this will create a VST preset file, but it can be changed to the native synth format (see [Configuration](#configuration)).

### Adding or removing patches

This functionality is coming soon. However, you can remove duplicate patches by selecting `Edit -> Remove duplicates`.

### Configuration

Patch1's configuration file will be in `~/.patch1/config.ini` (on Windows, `~` is your user profile folder). The options are as follows:

- `auto_load`: Whether to load the database at `path` on program launch. Can be `True` (default) or `False`.
- `auto_save`: Whether to save the loaded database on program exit. Can be `True` (default) or `False`.
- `path`: Absolute path to the database file to open at launch if `auto_load` is `True`. This is set to the path of the open database file after a database file is opened. Defaults to `~/.patch1/db`.
- `export_as`: The file format to used for the drag-and-drop quick export functionality. Can be `chunk` (FXP preset file with opaque binary chunk) (default), `params` (FXP preset file with normalized parameters [**NOT FUNCTIONAL** for Synth1]), or `patch` (synth's native patch file).
- `export_to`: The directory to show in the file save dialog when using one of the export buttons. This is set to the last directory selected by the aforementioned file save dialog. Defaults to the absolute path to your home directory, or user profile folder on Windows.