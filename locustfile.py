"""
Locust 부하 테스트 - parkingfee
실행: locust -f locustfile.py --host=http://localhost:5000
브라우저: http://localhost:8089
"""

from locust import HttpUser, task, between
import random

# CSV에서 추출한 실제 차량번호 끝 4자리
CAR_TAILS = [
    "5588", "3987", "6355", "1020", "5940",
    "0704", "1964", "4958", "7161", "9419",
    "4340", "2472", "6678", "0300", "6192",
    "4952", "0910", "5216", "6320", "8991",
]

# 존재하지 않는 번호 (404 응답 시나리오)
INVALID_TAILS = ["0000", "9999", "1111"]


class ParkingUser(HttpUser):
    # 각 작업 사이 대기 시간 (실제 사용자처럼)
    wait_time = between(1, 3)

    @task(5)
    def search_and_view(self):
        """정상 차량 검색 → 결과 조회 (가장 빈번한 시나리오)"""
        tail = random.choice(CAR_TAILS)

        with self.client.post(
            "/search",
            json={"carNumber": tail},
            catch_response=True,
            name="/search [hit]",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                redirect_url = data.get("redirect", "")
                if redirect_url:
                    self.client.get(redirect_url, name="/result or /select")
                resp.success()
            else:
                resp.failure(f"search failed: {resp.status_code}")

    @task(2)
    def view_index(self):
        """메인 페이지 접속"""
        self.client.get("/", name="/index")

    @task(1)
    def search_invalid(self):
        """존재하지 않는 차량 검색 (404 응답)"""
        tail = random.choice(INVALID_TAILS)
        with self.client.post(
            "/search",
            json={"carNumber": tail},
            catch_response=True,
            name="/search [miss]",
        ) as resp:
            if resp.status_code == 404:
                resp.success()   # 404는 정상 응답
            else:
                resp.failure(f"unexpected status: {resp.status_code}")

    @task(1)
    def view_settings(self):
        """설정 페이지 접속"""
        self.client.get("/settings", name="/settings")
