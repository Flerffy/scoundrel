import py_compile
import glob
import sys

files = glob.glob(r'c:\\Users\\Erik\\scoundrel\\**\\*.py', recursive=True)
ok = True
for f in sorted(files):
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        ok = False
        print("ERROR:", f)
        print(type(e).__name__ + ":", e)
        print()

if ok:
    print("All files compiled successfully")
    sys.exit(0)
else:
    print("Compilation failed")
    sys.exit(1)
