import configparser
import re
import json
from pathlib import Path
from src.data import *
from src.common import *
from src.patches import PatchSchema

DEFAULT_CONFIG = {
    'database': {
        'auto_load': True,
        'auto_save': True
    },
    'synth_interface': {
        'export_as': FXP_CHUNK,
        'export_to': Path.home()
    }
}

TMP_FXP_NAME = '%s_tmp.%s' % (APP_NAME_INLINE, FXP_FILE_EXT)

STATUS_MSGS = {
    STATUS_READY: 'Ready.',
    STATUS_IMPORT: 'Importing banks...',
    STATUS_NAME_TAG: 'Running name-based tagging...',
    STATUS_SIM_TAG: 'Running parameter-based tagging...',
    STATUS_OPEN: 'Opening database...',
    STATUS_SEARCH: 'Searching...',
    STATUS_WAIT: 'Working...'
}

CONFIG_FILE = 'config.ini'
DB_FILE = 'db'

FNAME_REMOVE = re.compile(r'[^\w ]+')


def searcher(func):
    """Wrapper for functions that perform searches."""

    def inner(self, q):
        if len(q):
            self.status(STATUS_SEARCH)
            self.empty_patches()

            self.last_query = (func.__name__, q)
            self.last_result = func(self, q)

            if self.last_result is not None:
                self.last_result.apply(self.put_patch, axis=1)

            self.search_done()
            self.unwait()
            return True
        return False

    return inner


