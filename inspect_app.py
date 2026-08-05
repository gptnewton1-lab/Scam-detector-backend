import importlib.util, pathlib, inspect
main_path = pathlib.Path('main.py').resolve()
spec = importlib.util.spec_from_file_location('workspace_main', str(main_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = getattr(mod, 'app', None)
print('main file:', main_path)
if app is None:
    print('no app')
else:
    paths = {route.path:route for route in app.routes}
    print('registered paths:')
    for p in sorted(paths.keys()):
        print(' ', p)
    if '/' in paths:
        r = paths['/']
        print('\nRoute methods:', r.methods)
        endpoint = r.endpoint
        print('Endpoint repr:', endpoint)
        try:
            src = inspect.getsource(endpoint)
            print('\nEndpoint source:\n', src)
        except Exception as e:
            print('Could not get source:', e)
