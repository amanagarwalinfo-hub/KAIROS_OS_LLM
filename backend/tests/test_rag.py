import urllib.request
import json

def test_question(q):
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/chat",
        data=json.dumps({"query": q, "mode": "learn"}).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"QUERY: {q}")
        print(f"TYPE: {data['query_type']}")
        print(f"TOPIC: {data['topic']}")
        print(f"SOURCE: {data.get('source_reference')}")
        print("-" * 50)

if __name__ == "__main__":
    test_question("What is a zombie process in Linux?")
    test_question("Explain deadlock and Coffman conditions")
    test_question("How does photosynthesis work in biology?")
