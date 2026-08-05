import urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8002/', timeout=5) as r:
        print('status=', r.status)
        print(r.read(800).decode('utf-8', errors='ignore'))
except Exception as e:
    print('error', type(e).__name__, e)
