import httpx
import time

API_URL = "http://localhost:8000/api/upload/"
FILE_PATH = "test_ingestion.txt"

def test_upload():
    print(f"Uploading {FILE_PATH} to {API_URL}...")
    try:
        with open(FILE_PATH, "rb") as f:
            files = {"file": ("test_ingestion.txt", f, "text/plain")}
            with httpx.Client() as client:
                response = client.post(API_URL, files=files)
        
        if response.status_code == 200:
            print("Upload successful!")
            print("Response:", response.json())
            return response.json()
        else:
            print(f"Upload failed with status {response.status_code}")
            print("Response:", response.text)
            return None
    except Exception as e:
        print(f"Error during upload: {e}")
        return None

if __name__ == "__main__":
    # Wait a bit for backend to start up if just launched
    # time.sleep(5) 
    result = test_upload()
    if result:
        print(f"\nUploaded File ID: {result.get('id')}")
