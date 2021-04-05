import configparser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from .data import *
from .sorting import TAGS_NAMES
from .common import *

CONFIG_FILE = DATA_DIR / 'config.ini'
DEFAULT_CONFIG = {
    'database': {
        'file': DATA_DIR / ('db.%s' % DB_FILE_EXT),
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


class App:
    """Implements the program's controller."""

    _db: PatchDatabase  # The active patch database
    _config: configparser.ConfigParser
    _exe: ThreadPoolExecutor  # When a task needs to run in the background
    quick_tmp: Path  # Temporary file for quick export

    tags = []  # tag indexes for active database
    banks = []  # bank indexes for active database

    def __init__(self):
        self._exe = ThreadPoolExecutor(max_workers=1)
        self._config = configparser.ConfigParser()

        self.load_config()

    def put_patch(self, patch):
        """Define this function in an implementation of `App`. It should
        add the `patch` to a list of patches visible to the user."""

        pass

    def keyword_search(self, kwd: str):
        """Searches for patches matching keyword `kwd` and calls `put_patch` on them."""

        self._db.keyword_search(kwd).apply(self.put_patch, axis=1)

    def search_by_bank(self, bank: str):
        """Searches for patches in bank `bank` and calls `put_patch` on them."""

        self._db.find_patches_by_val(
            bank, 'bank', exact=True).apply(self.put_patch, axis=1)

    def search_by_tags(self, tags: list):
        """Searches for patches matching `tags` and calls `put_patch` on them."""

        self._db.find_patches_by_tags(tags).apply(self.put_patch, axis=1)

    def refresh(self):
        """Refreshes cached indexes."""

        self.tags = self._db.tags
        self.banks = self._db.banks

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

        self._db.tags_from_val_defs(TAGS_NAMES, 'patch_name')
        self.refresh()

    def new_database(self, dir):
        """Creates a new database with patches from `dir`."""

        self.reload(PatchDatabase.bootstrap(Path(dir)))

    def open_database(self, path, silent=False):
        """Loads a previously saved database."""

        if not isinstance(path, Path):
            path = Path(path)

        if path.is_file():
            self._config.set('database', 'file', str(path))
            self.reload(PatchDatabase.from_file(path))
        elif not silent:
            raise Exception('That is not a valid database file.')
        else:
            self._db = PatchDatabase()

    def save_database(self, path):
        """Saves the active database to disk."""

        if self._db.is_active():
            self._db.to_file(path)

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
            self.open_database(self._config.get(
                'database', 'file'), silent=True)

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

    def end(self):
        """Housekeeping before exiting the program."""

        if self._config.getboolean('database', 'auto_save'):
            self.save_database(self._config.get('database', 'file'))

        with open(CONFIG_FILE, 'w') as cfile:
            self._config.write(cfile)
        self.quick_tmp.unlink(missing_ok=True)

        self._exe.shutdown()
