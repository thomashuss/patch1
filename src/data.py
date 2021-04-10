import multiprocessing
import pandas as pd
import numpy as np
import re
import pickle
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from os import cpu_count
from patchfiles import write_patchfile, read_patchfile
from common import *
from sy2fxpreset import *
from preset2fxp import *

_TAGS_SEP = '|'
FXP_CHUNK = 'chunk'
FXP_PARAMS = 'params'
DB_FILE = 'db'
DB_KEY = 'patches'
TAGS_KEY = 'TAGS'
CLS_FILE = 'cls'
PATCH_FILE = PATCH_FILE_EXT
JOBS = min(4, cpu_count())

# Create a series with all default values for filling in sparsely defined patches.
INIT_PATCH = pd.Series(PARAM_VALS, index=PARAM_NAMES, dtype=int)

# Columns of a dataframe containing patch metadeta.
META_DF_COLS = ['bank', 'num', 'patch_name', 'color', 'ver', 'tags']

class PatchDatabase:
    """Model for a pandas-based patch database."""

    _df: pd.DataFrame = None
    _tags: pd.DataFrame
    _knn: Pipeline = None

    modified_db = False
    modified_cls = False

    tags = []
    banks = []

    def __init__(self, df: pd.DataFrame = None, tags: pd.DataFrame = None, classifier: Pipeline = None, new = False):
        """Don't call this function directly."""

        if df is not None:
            self._df = df
            self.modified_db = new

            if tags is not None:
                self.refresh(_tags_df=tags)
            else:
                self.refresh()

            if classifier is not None:
                self._knn = classifier

    @classmethod
    def bootstrap(cls, root_dir: Path):
        """Creates a new database from the contents of the specified directory and returns a new `PatchDatabase`
        with the database loaded."""

        try:
            meta = []
            params = []

            # Syntax of a patch file name.
            re_file = re.compile(r'^[0-9]{3}\.%s$' % PATCH_FILE_EXT)

            # Regex is used on the file names, as opposed to globbing for file ext, to weed out
            # any hidden files or other garbage (*cough* macOS).
            files = filter(lambda f: re_file.match(f.name)
                           != None, root_dir.glob('**/*'))

            # Running *all* this I/O on a single thread is just so slow...
            with multiprocessing.Pool(processes=JOBS) as pool:
                # Don't care about the order yet, they'll be sorted later.
                for patch in pool.imap_unordered(read_patchfile, files):
                    meta.append(patch[0])
                    params.append(patch[1])

            meta_df = pd.DataFrame(meta, columns=META_DF_COLS[:-1])  # no tags
            param_df = pd.DataFrame(params, columns=PARAM_NAMES,
                                    dtype=int).fillna(INIT_PATCH)

            meta_df['bank'] = pd.Categorical(meta_df['bank'])
            meta_df['num'] = pd.Categorical(
                meta_df['num'], categories=PATCH_NUMS)
            meta_df.sort_values('patch_name')
            meta_df['color'] = pd.Categorical(
                meta_df['color'], categories=COLORS)
            meta_df['ver'] = pd.Categorical(meta_df['ver'])
            meta_df['tags'] = ''

            return cls(df=meta_df.join(param_df), new=True)
        except Exception as e:
            return e

    @classmethod
    def from_disk(cls, path: Path):
        """Creates a new `PatchDatabase` instance after loading a database from the directory `path`."""

        if not isinstance(path, Path):
            path = Path(path)
        
        store = pd.HDFStore(path / DB_FILE, mode='r')
        df = store.get(DB_KEY)

        try:
            tags = store.get(TAGS_KEY)
        except KeyError:
            tags = None
        store.close()

        knn = None
        if (path / CLS_FILE).is_file():
            with open(path / CLS_FILE, 'rb') as f:
                knn = pickle.load(f)
        return cls(df=df, tags=tags, classifier=knn)

    def to_disk(self, path: Path):
        """Saves the active database to the directory `path`."""

        if not isinstance(path, Path):
            path = Path(path)

        if self.modified_db:
            store = pd.HDFStore(path / DB_FILE, mode='w')
            store.put(DB_KEY, self._df, format='table')
            store.put(TAGS_KEY, self._tags)
            store.close()
        if self._knn is not None and self.modified_cls:
            with open(path / CLS_FILE, 'wb') as f:
                pickle.dump(self._knn, f)

    def is_active(self) -> bool:
        """Returns `True` if a database is loaded, `False` otherwise."""

        return self._df is not None

    def refresh(self, _tags_df: pd.DataFrame = None):
        """Rebuilds cached indexes for the active database."""

        if _tags_df is None:
            self._tags = self._df['tags'].str.get_dummies(_TAGS_SEP)
            self.tags = self._tags.columns.to_list()
        else:
            self._tags = _tags_df
            self.tags = self._tags.columns.to_list()
        self.banks = self.get_categories('bank')

    def volatile_db(func):
        """Wrapper for functions that modify the active database."""

        def inner(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self.modified_db = True
            self.refresh()
            return ret
        return inner

    def volatile_cls(func):
        """Wrapper for functions that modify the k-nearest neighbors classifier."""

        def inner(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            self.modified_cls = True
            return ret
        return inner

    @volatile_cls
    def train_classifier(self) -> float:
        """Constructs a k-nearest neighbors classifier for patches based on their parameters.
        Returns the accuracy of the classifier."""

        tagged_mask = self._df['tags'] != ''
        df = self._df.loc[tagged_mask]
        if len(df) == 0:
            raise Exception('Add some tags and try again.')
        df_slice = df[PARAM_NAMES]

        indicators = self._tags[tagged_mask]
        X = df_slice.to_numpy()
        y = indicators.to_numpy()

        X_train, X_test, y_train, y_test = train_test_split(X, y)
        self._knn = Pipeline([('scaler', StandardScaler()), ('knn', KNeighborsClassifier(
            n_jobs=JOBS, p=1, weights='distance'))])
        self._knn.fit(X_train, y_train)
        return float(self._knn.score(X_test, y_test))

    @volatile_db
    def classify_tags(self):
        """Tags patches based on their parameters using the previously generated classifier model."""

        assert isinstance(self._knn, Pipeline), 'Please create a classifier model first.'
        predictions = self._knn.predict(self._df[PARAM_NAMES].to_numpy())

        def classify(patch: pd.Series) -> str:
            prediction = predictions[int(patch.name)]
            tags = [self.tags[i] for i in np.asarray(prediction).nonzero()[0]]
            return encode_tags(tags, patch['tags'])

        self._df['tags'] = self._df.apply(classify, axis=1)

    def find_patches_by_val(self, find: str, col: str, exact=False, regex=False) -> pd.DataFrame:
        """Finds metadata of patches in the database matching `find` value in column `col`, either as a substring (`exact=False`),
        an exact match (`exact=True`), or a regular expression (`regex=True`). Returns a
        sliced `DataFrame`."""

        if exact:
            mask = self._df[col] == find
        else:
            mask = self._df[col].str.contains(find, case=False, regex=regex)

        return self._df.loc[mask][META_DF_COLS]

    def find_patches_by_tags(self, tags: list) -> pd.DataFrame:
        """Finds metadata of patches in the database tagged with (at least) each specified tag. Returns a sliced `DataFrame`."""

        # create masks for each tag, unpack into list, take logical and,
        # reduce into single mask, return slice of dataframe with that mask
        return self._df.loc[np.logical_and.reduce([*(self._tags[tag] == 1 for tag in tags)])][META_DF_COLS]

    def keyword_search(self, kwd: str) -> pd.DataFrame:
        """Finds metadata of patches in the database whose name matches the specified keyword query. Returns a
        sliced `DataFrame`."""

        return self.find_patches_by_val(kwd, 'patch_name')

    def get_categories(self, col: str) -> list:
        """Returns all possible values within a column of categorical data."""

        assert isinstance(self._df[col].dtype, pd.CategoricalDtype)
        return self._df[col].cat.categories.to_list()

    def get_patch_by_index(self, index: int) -> pd.Series:
        """Returns the full patch (meta + params) at the specified index in the database."""

        return self._df.iloc[index]

    def write_patch(self, index, typ, path):
        """Writes the patch at `index` to a file of type `typ` (either `FXP_CHUNK`, `FXP_PARAMS`, or `PATCH_FILE`) into a file at `path`."""

        if not isinstance(path, Path):
            path = Path(path)

        patch = self.get_patch_by_index(index)

        if path.is_dir():
            # If given a dir rather than a file, auto name the file
            if typ == PATCH_FILE:
                fname = (patch['num'], PATCH_FILE_EXT)
            else:
                fname = (re.sub(r'\W+', '', patch['patch_name']), FXP_FILE_EXT)
            path /= ('%s.%s' % fname)

        if typ == PATCH_FILE:
            write_patchfile(patch, path)
        else:
            params = patch[PARAM_NAMES].to_numpy(dtype=int)
            kwargs = {'plugin_id': VST_ID, 'plugin_version': None,
                      'label': patch['patch_name'], 'num_params': NUM_PARAMS}
            if typ == FXP_PARAMS:
                preset = Preset(params=make_fxp_params(params), **kwargs)
            elif typ == FXP_CHUNK:
                preset = ChunkPreset(chunk=make_fxp_chunk(
                    params, int(patch['ver'])), **kwargs)
            else:
                raise ValueError(
                    'Cannot write a patch to a file type of %s' % typ)

            write_fxp(preset, path)

    @volatile_db
    def tags_from_val_defs(self, re_defs: dict, col: str):
        """Tags patches in the database, where the patch's `col` value matches a regular expression in `re_defs`, with the dictionary key
        of the matching expression."""

        if self.is_active():
            defs = {val: re.compile(re_str, flags=re.IGNORECASE)
                    for val, re_str in re_defs.items()}

            def apply(row):
                return encode_tags(list(val for val, pattern in defs.items()
                                        if pattern.search(row[col])), row['tags'])
            self._df['tags'] = self._df.apply(apply, axis=1)

    @volatile_db
    def change_tags(self, index: int, tags: list, replace: bool=True):
        """Changes the tags of the patch at `index` to `tags`. If `replace` is `False`, `tags` will be added to the patch's existing tags."""

        if replace:
            old_tags = ''
        else:
            old_tags = self._df.iloc[index]['tags']
        self._df.iloc[index]['tags'] = encode_tags(tags, old_tags)

def tags_to_list(tags: str) -> list:
    """Returns the properly formatted (ragged) string of tags as a list."""

    return _TAGS_SEP.split(tags)


def tags_to_str(tags: str, sep: str = ', ') -> str:
    """Returns the properly formatted (ragged) string of tags as a string with the specified delimeter."""

    return tags.replace(_TAGS_SEP, sep)


def encode_tags(tags: list, old_tags: str = '') -> str:
    """Adds `tags` to `old_tags`, which is either a pre-defined properly formatted string of tags or a blank
    string, and returns a properly formatted (ragged) string of tags. Only duplicates across `tags` and `old_tags`
    will be corrected, and it is assumed that neither parameter has its own duplicates, though nothing particularly
    bad will happen if there are."""

    if len(old_tags) > 0:
        old_tagsl = old_tags.split(_TAGS_SEP)
        tags = list(filter(lambda tag: not tag in old_tagsl, tags))
        old_tags = old_tags + (_TAGS_SEP if len(tags) > 0 else '')

    return old_tags + _TAGS_SEP.join(tags)


__all__ = ['PatchDatabase', 'tags_to_list', 'tags_to_str',
           'FXP_CHUNK', 'FXP_PARAMS', 'PATCH_FILE']
