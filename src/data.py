import multiprocessing
import numpy as np
import pandas as pd
import re
from pathlib import Path
from os import cpu_count
from src.common import *
from src.patches import PatchSchema
from src.preset2fxp import *

_TAGS_SEP = '|'
FXP_CHUNK = 'chunk'
FXP_PARAMS = 'params'
DB_FILE = 'db'
DB_KEY = 'patches'
TAGS_KEY = 'tags'
PATCH_FILE = 'patch'
JOBS = min(4, cpu_count())


def volatile_db(func):
    """Wrapper for functions that modify the active database."""

    def inner(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        self.modified_db = True
        self.refresh()
        return ret

    return inner


class PatchDatabase:
    """Model for a pandas-based patch database conforming to a `PatchSchema`."""

    _df: pd.DataFrame = None
    _tags: pd.DataFrame
    _knn = None
    schema: PatchSchema

    modified_db = False
    modified_cls = False

    tags = []
    banks = []

    def __init__(self, schema: PatchSchema):
        """Constructs a new `PatchDatabase` instance following the `schema`."""

        self.schema = schema

    @volatile_db
    def bootstrap(self, root_dir: Path):
        """Creates a new database from the contents of the specified directory and loads the database."""

        re_file = re.compile(self.schema.file_pattern)
        files = filter(lambda f: re_file.match(f.name)
                       is not None, root_dir.glob('**/*'))

        meta = []
        params = []
        # Running *all* this I/O on a single thread is just so slow...
        with multiprocessing.Pool(processes=JOBS) as pool:
            for patch in pool.imap_unordered(self.schema.read_patchfile, files):
                if patch:
                    params.append(patch['params'])
                    del patch['params']
                    meta.append(patch)

        init_patch = pd.Series(
            self.schema.values, index=self.schema.params, dtype=self.schema.param_dtype)

        meta_df = pd.DataFrame(meta)
        param_df = pd.DataFrame(params, columns=self.schema.params,
                                dtype=int).fillna(init_patch)

        meta_df['bank'] = pd.Categorical(meta_df['bank'])
        meta_df['tags'] = ''

        for col, pos in self.schema.possibilites.items():
            meta_df[col] = pd.Categorical(meta_df[col], categories=pos)

        self._df = meta_df.join(param_df)

    def from_disk(self, path: Path):
        """Loads a database from the directory `path`."""

        if not isinstance(path, Path):
            path = Path(path)

        store = pd.HDFStore(str(path / DB_FILE), mode='r')
        self._df = store.get(DB_KEY)

        try:
            self._tags = store.get(TAGS_KEY)
        except KeyError:
            pass
        store.close()

        self.refresh()

    def to_disk(self, path: Path):
        """Saves the active database to the directory `path`."""

        if not isinstance(path, Path):
            path = Path(path)

        if self.modified_db:
            store = pd.HDFStore(str(path / DB_FILE), mode='w')
            store.put(DB_KEY, self._df, format='table')
            store.put(TAGS_KEY, self._tags)
            store.close()

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

    def train_classifier(self) -> float:
        """Constructs a k-nearest neighbors classifier for patches based on their parameters. The classifier is not
        intended to persist across sessions. Returns the accuracy of the classifier. """

        from sklearn.pipeline import Pipeline
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split

        tagged_mask = self._df['tags'] != ''
        df = self._df.loc[tagged_mask]
        if len(df) == 0:
            raise Exception('Add some tags and try again.')
        df_slice = df[self.schema.params]

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

        assert self._knn is not None, 'Please create a classifier model first.'
        predictions = self._knn.predict(
            self._df[self.schema.params].to_numpy())

        def classify(patch: pd.Series) -> str:
            prediction = predictions[int(patch.name)]
            tags = [self.tags[i] for i in np.asarray(prediction).nonzero()[0]]
            return encode_tags(tags, patch['tags'])

        self._df['tags'] = self._df.apply(classify, axis=1)

    def find_patches_by_val(self, find: str, col: str, exact=False, regex=False) -> pd.DataFrame:
        """Finds patches in the database matching `find` value in column `col`, either as a substring (`exact=False`),
        an exact match (`exact=True`), or a regular expression (`regex=True`). Returns a
        sliced `DataFrame`."""

        if exact:
            mask = self._df[col] == find
        else:
            mask = self._df[col].str.contains(find, case=False, regex=regex)

        return self._df.loc[mask]

    def find_patches_by_tags(self, tags: list) -> pd.DataFrame:
        """Finds patches in the database tagged with (at least) each specified tag. Returns a sliced `DataFrame`."""

        # create masks for each tag, unpack into list, take logical and,
        # reduce into single mask, return slice of dataframe with that mask
        return self._df.loc[np.logical_and.reduce([*(self._tags[tag] == 1 for tag in tags)])]

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
        """Writes the patch at `index` to a file of type `typ` (either `FXP_CHUNK`, `FXP_PARAMS`, or `PATCH_FILE`)
        into a file at `path`. """

        if not isinstance(path, Path):
            path = Path(path)

        patch = self.get_patch_by_index(index)

        if path.is_dir():
            # If given a dir rather than a file, auto name the file
            if typ == PATCH_FILE:
                fname = (self.schema.file_base, self.schema.file_ext)
            else:
                # regex sub to remove any unwanted characters from the file name.
                fname = (re.sub(r'\W+', '', patch['patch_name']), FXP_FILE_EXT)
            path /= ('%s.%s' % fname)

        if typ == PATCH_FILE:
            self.schema.write_patchfile(patch, path)
        else:
            kwargs = {'plugin_id': self.schema.vst_id, 'plugin_version': None,
                      'label': patch['patch_name'], 'num_params': self.schema.num_params}
            if typ == FXP_PARAMS:
                preset = Preset(params=self.schema.make_fxp_params(
                    patch[self.schema.params].to_numpy(dtype=int)), **kwargs)
            elif typ == FXP_CHUNK:
                preset = ChunkPreset(chunk=self.schema.make_fxp_chunk(
                    patch), **kwargs)
            else:
                raise ValueError(
                    'Cannot write a patch to a file type of %s' % typ)

            write_fxp(preset, str(path))

    @volatile_db
    def tags_from_val_defs(self, re_defs: dict, col: str):
        """Tags patches in the database, where the patch's `col` value matches a regular expression in `re_defs`,
        with the dictionary key of the matching expression. """

        for tag, pattern in re_defs.items():
            def apply(row):
                return encode_tags(tag, row['tags'])

            mask = self._df[col].str.contains(
                pattern, regex=True, flags=re.IGNORECASE)
            self._df.loc[mask, 'tags'] = self._df.loc[mask].apply(
                apply, axis=1)

    @volatile_db
    def change_tags(self, index: int, tags: list, replace: bool = True):
        """Changes the tags of the patch at `index` to `tags`. If `replace` is `False`, `tags` will be added to the
        patch's existing tags. """

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


def encode_tags(tags, old_tags: str = '') -> str:
    """Adds `tags` to `old_tags`, which is either a pre-defined properly formatted string of tags or a blank
    string, and returns a properly formatted (ragged) string of tags. Only duplicates across `tags` and `old_tags`
    will be corrected, and it is assumed that neither parameter has its own duplicates, though nothing particularly
    bad will happen if there are."""

    if isinstance(tags, str):
        tags = [tags]

    if len(old_tags) > 0:
        old_tagsl = old_tags.split(_TAGS_SEP)
        tags = list(filter(lambda tag: tag not in old_tagsl, tags))
        old_tags = old_tags + (_TAGS_SEP if len(tags) > 0 else '')

    return old_tags + _TAGS_SEP.join(tags)


__all__ = ['PatchDatabase', 'tags_to_list', 'tags_to_str',
           'FXP_CHUNK', 'FXP_PARAMS', 'PATCH_FILE']
