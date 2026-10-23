import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.pipeline import UserQueryRequest, process_query

def test_queries():
    test_cases = [
        "what is peterson algorithm",
        "what is bakery algorithm",
        "what is deadlock and coffman conditions",
        "how does photosynthesis work"
    ]
    
    for q in test_cases:
        res = process_query(UserQueryRequest(query=q, mode="learn"))
        print(f"QUERY: '{q}'")
        print(f"  -> Topic: {res.topic}")
        print(f"  -> Subtopic/Algo: {res.algorithm}")
        print(f"  -> Source: {res.source_reference}")
        print(f"  -> Type: {res.query_type}")
        print("-" * 60)

if __name__ == "__main__":
    test_queries()
