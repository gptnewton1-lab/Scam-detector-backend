import os
import main
print('cwd=', os.getcwd())
print('main file=', main.__file__)
print('routes=', [route.path for route in main.app.routes])
