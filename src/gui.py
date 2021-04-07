import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from traceback import print_exception
from collections import namedtuple
from random import choice
from common import *
from app import *
from tkinterdnd2 import *

TAGS_TAB = 'tags'
BANKS_TAB = 'banks'
MISC_SRCH_TAB = 'search'
INFO_TAB = 'info'
MISC_META_TAB = 'meta'

# Arguments for packing ttk notebooks and *most* widgets inside of them.
TABS_PACKWARGS = {'fill': tk.BOTH, 'side': tk.LEFT,
                  'expand': True, 'anchor': tk.W}

# For coloring ttk treeview entries with the patch's color
TreeColor = namedtuple('TreeColor', ('tagname', 'foreground'))

TREE_COLORS = (TreeColor('red', '#ff4d4f'), TreeColor('blue', '#5557fa'), TreeColor('green', '#10b526'),
               TreeColor('yellow', '#cbcb18'), TreeColor('magenta', '#ff54b5'), TreeColor('cyan', '#00b5b2'))

# Listbox dimensions and color
LB_KWARGS = {'width': 25, 'height': 30, 'selectbackground': '#d6be48'}

# Common properties of open/save dialogs
FILE_KWARGS = {'filetypes': (('All files', '*')), 'initialdir': str(DATA_DIR)}


def scrollbars(master, box, drawX=True, drawY=True):
    """Constructs scrollbars for a `Listbox` or `Treeview`."""

    if drawY:
        yscroll = ttk.Scrollbar(master)
        yscroll.pack(before=box, side=tk.RIGHT, fill=tk.Y)
        yscroll.config(command=box.yview)
        box.config(yscrollcommand=yscroll.set)
    if drawX:
        xscroll = ttk.Scrollbar(master, orient=tk.HORIZONTAL)
        xscroll.pack(before=box, side=tk.BOTTOM, fill=tk.X)
        xscroll.config(command=box.xview)
        box.config(xscrollcommand=xscroll.set)


