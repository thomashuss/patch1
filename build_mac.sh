#/bin/sh
# Always build in a virtualenv!
pyinstaller src/__main__.py \
    --noconfirm \
    --name Patch1 \
    --windowed \
    --upx-dir /usr/local/bin \
    --additional-hooks-dir=. \
    --hidden-import cmath \
    --hidden-import sklearn.neighbors._typedefs \
    --hidden-import sklearn.utils._weight_vector \
    --hidden-import tables \
    --exclude-module sklearn.cluster \
    --exclude-module scipy.fft