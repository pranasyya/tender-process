import requests
import time
import os

BASE_URL = "http://127.0.0.1:8001"

def create_dummy_file():
    content = "Tender Ref: TEND-2026-001\nTitle: Construction of Highway\nPublication Date: 20-01-2026\nEMD: Rs. 50,000"
    with open("dummy_tender.txt", "w") as f:
        f.write(content)
    return "dummy_tender.txt"

def test_analyse():
    print("Testing /analyse...")
    fpath = create_dummy_file()
    with open(fpath, "rb") as f:
        files = {'files': (fpath, f, 'text/plain')}
        resp = requests.post(f"{BASE_URL}/analyse", files=files)
    print("Response:", resp.json())
    assert resp.status_code == 200

def test_progress():
    print("Testing /progress...")
    for _ in range(10):
        resp = requests.get(f"{BASE_URL}/progress")
        js = resp.json()
        print("Progress:", js)
        if js.get("status") == "done":
            break
        time.sleep(1)

def test_tenders():
    print("Testing /tenders...")
    resp = requests.get(f"{BASE_URL}/tenders")
    js = resp.json()
    print(f"Found {len(js)} tenders")
    if js:
        print("Sample:", js[0])

def test_chat():
    print("Testing /chat...")
    resp = requests.post(f"{BASE_URL}/chat", json={"query": "What is the EMD amount?"})
    print("Chat Resp:", resp.json())

if __name__ == "__main__":
    try:
        test_analyse()
        test_progress()
        test_tenders()
        test_chat()
    except Exception as e:
        print("Test failed:", e)
