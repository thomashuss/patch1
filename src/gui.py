import os
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from collections import namedtuple
from tkinter import ttk, messagebox, filedialog, font, simpledialog
from traceback import print_exception
from src.app import *
from src.common import *
from src.patches import PatchSchema
from src.synth1 import Synth1
from . import DND_SUPPORT

if DND_SUPPORT:
    from tkinterdnd2 import *

# Arguments for packing panedwindow panes and *most* widgets inside of them.
PANE_PACKWARGS = {'fill': tk.BOTH, 'side': tk.LEFT,
                  'expand': True, 'anchor': tk.W}

# For coloring ttk treeview entries with the patch's color
TreeColor = namedtuple('TreeColor', ('tagname', 'foreground'))

TREE_COLORS = (TreeColor('red', '#ff4d4f'), TreeColor('blue', '#5557fa'), TreeColor('green', '#10b526'),
               TreeColor('yellow', '#cbcb18'), TreeColor('magenta', '#ff54b5'), TreeColor('cyan', '#00b5b2'))

# Common properties for listboxes
LB_KWARGS = {'selectbackground': '#d6be48',
             'activestyle': tk.NONE, 'width': 25}

# Common properties of open/save dialogs
FILE_KWARGS = {'filetypes': (('All files', '*'),), 'initialdir': str(Path.home())}

ALWAYS = 'always'
NEVER = 'never'
EMPTY = ''

EMPTY_PATCH_NAME = 'Select a patch.'


def scrollbars(master, box, draw_x=True, draw_y=True):
    """Constructs scrollbars for a `Listbox` or `Treeview`."""

    if draw_y:
        yscroll = ttk.Scrollbar(master)
        yscroll.pack(before=box, side=tk.RIGHT, fill=tk.Y)
        yscroll.config(command=box.yview)
        box.config(yscrollcommand=yscroll.set)
    if draw_x:
        xscroll = ttk.Scrollbar(master, orient=tk.HORIZONTAL)
        xscroll.pack(before=box, side=tk.BOTTOM, fill=tk.X)
        xscroll.config(command=box.xview)
        box.config(xscrollcommand=xscroll.set)


def path_to_dnd(path: Path) -> str:
    """Converts a `Path` into an acceptable value for `tkinterdnd2.`"""

    # tkinterdnd2 will only accept fs paths with forward slashes, even on Windows.
    wants_sep = '/'
    if os.path.sep == wants_sep:
        return str(path)
    else:
        return wants_sep.join(str(path).split(os.path.sep))


def searcher(func):
    """Wrapper for functions that perform searches."""

    # Don't want the tkinter event object.
    def inner(self, _=None):
        try:
            return func(self)
        except IndexError:
            # An event handler for listbox selection can be called even when
            # nothing is selected, so silently ignore it.
            pass

    return inner


def check_active(func):
    """Wrapper for functions that verify a patch is currently loaded."""

    def inner(self, *args):
        if self.active_patch > -1:
            return func(self, *args)

    return inner


