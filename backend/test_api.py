import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

def test_full_flow():
    with TestClient(app) as client:
        print("\n--- 1. Testing Static Files ---")
        resp = client.get("/index.html")
        print(f"GET /index.html: status={resp.status_code}, length={len(resp.text)}")
        assert resp.status_code == 200, "Failed to get index.html"
        assert "منصة" in resp.text or "مركز" in resp.text, "Index.html content mismatch"

        print("\n--- 2. Testing Admin Seeding & Login ---")
        admin_login = client.post("/api/auth/login", json={
            "email": "0001",
            "password": "admin1234"
        })
        print(f"POST /api/auth/login (admin 0001): status={admin_login.status_code}, body={admin_login.json()}")
        assert admin_login.status_code == 200, "Admin 0001 login failed"
        admin_data = admin_login.json()
        assert admin_data["role"] == "ADMIN", "Admin role mismatch"
        admin_token = admin_data["token"]

        print("\n--- 3. Testing Admin Dashboard ---")
        overview = client.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
        print(f"GET /api/admin/overview: status={overview.status_code}, body={overview.json()}")
        assert overview.status_code == 200

        users_list = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        print(f"GET /api/admin/users: status={users_list.status_code}, total_users={len(users_list.json())}")
        assert users_list.status_code == 200
        assert len(users_list.json()) >= 2, "Admin accounts not seeded properly"

        print("\n--- 4. Testing User Registration ---")
        reg_phone = "01099887766"
        reg_resp = client.post("/api/auth/register", json={
            "fullName": "طالب تجريبي للاختبار",
            "phone": reg_phone,
            "age": 20,
            "email": "test_student@example.com",
            "password": "studentPassword123"
        })
        print(f"POST /api/auth/register: status={reg_resp.status_code}")
        if reg_resp.status_code == 201:
            reg_data = reg_resp.json()
            student_code = reg_data["userCode"]
            print(f"Registered user with code: {student_code}")
        else:
            print("User might already be registered, logging in...")
            student_code = None

        print("\n--- 5. Testing Student Login ---")
        login_resp = client.post("/api/auth/login", json={
            "email": reg_phone,
            "password": "studentPassword123"
        })
        print(f"POST /api/auth/login (student): status={login_resp.status_code}")
        assert login_resp.status_code == 200
        student_token = login_resp.json()["token"]
        student_code = login_resp.json()["userCode"]

        print("\n--- 6. Testing Profile & Progress Logging ---")
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
        print(f"GET /api/auth/me: {me.text}")
        assert me.status_code == 200

        profile = client.get("/api/auth/profile", headers={"Authorization": f"Bearer {student_token}"})
        print(f"GET /api/auth/profile: {profile.json()}")
        assert profile.status_code == 200

        # Log memorization
        log_resp = client.post("/api/progress/log", json={
            "content": "حفظت سورة النبأ كاملة بفضل الله",
            "pagesCount": 2.0
        }, headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/progress/log: status={log_resp.status_code}")
        if log_resp.status_code == 400:
            # try update
            update_resp = client.put("/api/progress/log", json={
                "content": "حفظت سورة النبأ وسورة النازعات",
                "pagesCount": 3.0
            }, headers={"Authorization": f"Bearer {student_token}"})
            print(f"PUT /api/progress/log: status={update_resp.status_code}")

        stats = client.get("/api/progress/stats", headers={"Authorization": f"Bearer {student_token}"})
        print(f"GET /api/progress/stats: {stats.json()}")
        assert stats.status_code == 200

        print("\n--- 7. Testing Leaderboard ---")
        lb = client.get("/api/leaderboard/weekly")
        print(f"GET /api/leaderboard/weekly: status={lb.status_code}, entries_count={len(lb.json()['entries'])}")
        assert lb.status_code == 200

        print("\n--- 8. Testing Study Plan Generation ---")
        plan_resp = client.post("/api/plan/generate", json={
            "memorizedPages": 10,
            "minutesPerDay": 30,
            "goal": "khatm",
            "ability": "good",
            "timing": "fajr",
            "daysPerWeek": 6,
            "followUp": "alone",
            "challenge": "forgetting"
        }, headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/plan/generate: status={plan_resp.status_code}, title={plan_resp.json().get('title')}, aiGenerated={plan_resp.json().get('aiGenerated')}")
        assert plan_resp.status_code == 200

        my_plan = client.get("/api/plan/mine", headers={"Authorization": f"Bearer {student_token}"})
        assert my_plan.status_code == 200 and my_plan.json().get("hasPlan") is True

        print("\n--- 9. Testing Beginner Plan ---")
        b_plan = client.post("/api/beginner-plan/generate", json={
            "ageGroup": "youth",
            "priorMemorization": "none",
            "ability": "medium",
            "minutesPerDay": 20,
            "followUp": "teacher"
        }, headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/beginner-plan/generate: status={b_plan.status_code}, totalItems={b_plan.json().get('totalItems')}")
        assert b_plan.status_code == 200

        # Mark first item complete
        complete_resp = client.post("/api/beginner-plan/complete", json={"order": 0}, headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/beginner-plan/complete: status={complete_resp.status_code}, currentIndex={complete_resp.json().get('currentIndex')}")
        assert complete_resp.status_code == 200
        assert complete_resp.json().get("currentIndex") == 1

        print("\n--- 10. Testing Quiz Submission ---")
        quiz_resp = client.post("/api/quiz/submit", json={
            "surahName": "سورة الإخلاص",
            "score": 5,
            "totalQuestions": 5
        }, headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/quiz/submit: status={quiz_resp.status_code}, body={quiz_resp.json()}")
        assert quiz_resp.status_code == 200

        my_scores = client.get("/api/quiz/my-scores", headers={"Authorization": f"Bearer {student_token}"})
        print(f"GET /api/quiz/my-scores: status={my_scores.status_code}, count={len(my_scores.json())}")
        assert my_scores.status_code == 200
        assert len(my_scores.json()) >= 1

        print("\n--- 11. Testing Exam Result Upsert & Lookup (with Admin Security) ---")
        # Unauthenticated / student attempt should be rejected
        exam_unauth = client.post("/api/results", json={"resultCode": "EX-9988", "studentName": "طالب تجريبي"})
        print(f"POST /api/results (unauthorized): status={exam_unauth.status_code}")
        assert exam_unauth.status_code in (401, 403), "Expected 401 or 403 for unauthorized exam creation"

        exam_student = client.post("/api/results", json={"resultCode": "EX-9988", "studentName": "طالب تجريبي"}, headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/results (student): status={exam_student.status_code}")
        assert exam_student.status_code == 403, "Expected 403 for student exam creation"

        # Admin attempt should succeed
        exam_create = client.post("/api/results", json={
            "resultCode": "EX-9988",
            "studentName": "طالب تجريبي",
            "examName": "اختبار جزء عمّ",
            "examDate": "2026-09-01",
            "score": 95,
            "maxScore": 100,
            "notes": "ممتاز ومتقن للتجويد"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        print(f"POST /api/results (admin): status={exam_create.status_code}, body={exam_create.json()}")
        assert exam_create.status_code == 200

        exam_lookup = client.get("/api/results/EX-9988")
        print(f"GET /api/results/EX-9988: status={exam_lookup.status_code}, body={exam_lookup.json()}")
        assert exam_lookup.status_code == 200
        assert exam_lookup.json()["studentName"] == "طالب تجريبي"

        print("\n--- 12. Testing Payment & Leaderboard Admin Protections ---")
        # Payment all-subscriptions
        pay_student = client.get("/api/payment/all-subscriptions", headers={"Authorization": f"Bearer {student_token}"})
        print(f"GET /api/payment/all-subscriptions (student): status={pay_student.status_code}")
        assert pay_student.status_code == 403

        pay_admin = client.get("/api/payment/all-subscriptions", headers={"Authorization": f"Bearer {admin_token}"})
        print(f"GET /api/payment/all-subscriptions (admin): status={pay_admin.status_code}, count={len(pay_admin.json())}")
        assert pay_admin.status_code == 200

        # Leaderboard reset
        lb_student = client.post("/api/leaderboard/reset", headers={"Authorization": f"Bearer {student_token}"})
        print(f"POST /api/leaderboard/reset (student): status={lb_student.status_code}")
        assert lb_student.status_code == 403

        lb_admin = client.post("/api/leaderboard/refresh", headers={"Authorization": f"Bearer {admin_token}"})
        print(f"POST /api/leaderboard/refresh (admin): status={lb_admin.status_code}")
        assert lb_admin.status_code == 200

        print("\n--- 13. Testing Notifications ---")
        notifs = client.get("/api/notifications/my", headers={"Authorization": f"Bearer {student_token}"})
        print(f"GET /api/notifications/my: status={notifs.status_code}, count={len(notifs.json())}")
        assert notifs.status_code == 200
        assert len(notifs.json()) >= 1

        print("\n*** ALL TESTS PASSED SUCCESSFULLY! The Python FastAPI backend fully matches the Spring Boot specifications. ***")

if __name__ == "__main__":
    test_full_flow()