class AppGui(App, ttk.Frame):
    """Graphical implementation of the `App`."""

    # List containing all widgets with the ability to change the program's state from idle->busy or vice versa
    busy_wids = []

    status_text: tk.StringVar  # Text of the status label on the bottom
    banks_list: tk.StringVar  # List which propogates the banks listbox
    tags_list: tk.StringVar  # List which propogates the tags listbox
    info_list: tk.StringVar  # List which propogates the patch info listbox
    patch_list: ttk.Treeview  # Treeview of patches which match the search results
    kwd_entry: ttk.Entry  # Keyword search text box

    info = messagebox.showinfo

    def __init__(self, master: tk.Tk):
        """Creates a new graphical instance of the program within the specified `Tk` instance."""

        ttk.Frame.__init__(self, master)
        self.pack()
        self.root = self.master.winfo_toplevel()

        self.root.withdraw()
        self.root.protocol('WM_DELETE_WINDOW', self.end)
        self.root.report_callback_exception = self.exc

        ################################################
        ############# BEGIN UI DEFINITIONS #############
        ################################################

        paned_win = tk.PanedWindow(orient=tk.HORIZONTAL)
        paned_win.pack(fill=tk.BOTH, expand=True)
        self.root.title(APP_NAME)

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
        edit.add_command(label='(Re-)train model...',
                         command=self.create_model)
        edit.add_command(label='Settings')
        menubar.add_cascade(label='Edit', menu=edit)

        help = tk.Menu(menubar, tearoff=False)
        help.add_command(label='About', command=lambda: messagebox.showinfo(
            'About %s' % APP_NAME, '%s 0.0.1\nTame your %s patches' % (APP_NAME, SYNTH_NAME)))

        menubar.add_cascade(label='Help', menu=help)
        self.master.config(menu=menubar)

        ############## BEGIN SEARCH PANE ##############

        self.search_pane = ttk.Notebook(self.master)
        self.search_pane.pack(**TABS_PACKWARGS)
        paned_win.add(self.search_pane, stretch='never')

        tags_tab = ttk.Frame(self.search_pane, name=TAGS_TAB)
        tags_tab.pack(**TABS_PACKWARGS)
        self.tags_list = tk.StringVar()
        self.tags_lb = tk.Listbox(
            tags_tab, listvariable=self.tags_list, selectmode=tk.EXTENDED, **LB_KWARGS)
        self.tags_lb.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        scrollbars(self.master, self.tags_lb)
        self.tags_lb.bind('<<ListboxSelect>>', self.search_by_tags)
        self.busy_wids.append(self.tags_lb)
        self.search_pane.add(tags_tab, text='Tags')

        banks_tab = ttk.Frame(self.search_pane, name=BANKS_TAB)
        banks_tab.pack(**TABS_PACKWARGS)
        self.banks_list = tk.StringVar()
        self.banks_lb = tk.Listbox(
            banks_tab, listvariable=self.banks_list, selectmode=tk.SINGLE, **LB_KWARGS)
        self.banks_lb.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        scrollbars(self.master, self.banks_lb)
        self.banks_lb.bind('<<ListboxSelect>>', self.search_by_bank)
        self.busy_wids.append(self.banks_lb)
        self.search_pane.add(banks_tab, text='Banks')

        kwd_tab = ttk.Frame(self.search_pane, name=MISC_SRCH_TAB)
        kwd_tab.pack(**TABS_PACKWARGS)
        self.kwd_entry = ttk.Entry(kwd_tab)
        self.kwd_entry.bind('<Return>', self.search_by_kwd)
        self.kwd_entry.pack(fill=tk.X)
        self.busy_wids.append(self.kwd_entry)
        self.kwd_btn = ttk.Button(kwd_tab, text='Search',
                                  command=self.search_by_kwd)
        self.kwd_btn.pack(anchor=tk.NW)
        self.busy_wids.append(self.kwd_btn)
        self.search_pane.add(kwd_tab, text='Keyword')

        ############## END SEARCH PANE ##############

        ############## BEGIN PATCHES PANE ##############

        patches_pane = ttk.Frame(self.master)
        patches_pane.pack(**TABS_PACKWARGS)
        paned_win.add(patches_pane, stretch='always')

        self.patch_list = ttk.Treeview(patches_pane, columns=(
            'name', 'patch_tags'), show='headings', style='patchList.Treeview')
        self.patch_list.pack(**TABS_PACKWARGS)
        self.patch_list.bind('<<TreeviewSelect>>', self.update_active_patch)

        self.status_text = tk.StringVar(value=STATUS_MSGS[STATUS_READY])
        status_label = ttk.Label(patches_pane, textvariable=self.status_text)
        status_label.pack(
            before=self.patch_list, side=tk.BOTTOM, anchor=tk.W)

        scrollbars(patches_pane, self.patch_list, drawX=False)
        for c in TREE_COLORS:
            self.patch_list.tag_configure(**c._asdict())
        self.patch_list.heading('name', text='Name')
        self.patch_list.heading('patch_tags', text='Tags')

        self.patch_list.drag_source_register(1, DND_FILES)
        self.patch_list.dnd_bind('<<DragInitCmd>>', self.quick_export)

        ############## END PATCHES PANE ##############

        ############## BEGIN META PANE ##############

        meta_pane = ttk.Notebook(self.master)
        meta_pane.pack(**TABS_PACKWARGS)
        paned_win.add(meta_pane, stretch='never')

        info_tab = ttk.Frame(self.master, name=INFO_TAB)
        info_tab.pack(**TABS_PACKWARGS)

        self.info_list = tk.StringVar()
        info_lb = tk.Listbox(
            info_tab, listvariable=self.info_list, selectmode=tk.SINGLE, **LB_KWARGS)
        info_lb.pack(**TABS_PACKWARGS)
        meta_pane.add(info_tab, text='Info')

        misc_meta_tab = ttk.Frame(self.master, name=MISC_META_TAB)
        misc_meta_tab.pack(**TABS_PACKWARGS)

        meta_pane.add(misc_meta_tab, text='Insights')

        ############## END META PANE ##############

        self.root.deiconify()
        super().__init__()

    def err(self, msg: str):
        """Displays an error message to the user."""

        self.status(STATUS_READY)
        messagebox.showerror('Error', msg)

    def exc(self, ex, val, tb):
        """Exception handler for Tkinter."""

        print_exception(ex, val, tb)
        self.err(str(val))

    def busy_state(self, state):
        """Updates all busy widgets to `state`."""

        for w in self.busy_wids:
            w.config(state=state)

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

    def put_patch(self, patch: PatchMetadata):
        self.patch_list.insert('', patch.index, patch.index, values=(
            patch.name, patch.tags), tags=(patch.color))

    def empty_patches(self):
        """Empties the patch Treeview."""

        kids = self.patch_list.get_children()
        if len(kids) > 0:
            self.update_active_patch()
            self.patch_list.delete(*kids)

    def count_patches(self):
        """Update the status text with the number of visible patches."""

        kids = self.patch_list.get_children()
        count = len(kids)
        if count > 0:
            new_text = 'Found ' + \
                str(count) + ' patch' + ('es.' if count > 1 else '.')

            # self.patch_list.focus_set()
            self.patch_list.see(kids[0])
        else:
            new_text = choice(('No patches found.',
                               'Better luck next time.',
                               'I looked everywhere.',
                               r'¯\_(ツ)_/¯',
                               'No patch for you.',
                               "I'm sorry Dave, I'm afraid I can't do that."))

        self.status_text.set(new_text)
        self.unwait()

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

        self.info_list.set(super().update_meta())

    def quick_export(self, _):
        """Event handler for dragging an entry from the patch `Treeview`."""

        if self.active_patch > -1:
            return (MOVE, DND_FILES, super().quick_export(self.active_patch))

    def refresh(self):
        """Refreshes the GUI to reflect new cached data."""

        super().refresh()
        self.tags_list.set(self.tags)
        self.banks_list.set(self.banks)

        # TODO only switch tab if banks or tags is selected
        if len(self.tags) == 0:
            to_select = BANKS_TAB
        else:
            to_select = TAGS_TAB
        self.search_pane.select('.!notebook.' + to_select)

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

    @searcher
    def search_by_tags(self):
        """Searches for patches matching the currently selected tag(s) in the tags `Listbox`."""

        super().search_by_tags([self.tags_lb.get(i)
                                for i in self.tags_lb.curselection()])

    @searcher
    def search_by_bank(self):
        """Searches for patches belonging to the currently selected bank in the banks `Listbox`."""

        super().search_by_bank(self.banks_lb.get(
            self.banks_lb.curselection()[0]))

    @searcher
    def search_by_kwd(self):
        """Searches for patches matching the query currently entered in the keyword `Entry`."""

        super().keyword_search(self.kwd_entry.get().strip())

    def status(self, msg):
        """Updates the status indicator with the static status message defined by `msg`."""

        self.status_text.set(STATUS_MSGS[msg])
        super().status(msg)

    def new_database_prompt(self):
        """Prompts the user to select a directory containing patch banks and then imports that directory."""

        dir = filedialog.askdirectory(
            title='Select the folder containing your %s banks:' % SYNTH_NAME, initialdir=FILE_KWARGS['initialdir'])
        if len(dir) != 0:
            super().new_database(dir)

    def end(self):
        """Closes the program."""

        super().end()
        self.master.destroy()


__all__ = ['AppGui']
