import httpx

def test_live():
    base_url = "http://localhost:8081"

    print("1. GET /index.html")
    r = httpx.get(f"{base_url}/index.html")
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    assert r.status_code == 200

    print("\n2. POST /api/auth/login (Admin 0001)")
    r = httpx.post(f"{base_url}/api/auth/login", json={"email": "0001", "password": "admin1234"})
    print(f"Status: {r.status_code}, Body: {r.json()}")
    assert r.status_code == 200
    token = r.json()["token"]

    print("\n3. GET /api/admin/overview")
    headers = {"Authorization": f"Bearer {token}"}
    r = httpx.get(f"{base_url}/api/admin/overview", headers=headers)
    print(f"Status: {r.status_code}, Body: {r.json()}")
    assert r.status_code == 200

    print("\n4. GET /api/leaderboard/weekly")
    r = httpx.get(f"{base_url}/api/leaderboard/weekly")
    print(f"Status: {r.status_code}, Total users: {r.json()['totalUsers']}")
    assert r.status_code == 200

    print("\n5. GET /api/ijaza/sheikhs")
    r = httpx.get(f"{base_url}/api/ijaza/sheikhs")
    print(f"Status: {r.status_code}, Sheikhs: {r.json()}")
    assert r.status_code == 200

    print("\nALL LIVE ENDPOINTS ARE FULLY OPERATIONAL ON PORT 8081!")

if __name__ == "__main__":
    test_live()
