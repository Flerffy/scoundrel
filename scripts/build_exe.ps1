# Build script for Windows (PowerShell)
# Installs PyInstaller into the virtualenv and runs a one-dir build so asset paths
# remain on disk and the game can find them using normal Path(__file__) logic.

$python = "$PWD/.venv/Scripts/python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Python executable not found at $python. Activate your venv or adjust the path."
    exit 1
}

# Ensure pip and setuptools are up-to-date
& $python -m pip install --upgrade pip setuptools wheel
# Install PyInstaller
& $python -m pip install pyinstaller

# Build args
$entry = "scoundrel/scoundrel.py"
$name = "Scoundrel"
# Add data entries (format for Windows: source;dest)
$add1 = "scoundrel/assets;scoundrel/assets"
$add2 = "scoundrel/data;scoundrel/data"
$add3 = "data;data"

# Remove previous build/dist
try { Remove-Item -Recurse -Force build,dist -ErrorAction SilentlyContinue } catch { }

# Run pyinstaller (onedir so assets are kept alongside the package)
& $python -m PyInstaller --noconfirm --onedir --windowed --name $name --add-data $add1 --add-data $add2 --add-data $add3 $entry

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build completed. See dist/$name/"
} else {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
