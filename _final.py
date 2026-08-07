import urllib.request
out = []
for path in ("/health", "/", "/openapi.json"):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=5) as r:
            out.append(f"{path} -> {r.status} {r.read().decode()[:120]}")
    except Exception as e:
        out.append(f"{path} -> FAIL {type(e).__name__}: {e}")
with open("final_check.txt", "w") as f:
    f.write("\n".join(out))