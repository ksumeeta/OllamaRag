import requests
import os

url = "http://localhost:8000/api/upload/"
files = {'file': ('test_upload.txt', open('test_upload.txt', 'rb'), 'text/plain')}
data = {'overwrite': 'true'}

try:
    response = requests.post(url, files=files, data=data)
    print(response.status_code)
    print(response.text)
except Exception as e:
    print(e)
