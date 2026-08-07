import urllib.request
out = []
for path in ("/openapi.json", "/health"):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=5) as r:
            out.append(f"{path} -> {r.status}")
    except Exception as e:
        out.append(f"{path} -> {type(e).__name__}: {e}")
with open("swagger_check.txt", "w") as f:
    f.write("\n".join(out))
