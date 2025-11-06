import sys
sys.path.insert(0, r'C:\Users\Erik\scoundrel')
sys.path.insert(0, r'C:\Users\Erik\scoundrel\scoundrel')
try:
    import scoundrel.engine as eng
    print('scoundrel.engine imported OK')
except Exception as e:
    print('import failed:', e)
    raise
