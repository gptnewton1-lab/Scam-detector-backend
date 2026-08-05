import os
import pathlib
print('cwd:', os.getcwd())
print('cwd exists:', pathlib.Path(os.getcwd()).exists())
print('files:')
for p in pathlib.Path('.').rglob('main.py'):
    print('  ', p.resolve())
print('searching files for welcome text...')
for p in pathlib.Path('.').rglob('*.py'):
    try:
        text = p.read_text(errors='ignore')
    except Exception:
        continue
    if 'Welcome to the Scam Detector API' in text:
        print('found in', p.resolve())
print('done')
