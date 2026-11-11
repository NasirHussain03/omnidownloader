import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("Testing /api/health...")
    r = client.get("/api/health")
    print("Health response:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

    print("\nTesting GET / (Static Frontend)...")
    r = client.get("/")
    print("Root response:", r.status_code, "Length:", len(r.text))
    assert r.status_code == 200
    assert "OmniDownloader" in r.text

    print("\nTesting /api/search?q=lofi+chill&limit=3...")
    r = client.get("/api/search?q=lofi+chill&limit=3")
    print("Search status:", r.status_code)
    data = r.json()
    print("Found items count:", data.get("count"))
    assert r.status_code == 200
    assert data.get("success") is True
    assert len(data.get("results", [])) > 0
    first = data["results"][0]
    print(f"Sample result: [{first['id']}] {first['title']} ({first['duration_formatted']})")

    print("\nTesting /api/extract for YouTube URL...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    r = client.post("/api/extract", json={"url": test_url})
    print("Extract status:", r.status_code)
    data = r.json()
    assert r.status_code == 200
    assert data.get("success") is True
    print(f"Title: {data.get('title')}")
    print(f"Platform: {data.get('platform')}")
    print(f"Best direct URL present: {bool(data.get('best_direct_url'))}")
    print(f"Formats count: {len(data.get('formats', []))}")
    if data.get('formats'):
        print(f"First format: {data['formats'][0]['quality_label']} | {data['formats'][0]['ext']}")

    print("\nTesting /api/stats...")
    r = client.get("/api/stats")
    assert r.status_code == 200
    print("Stats response:", r.json())

    print("\nTesting Cache Speedup (2nd call for same search)...")
    import time
    t0 = time.perf_counter()
    r_cached = client.get("/api/search?q=lofi+chill&limit=3")
    cached_time = (time.perf_counter() - t0) * 1000
    assert r_cached.status_code == 200
    print(f"Cached search completed in: {cached_time:.2f} ms")

    print("\nTesting /api/redirect-download...")
    r = client.get("/api/redirect-download?url=https://example.com/video.mp4", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "https://example.com/video.mp4"
    print("Redirect-download 302 OK!")

    print("\nAll endpoint tests PASSED successfully!")

if __name__ == "__main__":
    test_endpoints()