class AppGui(App, ttk.Frame):
    """Graphical implementation of the `App`."""

    # List containing all widgets with the ability to change the GUI's state from idle->busy or vice versa
    busy_wids = []

    status_text: tk.StringVar  # Text of the status label on the bottom
    banks_list: tk.StringVar  # List which populates the banks listbox
    active_tags: tk.StringVar  # List which populates the tag selection listbox
    patch_list: ttk.Treeview  # Treeview of patches which match the search results
    kwd_entry: ttk.Entry  # Keyword search text box

    schema: PatchSchema

    def __init__(self, master: tk.Tk):
        """Creates a new graphical instance of the program within the specified `Tk` instance."""

        ttk.Frame.__init__(self, master)
        self.schema = Synth1()
        self.pack()
        self.root = self.master.winfo_toplevel()

        self.root.withdraw()
        self.root.protocol('WM_DELETE_WINDOW', self.end)
        self.root.report_callback_exception = self.exc

        ##################################################
        #              BEGIN UI DEFINITIONS              #
        ##################################################

        paned_win = tk.PanedWindow(orient=tk.HORIZONTAL)
        paned_win.pack(fill=tk.BOTH, expand=True)
        self.root.title('%s - %s' % (self.schema.synth_name, APP_NAME))

        menubar = tk.Menu(self.master)
        file = tk.Menu(menubar, tearoff=False)
        file.add_command(label='Create new database...',
                         command=self.new_database_prompt)
        file.add_separator()
        file.add_command(label='Exit', command=self.end)
        menubar.add_cascade(label='File', menu=file)

        edit = tk.Menu(menubar, tearoff=False)
        edit.add_command(label='Run name-based tagging...',
                         command=self.tag_names)
        edit.add_command(label='Run parameter-based tagging...',
                         command=self.tag_similar)
        edit.add_separator()
        edit.add_command(label='Settings')
        menubar.add_cascade(label='Edit', menu=edit)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label='%s Website' % APP_NAME,
                              command=lambda: webbrowser.open(APP_WEBSITE, new=2))

        menubar.add_cascade(label='Help', menu=help_menu)
        self.master.config(menu=menubar)

        ###############################################
        #              BEGIN SEARCH PANE              #
        ###############################################

        self.search_pane = ttk.Frame(self.master)
        self.search_pane.pack(**PANE_PACKWARGS)
        paned_win.add(self.search_pane, stretch=NEVER)
        self.search_pane.columnconfigure(0, weight=1)

        kwd_frame = ttk.Frame(self.search_pane)
        kwd_frame.columnconfigure(0, weight=1)
        kwd_frame.grid(row=0, column=0, sticky=tk.NSEW)
        # width=0 means the Entry won't stretch the pane at all.
        self.kwd_entry = ttk.Entry(kwd_frame, width=0)
        self.kwd_entry.bind('<Key>', self.search_keypress_handler)
        self.kwd_entry.grid(row=0, column=0, sticky=tk.NSEW)
        self.busy_wids.append(self.kwd_entry)
        self.kwd_btn = ttk.Button(kwd_frame, text='Search',
                                  command=self.search_by_kwd)
        self.kwd_btn.grid(row=0, column=1, sticky=tk.NSEW)
        self.busy_wids.append(self.kwd_btn)

        tags_frame = ttk.Frame(self.search_pane)
        self.search_pane.rowconfigure(1, weight=1)
        tags_frame.grid(row=1, column=0, sticky=tk.NSEW)
        self.active_tags = tk.StringVar()
        self.tags_lb = tk.Listbox(
            tags_frame, listvariable=self.active_tags, selectmode=tk.EXTENDED, **LB_KWARGS)
        self.tags_lb.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        scrollbars(self.master, self.tags_lb)
        self.tags_lb.bind('<<ListboxSelect>>', self.search_by_tags)
        self.busy_wids.append(self.tags_lb)

        banks_frame = ttk.Frame(self.search_pane)
        self.search_pane.rowconfigure(2, weight=1)
        banks_frame.grid(row=2, column=0, sticky=tk.NSEW)
        self.banks_list = tk.StringVar()
        self.banks_lb = tk.Listbox(
            banks_frame, listvariable=self.banks_list, selectmode=tk.SINGLE, **LB_KWARGS)
        self.banks_lb.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        scrollbars(self.master, self.banks_lb)
        self.banks_lb.bind('<<ListboxSelect>>', self.search_by_bank)
        self.busy_wids.append(self.banks_lb)

        #############################################
        #              END SEARCH PANE              #
        #############################################

        ################################################
        #              BEGIN PATCHES PANE              #
        ################################################

        patches_pane = ttk.Frame(self.master)
        patches_pane.pack(**PANE_PACKWARGS)
        paned_win.add(patches_pane, stretch=ALWAYS)

        # Foreground colors set in Treeview tags don't work on Windows with Tk 8.6.9.
        # Python 3.10 and newer have an updated version of Tk where this bug is no longer present.
        # Bug and fix described here: https://bugs.python.org/issue36468
        if sys.platform == 'win32' and sys.version_info.major == 3 and sys.version_info.minor < 10:
            def fixed_map(option):
                return [elm for elm in style.map('Treeview', query_opt=option) if
                        elm[:2] != ('!disabled', '!selected')]

            style = ttk.Style()
            style.map('Treeview', foreground=fixed_map('foreground'), background=fixed_map('background'))

        self.patch_list = ttk.Treeview(patches_pane, columns=(
            'name', 'patch_tags'), show='headings', style='patchList.Treeview')
        self.patch_list.pack(**PANE_PACKWARGS)
        self.patch_list.bind('<<TreeviewSelect>>', self.update_active_patch)

        self.status_text = tk.StringVar(value=STATUS_MSGS[STATUS_READY])
        status_label = ttk.Label(patches_pane, textvariable=self.status_text)
        status_label.pack(
            before=self.patch_list, side=tk.BOTTOM, anchor=tk.W)

        scrollbars(patches_pane, self.patch_list, draw_x=False)
        for c in TREE_COLORS:
            self.patch_list.tag_configure(**c._asdict())
        self.patch_list.heading('name', text='Name')
        self.patch_list.heading('patch_tags', text='Tags')

        if DND_SUPPORT:
            self.patch_list.drag_source_register(1, DND_FILES)
            self.patch_list.dnd_bind('<<DragInitCmd>>', self.quick_export)

        ##############################################
        #              END PATCHES PANE              #
        ##############################################

        #############################################
        #              BEGIN META PANE              #
        #############################################

        meta_pane = ttk.Frame(self.master)
        meta_pane.pack(**PANE_PACKWARGS)
        paned_win.add(meta_pane, stretch=NEVER)
        meta_pane.columnconfigure(0, weight=1)

        meta_pane.rowconfigure(0, weight=2)
        info_pane = ttk.Frame(meta_pane)
        info_pane.grid(row=0, column=0, sticky=tk.NSEW, columnspan=2)

        bold_font = font.nametofont('TkDefaultFont').copy()
        bold_font.configure(weight=font.BOLD)

        self.active_name = tk.StringVar(value=EMPTY_PATCH_NAME)
        name_lbl = ttk.Label(info_pane, textvariable=self.active_name, font=bold_font, width=LB_KWARGS['width'],
                             wraplength=LB_KWARGS['width'] * 10)
        name_lbl.pack(anchor=tk.W)

        self.active_bank = tk.StringVar()
        bank_lbl = ttk.Label(info_pane, textvariable=self.active_bank, wraplength=LB_KWARGS['width'] * 10)
        bank_lbl.pack(anchor=tk.W)

        self.active_tags_editor = tk.StringVar()
        tags_editor = tk.Listbox(info_pane, selectmode=tk.SINGLE, listvariable=self.active_tags_editor, **LB_KWARGS)
        tags_editor.pack(**PANE_PACKWARGS)

        meta_pane.rowconfigure(1, weight=0)
        meta_pane.columnconfigure(0, weight=1)
        meta_pane.columnconfigure(1, weight=1)

        plus_btn = ttk.Button(meta_pane, text='+', command=self.tag_prompt)
        plus_btn.grid(row=1, column=0, sticky=tk.NSEW)
        minus_btn = ttk.Button(meta_pane, text='-')
        minus_btn.grid(row=1, column=1, sticky=tk.NSEW)

        ttk.Separator(meta_pane, orient=tk.HORIZONTAL).grid(row=2, columnspan=2, sticky=tk.EW)

        # buttons
        fxp_btn = ttk.Button(meta_pane, text='.fxp', command=self.fxp_export)
        meta_pane.rowconfigure(3, weight=0)
        fxp_btn.grid(row=3, column=0, sticky=tk.NSEW)

        if self.schema.file_ext is not None:
            native_btn = ttk.Button(meta_pane, text='.' + self.schema.file_ext, command=self.native_export)
            native_btn.grid(row=3, column=1, sticky=tk.NSEW)

        ###########################################
        #              END META PANE              #
        ###########################################

        self.root.deiconify()
        super().__init__(self.schema)

    def info(self, msg: str, title='Info'):
        """Displays an informational message to the user."""

        messagebox.showinfo(title, msg)

    def err(self, msg: str):
        """Displays an error message to the user."""

        messagebox.showerror('Error', msg)

    def exc(self, ex, val, tb):
        """Exception handler for Tkinter."""

        print_exception(ex, val, tb)
        self.status(STATUS_READY)
        self.err(str(val))

    def busy_state(self, state):
        """Changes the state of the program to `state`."""

        for w in self.busy_wids:
            w.config(state=state)

    def clear_selection(self):
        """Clears all currently selected items in the search pane listboxes."""

        for lb in (self.tags_lb, self.banks_lb):
            lb.selection_clear(0, tk.END)

    def clear_keyword(self):
        """Clears the keyword search box."""

        self.kwd_entry.delete(0, tk.END)

    def clear_search(self):
        """Clears the search pane."""

        self.clear_selection()
        self.clear_keyword()

    def wait(self):
        """Informs the user that the program is busy."""

        self.root.config(cursor='watch')
        # disable widgets that could change the program state while it's still loading something
        self.busy_state(tk.DISABLED)
        self.master.update()  # update in case something locks the ui

    def unwait(self):
        """Informs the user that the program is no longer busy."""

        self.root.config(cursor='')
        self.busy_state(tk.NORMAL)

    def put_patch(self, patch):
        self.patch_list.insert('', patch.name, patch.name, values=(
            patch['patch_name'], patch['tags']), tags=(patch['color']))

    def empty_patches(self):
        """Empties the patch Treeview."""

        kids = self.patch_list.get_children()
        if len(kids) > 0:
            self.update_active_patch()
            self.patch_list.delete(*kids)

    def search_done(self):
        """Updates the status text with the number of visible patches."""

        kids = self.patch_list.get_children()
        count = len(kids)
        if count > 0:
            new_text = 'Found ' + \
                       str(count) + ' patch' + ('es.' if count > 1 else '.')

            # self.patch_list.focus_set()
            self.patch_list.see(kids[0])
        else:
            new_text = 'No patches found.'

        self.status_text.set(new_text)

    def update_active_patch(self, _=None):
        """Updates the cache of the currently active patch."""

        sel = self.patch_list.selection()
        if len(sel) > 0:
            # iid of treeview element
            self.active_patch = int(sel[0])
        else:
            self.active_patch = -1
        self.update_meta()

    def update_meta(self):
        """Updates the metadata pane with information about the selected patch."""

        data = self.get_meta()
        self.active_bank.set(data.get('bank', EMPTY))
        self.active_name.set(data.get('name', EMPTY_PATCH_NAME))
        self.active_tags_editor.set(data.get('tags', EMPTY))

    @check_active
    def quick_export(self, _):
        """Event handler for dragging an entry from the patch `Treeview`."""

        # Delay since tkinterdnd needs instant return
        self.root.after(70, super().quick_export, self.active_patch)
        return MOVE, DND_FILES, path_to_dnd(self.quick_tmp)

    @check_active
    def fxp_export(self):
        """Exports the active patch to a .fxp file after prompting the user for a path."""

        out_path = filedialog.asksaveasfilename(
            title='Export as a .fxp file',
            initialfile=self.name_patchfile(),
            initialdir=self.get_export_path(),
            filetypes=(('VST preset file', '*.fxp'),))
        if len(out_path) != 0:
            self.export_patch(None, Path(out_path))

    @check_active
    def native_export(self):
        """Exports the active patch to a native patch file after prompting the user for a path."""

        out_path = filedialog.asksaveasfilename(
            title='Export as a .%s file' % self.schema.file_ext,
            initialfile='%s.%s' % (self.schema.file_base, self.schema.file_ext),
            initialdir=self.get_export_path(),
            filetypes=(('%s preset file' % self.schema.synth_name, '*.%s' % self.schema.file_ext),))
        if len(out_path) != 0:
            self.export_patch(PATCH_FILE, Path(out_path))

    @check_active
    def tag_prompt(self):
        """Prompts the user to add a tag to the active patch."""

        tag = simpledialog.askstring('Add a tag...', 'Tag this patch with:')
        if tag is not None and tag != EMPTY:
            self.add_tag(tag)

    def refresh(self):
        """Refreshes the GUI to reflect new cached data."""

        super().refresh()
        #self.clear_search()
        self.active_tags.set(self.tags)
        self.banks_list.set(self.banks)

        if self.active_patch > -1:
            self.update_meta()

    @searcher
    def search_by_tags(self):
        """Searches for patches matching the currently selected tag(s) in the tags `Listbox`."""

        self.clear_keyword()
        super().search_by_tags([self.tags_lb.get(i)
                                for i in self.tags_lb.curselection()])

    @searcher
    def search_by_bank(self):
        """Searches for patches belonging to the currently selected bank in the banks `Listbox`."""

        self.clear_keyword()
        super().search_by_bank(self.banks_lb.get(
            self.banks_lb.curselection()[0]))

    @searcher
    def search_by_kwd(self):
        """Searches for patches matching the query currently entered in the keyword `Entry`."""

        self.clear_selection()
        super().keyword_search(self.kwd_entry.get().strip())

    def search_keypress_handler(self, event):
        """Event handler for pressing a key in the keyword `Entry`."""

        if event.char == '\r':
            self.search_by_kwd()

    def status(self, msg):
        """Updates the status indicator with the static status message defined by `msg`."""

        self.status_text.set(STATUS_MSGS[msg])
        super().status(msg)

    def new_database_prompt(self):
        """Prompts the user to select a directory containing patch banks and then imports that directory."""

        new_dir = filedialog.askdirectory(
            title='Select the folder containing your banks:', initialdir=FILE_KWARGS['initialdir'])
        if len(new_dir) != 0:
            super().new_database(new_dir)

    def end(self):
        """Closes the program."""

        self.root.withdraw()
        super().end()
        self.master.destroy()


__all__ = ['AppGui']
