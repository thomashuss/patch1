import configparser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from typing import NamedTuple
from data import *
from sorting import TAGS_NAMES
from common import *

CONFIG_FILE = DATA_DIR / 'config.ini'
DEFAULT_CONFIG = {
    'database': {
        'auto_load': True,
        'auto_save': True
    },
    'synth_interface': {
        'quick_export_as': FXP_CHUNK,
        'export_to': Path.home()
    }
}
TMP_FXP_NAME = '%s_tmp.%s' % (APP_NAME, FXP_FILE_EXT)
TMP_PFILE_NAME = '%s.%s' % (PATCH_NUMS[0], PATCH_FILE_EXT)

STATUS_MSGS = {
    STATUS_READY: 'Ready.',
    STATUS_IMPORT: 'Importing banks...',
    STATUS_NAME_TAG: 'Running name-based tagging...',
    STATUS_SIM_TAG: 'Running parameter-based tagging...',
    STATUS_OPEN: 'Opening database...',
    STATUS_SEARCH: 'Searching...',
    STATUS_WAIT: 'Working...'
}


class PatchMetadata(NamedTuple):
    index: int
    name: str
    bank: str
    num: str
    color: str
    ver: str
    tags: str

    @classmethod
    def from_patch(cls, patch):
        """Constructs a new `PatchMetadata` object from the `patch`."""

        return cls(patch.name, patch['patch_name'], patch['bank'], patch['num'], patch['color'], patch['ver'], tags_to_str(patch['tags']))


