import json
from urllib.request import Request, urlopen

url = 'http://127.0.0.1:8002/analyze'

#turns object into json string and encodes it to bytes
data = json.dumps({'text': 'Urgent! Send money now to claim your bonus.'}).encode('utf-8')

#creates a request object with url,data and headers, then sends the request to the server and gets the response 
req = Request(url, data=data, headers={'Content-Type': 'application/json'})

#sends request to the server and gets response
res = urlopen(req)

#sends request to the server aand gets response 
print(res.status)
print(res.read().decode())
