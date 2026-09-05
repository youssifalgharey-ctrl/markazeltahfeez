import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User

def test_single_session_concurrency_block():
    with TestClient(app) as client:
        print("\n=== Test 1: Device 1 logs in successfully ===")
        login1 = client.post("/api/auth/login", json={
            "email": "0001",
            "password": "admin1234"
        })
        assert login1.status_code == 200, f"Device 1 login failed: {login1.text}"
        data1 = login1.json()
        token1 = data1["token"]
        assert token1, "Token 1 missing"
        print("Device 1 logged in successfully. Token received.")

        print("\n=== Test 2: Device 2 attempts to log in with same account -> MUST BE BLOCKED ===")
        login2 = client.post("/api/auth/login", json={
            "email": "0001",
            "password": "admin1234"
        })
        print(f"Device 2 login attempt status: {login2.status_code}, response: {login2.json()}")
        assert login2.status_code == 400, "Device 2 was NOT blocked!"
        assert "مفتوح حالياً على جهاز آخر" in login2.json().get("detail", ""), "Expected blocking message not received"
        print("Device 2 was blocked successfully with expected message!")

        print("\n=== Test 3: Device 1 sends heartbeat to keep session active ===")
        hb = client.post("/api/auth/heartbeat", headers={"Authorization": f"Bearer {token1}"})
        assert hb.status_code == 200, "Heartbeat failed"
        assert hb.json().get("status") == "alive"
        print("Device 1 heartbeat successful.")

        print("\n=== Test 4: Device 1 logs out ===")
        logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token1}"})
        assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.text}"
        print(f"Device 1 logged out: {logout_resp.json()}")

        print("\n=== Test 5: Device 2 now attempts to log in -> MUST SUCCEED ===")
        login2_again = client.post("/api/auth/login", json={
            "email": "0001",
            "password": "admin1234"
        })
        assert login2_again.status_code == 200, f"Device 2 login after logout failed: {login2_again.text}"
        token2 = login2_again.json()["token"]
        assert token2, "Token 2 missing"
        print("Device 2 logged in successfully after Device 1 logged out!")

        print("\n=== Test 6: Old Device 1 token is invalid ===")
        profile_old = client.get("/api/auth/profile", headers={"Authorization": f"Bearer {token1}"})
        assert profile_old.status_code == 401, "Old Device 1 token should be rejected!"
        print("Old Device 1 token properly rejected with 401.")

        print("\n=== Test 7: Inactivity timeout simulation ===")
        db = SessionLocal()
        user = db.query(User).filter(User.userCode == "0001").first()
        user.last_active_at = datetime.now() - timedelta(seconds=150)
        db.commit()
        db.close()

        login3 = client.post("/api/auth/login", json={
            "email": "0001",
            "password": "admin1234"
        })
        assert login3.status_code == 200, f"Login after inactivity timeout failed: {login3.text}"
        print("Login after inactivity timeout succeeded as expected!")

        # Clean up logout
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {login3.json()['token']}"})

        print("\n*** ALL SINGLE-SESSION CONCURRENCY TESTS PASSED! ***")

if __name__ == "__main__":
    test_single_session_concurrency_block()