class App:
    """Implements the program's controller."""

    _db: PatchDatabase  # The active patch database
    _config: configparser.ConfigParser
    _exe: ThreadPoolExecutor  # When a task needs to run in the background

    quick_tmp: Path  # Temporary file for quick export
    active_patch: int = -1  # Index in db of currently active patch
    last_query = ''  # Last search query, to avoid redundant queries

    tags = []  # tag indexes for active database
    banks = []  # bank indexes for active database

    def __init__(self):
        """Creates a new instance of the program."""

        self.status(STATUS_OPEN)

        self._exe = ThreadPoolExecutor(max_workers=1)
        self._config = configparser.ConfigParser()

        self.load_config()
        self.status(STATUS_READY)

    def _put_patch(self, patch):
        """Internal use only"""

        self.put_patch(PatchMetadata.from_patch(patch))

    def put_patch(self, patch: PatchMetadata):
        """Define this. It should add the `patch` to a list of patches visible to the user."""
        pass

    def wait(self):
        """Define this. It should inform the user that the program is busy."""
        pass

    def unwait(self):
        """Define this. It should inform the user that the program is no longer busy."""
        pass

    def empty_patches(self):
        """Define this. It should empty the user-facing list of patches."""
        pass

    def search_done(self):
        """Define this. It's called whenever a search is finished."""
        pass

    def update_meta(self) -> list:
        """This should update the user-facing metadata list with the return value of the super function."""

        if self.active_patch > -1:
            patch = self.by_index(self.active_patch)
            return [
                'Name:', patch.name, '',
                'Bank:', '%s (#%s)' % (patch.bank, patch.num), '',
                'Tags:', patch.tags, '',
                '%s version:' % SYNTH_NAME, patch.ver
            ]
        else:
            return []

    def searcher(func):
        """Wrapper for functions that perform searches."""

        def inner(self, q):
            if len(q) > 0 and self.last_query != q:
                self.last_query = q
                self.status(STATUS_SEARCH)
                func(self, q)
                self.search_done()
                self.unwait()
                return True
            return False
        return inner

    @searcher
    def search_by_tags(self, tags: list):
        """Searches for patches matching `tags`."""

        self._db.find_patches_by_tags(tags).apply(self._put_patch, axis=1)

    @searcher
    def search_by_bank(self, bank: str):
        """Searches for patches in bank `bank`."""

        self._db.find_patches_by_val(
            bank, 'bank', exact=True).apply(self._put_patch, axis=1)

    @searcher
    def keyword_search(self, kwd: str):
        """Searches for patches matching keyword `kwd`."""

        self._db.keyword_search(kwd).apply(self._put_patch, axis=1)

    def refresh(self):
        """Refreshes cached indexes."""

        self.tags = self._db.tags
        self.banks = self._db.banks
        self.status(STATUS_READY)

    def reload(self, result):
        """Replaces the active database instance."""

        if isinstance(result, Future):  # unused atm
            result = result.result()
        if isinstance(result, Exception):
            raise Exception(
                'There was an error loading the database:\n%s' % result)

        self._db = result
        self.refresh()

    def tag_names(self):
        """Tags patches based on their names."""

        self.status(STATUS_NAME_TAG)
        self._db.tags_from_val_defs(TAGS_NAMES, 'patch_name')
        self.refresh()

    def tag_similar(self):
        """Tags patches based on their similarity to other patches."""

        self.status(STATUS_SIM_TAG)
        self._db.classify_tags()
        self.refresh()

    def create_model(self):
        """Creates a model for identifying patches based on similarity."""

        self.status(STATUS_WAIT)
        self._db.train_classifier()
        self.refresh()

    def status(self, msg):
        """Fully implement this function by updating a user-facing status indicator before calling the super."""

        if msg == STATUS_READY:
            self.unwait()
        else:
            self.empty_patches()
            self.wait()

    def new_database(self, dir):
        """Creates a new database with patches from `dir`."""

        self.status(STATUS_IMPORT)
        self.reload(PatchDatabase.bootstrap(Path(dir)))

    def open_database(self, path, silent=False):
        """Loads a previously saved database."""

        if not isinstance(path, Path):
            path = Path(path)

        if path.is_dir():
            try:
                self.reload(PatchDatabase.from_disk(path))
            except:
                if not silent:
                    raise Exception('That is not a valid data folder.')
                else:
                    self._db = PatchDatabase()
        else:
            self._db = PatchDatabase()

    def save_database(self, path):
        """Saves the active database to disk."""

        if self._db.is_active():
            self._db.to_disk(path)

    def load_config(self):
        """Loads the config file for the program, or create one if it doesn't exist."""

        DATA_DIR.mkdir(exist_ok=True)
        self._config.read_dict(DEFAULT_CONFIG)
        if CONFIG_FILE.is_file():
            self._config.read(CONFIG_FILE)
        else:
            CONFIG_FILE.touch()

        if self._config.get('synth_interface', 'quick_export_as') == PATCH_FILE:
            self.quick_tmp = Path(DATA_DIR / TMP_PFILE_NAME).resolve()
        else:
            self.quick_tmp = Path(DATA_DIR / TMP_FXP_NAME).resolve()
        self.quick_tmp.touch(exist_ok=True)

        if self._config.getboolean('database', 'auto_load'):
            self.open_database(DATA_DIR, silent=True)

    def export_patch(self, ind: int, typ=PATCH_FILE, path=None):
        """Exports the patch at index `ind`."""

        if ind:
            if path is None:
                path = Path(self._config.get(
                    'synth_interface', 'export_to'))

            self._db.write_patch(ind, typ, path)

    def quick_export(self, ind: int) -> str:
        """Asynchronously exports the patch at index `ind` using quick settings."""

        self._exe.submit(self._db.write_patch, ind, self._config.get('synth_interface',
                                                                     'quick_export_as'), self.quick_tmp)
        return str(self.quick_tmp)

    def by_index(self, ind: int):
        """Returns the patch at index `ind`."""

        return PatchMetadata.from_patch(self._db.get_patch_by_index(ind))

    def end(self):
        """Housekeeping before exiting the program."""

        if self._config.getboolean('database', 'auto_save'):
            self.save_database(DATA_DIR)

        with open(CONFIG_FILE, 'w') as cfile:
            self._config.write(cfile)
        self.quick_tmp.unlink(missing_ok=True)

        self._exe.shutdown()


__all__ = ['App', 'PatchMetadata', 'STATUS_MSGS']
