import numpy as np
import pandas as pd
import re
from pathlib import Path
from os import cpu_count
from tables.exceptions import HDF5ExtError
from src.patches import PatchSchema
from src.preset2fxp import *

FXP_CHUNK = 'chunk'
FXP_PARAMS = 'params'
DB_KEY = 'patches'
TAGS_KEY = 'tags'
PATCH_FILE = 'patch'
JOBS = min(4, cpu_count())


def updates(func):
    """Wrapper for functions that require an update of the database."""

    def inner(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        self.refresh()
        return ret

    return inner


class PatchDatabase:
    """Model for a pandas-based patch database conforming to a `PatchSchema`."""

    __df: pd.DataFrame = None
    __tags: pd.DataFrame
    __knn = None
    schema: PatchSchema

    tags: pd.Index = pd.Index([])
    banks = []

    def __init__(self, schema: PatchSchema):
        """Constructs a new `PatchDatabase` instance following the `schema`."""

        self.schema = schema

    def bootstrap(self, root_dir: Path):
        """Creates a new database from the contents of the specified directory and loads the database."""

        re_file = re.compile(self.schema.file_pattern)
        files = filter(lambda f: re_file.match(f.name) is not None, root_dir.glob('**/*'))

        meta = []
        params = []
        for patch in map(self.schema.read_patchfile, files):
            if patch:
                params.append(patch['params'])
                del patch['params']
                meta.append(patch)

        init_patch = pd.Series(
            self.schema.values, index=self.schema.params, dtype=self.schema.param_dtype)

        meta_df = pd.DataFrame(meta)
        param_df = pd.DataFrame(params,
                                columns=self.schema.params).fillna(init_patch).astype(int)

        meta_df['bank'] = pd.Categorical(meta_df['bank'])
        meta_df['tags'] = ''

        for col, pos in self.schema.possibilites.items():
            meta_df[col] = pd.Categorical(meta_df[col], categories=pos)

        self.__df = meta_df.join(param_df)
        self.__tags = pd.DataFrame(index=self.__df.index, dtype='bool')
        self.refresh()

    # noinspection PyTypeChecker
    def from_disk(self, file):
        """Loads a database from the `file`."""

        try:
            store = pd.HDFStore(file, mode='r')
        except (HDF5ExtError, OSError):
            raise FileNotFoundError

        self.__df = store.get(DB_KEY)
        self.__tags = store.get(TAGS_KEY)
        store.close()

        self.refresh()

    def to_disk(self, file):
        """Saves the active database to the `file`."""

        store = pd.HDFStore(str(file), mode='w')
        store.put(DB_KEY, self.__df, format='table')
        store.put(TAGS_KEY, self.__tags)
        store.close()

    def is_active(self) -> bool:
        """Returns `True` if a database is loaded, `False` otherwise."""

        return self.__df is not None

    def refresh(self):
        """Rebuilds cached indexes for, and cleans up, the active database."""

        self.__clean_tags()

        self.tags = self.__tags.columns
        self.banks = self.get_categories('bank')

    def __return_df(self, mask):
        """Returns a `DataFrame` composed of metadata from the patches in the database represented by the Boolean mask
        `mask`."""

        return self.__df.loc[mask][self.schema.meta_cols]

    def find_patches_by_val(self, find: str, col: str, exact=False, regex=False) -> pd.DataFrame:
        """Finds patches in the database matching `find` value in column `col`, either as a substring (`exact=False`),
        an exact match (`exact=True`), or a regular expression (`regex=True`)."""

        if exact:
            mask = self.__df[col] == find
        else:
            mask = self.__df[col].str.contains(find, case=False, regex=regex)

        return self.__return_df(mask)

    def keyword_search(self, kwd: str) -> pd.DataFrame:
        """Finds metadata of patches in the database whose name matches the specified keyword query."""

        return self.find_patches_by_val(kwd, 'patch_name')

    def find_patches_by_tags(self, tags: list) -> pd.DataFrame:
        """Finds patches in the database tagged with (at least) each tag in `tags`."""

        try:
            # create masks for each tag, unpack into list, take logical and,
            # reduce into single mask, return slice of dataframe with that mask
            return self.__return_df(np.logical_and.reduce([*(self.__tags[tag] == True for tag in tags)]))
        except KeyError:
            ...

    def get_tags(self, ind: int) -> list:
        """Returns the tags of the patch at index `ind`."""

        return self.tags[self.__tags.iloc[ind]].to_list()

    def get_categories(self, col: str) -> list:
        """Returns all possible values within a column of categorical data."""

        assert isinstance(self.__df[col].dtype, pd.CategoricalDtype)
        return self.__df[col].cat.categories.to_list()

    def train_classifier(self):
        """Constructs a k-nearest neighbors classifier for patches based on their parameters. The classifier is not
        intended to persist across sessions."""

        from sklearn.pipeline import Pipeline
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.preprocessing import StandardScaler

        df = self.__df.drop_duplicates(self.schema.params)
        tags = self.__tags.loc[df.index].fillna(False)
        tagged_mask = tags.any(axis=1)
        if len(tagged_mask) == 0:
            raise Exception('Add some tags and try again.')
        df = df.loc[tagged_mask]
        tags = tags.loc[tagged_mask]

        X = df[self.schema.params].to_numpy()
        y = tags.to_numpy(dtype='bool')

        self.__knn = Pipeline([('scaler', StandardScaler()), ('knn', KNeighborsClassifier(
            n_jobs=JOBS, p=1, weights='distance'))])
        self.__knn.fit(X, y)

    def classify_tags(self):
        """Tags patches based on their parameters using the previously generated classifier model."""

        assert self.__knn is not None, 'Please create a classifier model first.'

        self.__tags |= self.__knn.predict(
            self.__df[self.schema.params].to_numpy())
        self.__update_tags()

        del self.__knn

    def tags_from_val_defs(self, re_defs: dict, col: str):
        """Tags patches in the database, where the patch's `col` value matches a regular expression in `re_defs`,
        with the dictionary key of the matching expression."""

        for tag, pattern in re_defs.items():
            mask = self.__df[col].str.contains(
                pattern, regex=True, flags=re.IGNORECASE)

            self.__tags.loc[mask, tag] = True

        self.__update_tags()

    def change_tags(self, index: int, tags: list, replace: bool = True):
        """Changes the tags of the patch at `index` to `tags`. If `replace` is `False`, `tags` will be added to the
        patch's existing tags."""

        if replace:
            self.__tags.loc[index, :] = False

        self.__tags.loc[index, tags] = True
        self.__update_tags(index)

    @updates
    def remove_duplicates(self):
        """Removes duplicate patches from the database."""

        self.__df = self.__df.drop_duplicates(self.schema.params)

    def __clean_tags(self):
        """Internal use only. Re-fits the tag DataFrame to the patch DataFrame, removes unused tags, sorts columns,
        and fills empty values."""

        df_l = len(self.__df)
        tags_l = len(self.__tags)

        # Re-fit tags df if a patch was removed...
        if df_l < tags_l:
            self.__tags = self.__tags.loc[self.__df.index]
        # ...or added
        elif df_l > tags_l:
            self.__tags.append(pd.DataFrame(columns=self.__tags.columns,
                                            index=range(0, df_l - tags_l))
                               .fillna(False), ignore_index=True)

        # Remove unused tags and sort columns
        self.__tags = self.__tags[sorted(self.__tags.columns[self.__tags.any()], key=lambda s: s.lower())]

    def __update_tags(self, index=None):
        """Internal use only. Updates the stringified tags for the patch at `index` or the entire database, and
        cleans up the tag database."""

        sep = ', '

        self.__tags = self.__tags.fillna(False)
        self.refresh()
        if index is not None:
            patch = self.__tags.iloc[index]
            self.__df.loc[index, 'tags'] = sep.join(self.tags[patch])
        else:
            self.__df['tags'] = self.__tags.apply(lambda row: sep.join(self.tags[row]), axis=1)

    def write_patch(self, index, typ, path: Path):
        """Writes the patch at `index` into a file of type `typ` (either `FXP_CHUNK`, `FXP_PARAMS`, or `PATCH_FILE`)
        at `path`."""

        patch = self.__df.iloc[index]

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


__all__ = ['PatchDatabase', 'FXP_CHUNK', 'FXP_PARAMS', 'PATCH_FILE']
