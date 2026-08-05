import importlib.util
import pathlib
import uvicorn
import sys

port = 8001
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])
    except Exception:
        pass

main_path = pathlib.Path(__file__).parent / "main.py"
spec = importlib.util.spec_from_file_location("workspace_main", str(main_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if hasattr(module, 'app'):
    uvicorn.run(module.app, host="127.0.0.1", port=port)
else:
    print('No app found in main.py')