def volatile(func):
    """Wrapper for functions that manipulate the active database."""

    def inner(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        self.refresh()
        self.modified_db = True
        return ret

    return inner


class App:
    """Implements the program's controller."""

    __db: PatchDatabase  # The active patch database
    __config: configparser.ConfigParser
    __data_dir: Path
    __config_file: Path
    schema: PatchSchema

    quick_tmp: Path  # Temporary file for quick export
    active_patch: int = -1  # Index in db of currently active patch
    last_query = ('', '')
    last_result = None
    modified_db = False

    tags = []  # tag indexes for active database
    banks = []  # bank indexes for active database

    def __init__(self, schema: PatchSchema):
        """Creates a new instance of the program."""

        self.status(STATUS_OPEN)

        self.__data_dir = Path.home() / ('.%s' % APP_NAME_INLINE)
        self.__config_file = self.__data_dir / CONFIG_FILE
        self.__db_file = self.__data_dir / DB_FILE
        self.schema = schema
        self.__db = PatchDatabase(self.schema)
        self.__config = configparser.ConfigParser()

        self.load_config()
        self.status(STATUS_READY)

    def info(self, msg: str):
        """Define this. It should display an informational message to the user."""
        ...

    def err(self, msg: str):
        """Define this. It should display an error message to the user."""
        ...

    def put_patch(self, patch):
        """Define this. It should add the `patch` to a list of patches visible to the user."""
        ...

    def wait(self):
        """Define this. It should inform the user that the program is busy."""
        ...

    def unwait(self):
        """Define this. It should inform the user that the program is no longer busy."""
        ...

    def empty_patches(self):
        """Define this. It should empty the user-facing list of patches."""
        ...

    def search_done(self):
        """Define this. It's called whenever a search is finished."""
        ...

    def get_meta(self) -> dict:
        """Returns the metadata of the active patch."""

        if self.active_patch > -1:
            patch = self.last_result.loc[self.active_patch]
            return {
                'name': patch['patch_name'],
                'bank': patch['bank'],
                'tags': self.__db.get_tags(self.active_patch)
            }
        else:
            return dict()

    @searcher
    def tag_search(self, tags: list):
        """Searches for patches matching `tags`."""

        return self.__db.find_patches_by_tags(tags)

    @searcher
    def bank_search(self, bank: str):
        """Searches for patches in bank `bank`."""

        return self.__db.find_patches_by_val(bank, 'bank', exact=True)

    @searcher
    def keyword_search(self, kwd: str):
        """Searches for patches matching keyword `kwd`."""

        return self.__db.keyword_search(kwd)

    def refresh(self):
        """Refreshes cached indexes."""

        self.tags = self.__db.tags.to_list()
        self.banks = self.__db.banks
        self.status(STATUS_READY)

        if len(self.last_query[0]):
            getattr(self, self.last_query[0])(self.last_query[1])

    @volatile
    def tag_names(self):
        """Tags patches based on their names."""

        from src.sorting import TAGS_NAMES
        self.status(STATUS_NAME_TAG)
        self.__db.tags_from_val_defs(TAGS_NAMES, 'patch_name')

    @volatile
    def tag_names_custom(self, path):
        """Tags patches based on their names, using the custom definitions in the JSON file at `path`."""

        with open(path, 'r') as f:
            tags_names = json.load(f)
        self.status(STATUS_NAME_TAG)
        self.__db.tags_from_val_defs(tags_names, 'patch_name')

    @volatile
    def tag_similar(self):
        """Tags patches based on their similarity to other patches."""

        self.status(STATUS_WAIT)
        acc = self.__db.train_classifier()
        self.info('Based on your current tags, this tagging method is estimated to be %f%% accurate. ' % (acc * 100) +
                  'To improve its accuracy, manually tag some untagged patches and correct existing tags, then run '
                  'this again.')
        self.status(STATUS_SIM_TAG)
        self.__db.classify_tags()

    @volatile
    def add_tag(self, tag: str):
        """Adds `tag` to the active patch's tags."""

        self.__db.change_tags(self.active_patch, [tag], False)

    @volatile
    def remove_tag(self, tag: str):
        """Removes `tag` from the active patch's tags."""

        tags = self.__db.get_tags(self.active_patch)
        tags.remove(tag)
        self.__db.change_tags(self.active_patch, tags, True)

    def status(self, msg):
        """Fully implement this function by updating a user-facing status indicator before calling the super."""

        if msg == STATUS_READY:
            self.unwait()
        else:
            self.wait()

    @volatile
    def new_database(self, patches_dir):
        """Creates a new database with patches from `dir`."""

        self.status(STATUS_IMPORT)
        self.__db.bootstrap(Path(patches_dir))

    def open_database(self, silent=False):
        """Loads a previously saved database."""

        path = self.__db_file
        if path.is_file():
            try:
                self.__db.from_disk(path)
                self.modified_db = False
                self.refresh()
            except FileNotFoundError:
                if not silent:
                    raise Exception('That is not a valid data file.')

    def save_database(self, path=None):
        """Saves the active database to the file at `path`, or the default database file."""

        if self.__db.is_active() and self.modified_db:
            self.__db.to_disk(path if path else self.__db_file)
            self.modified_db = False

    @volatile
    def unduplicate(self):
        """Removes duplicate patches from the database."""

        self.__db.remove_duplicates()

    def load_config(self):
        """Loads the config file for the program, or create one if it doesn't exist."""

        self.__data_dir.mkdir(exist_ok=True)
        self.__config.read_dict(DEFAULT_CONFIG)
        if self.__config_file.is_file():
            self.__config.read(self.__config_file)
        else:
            self.__config_file.touch()

        if self.__config.get('synth_interface', 'export_as') == PATCH_FILE:
            self.quick_tmp = Path(
                self.__data_dir / ('%s.%s' % (self.schema.file_base, self.schema.file_ext))).resolve()
        else:
            self.quick_tmp = Path(self.__data_dir / TMP_FXP_NAME).resolve()
        self.quick_tmp.touch(exist_ok=True)

        if self.__config.getboolean('database', 'auto_load'):
            self.open_database(silent=True)

    def get_config_path(self) -> Path:
        """Returns the `Path` to the `App`'s configuration file."""

        return self.__config_file

    def export_patch(self, typ, path: Path):
        """Exports the active patch as type `typ`."""

        if typ is None:
            typ = self.__config.get('synth_interface', 'export_as')

        self.__config.set('synth_interface', 'export_to', str(path.parent.resolve()))
        self.__db.write_patch(self.active_patch, typ, path)

    def get_export_path(self):
        """Returns the default path for exporting patches."""

        return self.__config.get('synth_interface', 'export_to')

    def name_patchfile(self, typ=None):

        if typ == PATCH_FILE:
            fname = (self.schema.file_base, self.schema.file_ext)
        else:
            # regex sub to remove any unwanted characters from the file name.
            fname = (FNAME_REMOVE.sub('', self.last_result.loc[self.active_patch]['patch_name']), FXP_FILE_EXT)
        return '%s.%s' % fname

    def quick_export(self, ind: int):
        """Exports the patch at index `ind` using quick settings. The patch will be saved at the path
        `self.quick_tmp`. """

        self.__db.write_patch(ind, self.__config.get('synth_interface', 'export_as'), self.quick_tmp)

    def end(self):
        """Housekeeping before exiting the program."""

        if self.__config.getboolean('database', 'auto_save'):
            self.save_database()

        with open(self.__config_file, 'w') as cfile:
            self.__config.write(cfile)
        self.quick_tmp.unlink(missing_ok=True)


__all__ = ['App', 'STATUS_MSGS', 'PATCH_FILE']
