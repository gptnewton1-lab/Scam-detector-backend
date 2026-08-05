import urllib.request 
import urllib.error 
req=urllib.request.Request('http://127.0.0.1:8000/') 
resp=urllib.request.urlopen(req, timeout=5) 
print(resp.status) 
