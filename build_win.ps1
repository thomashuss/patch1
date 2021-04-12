# Always build in a virtualenv!
& venv\Scripts\Activate.ps1
pyinstaller src\__main__.py `
    --noconfirm `
    --name Patch1 `
    --windowed `
    --noupx `
    --additional-hooks-dir=. `
    --hidden-import cmath `
    --hidden-import sklearn.neighbors._typedefs `
    --hidden-import sklearn.utils._weight_vector `
    --hidden-import tables `
    --exclude-module sklearn.cluster `
    --exclude-module scipy.fft