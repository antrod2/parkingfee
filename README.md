# parkingfee

주차 요금 정산 웹 애플리케이션 (Flask 기반)

---

## 프로젝트 구조

```
parkingfee/
├── app.py                  # Flask 메인 애플리케이션
├── utils/
│   ├── fee_calculator.py   # 주차 요금 계산 로직
│   └── season_pass.py      # 정기권 유효성 확인
├── templates/
│   ├── index.html          # 차량 번호 입력 화면
│   ├── select.html         # 동일 번호 차량 선택 화면
│   ├── result.html         # 요금 조회 결과 화면
│   ├── payment.html        # 결제 화면
│   └── settings.html       # 설정 화면
└── static/
    ├── css/                # 스타일시트
    ├── data/               # car_data.csv (입차 데이터)
    └── image/              # 차량 이미지 (차량번호.jpg)
```

---

## 주요 기능

### 1. 차량 조회 (`app.py`)
- 사용자가 차량 번호 뒤 4자리를 입력하면 CSV에서 입차 정보를 검색
- 1건 매칭: 바로 결과 화면으로 이동
- 다건 매칭: 차량 선택 화면(`select.html`)으로 이동
- CSV 파일은 mtime 기반 캐싱으로 불필요한 재읽기 방지

### 2. 요금 계산 (`utils/fee_calculator.py`)
- **무료**: 입차 후 29분 이내
- **기본료**: 600원 (최초 부과)
- **추가 요금**: 10분당 200원
- **야간 무료**: 00:00 ~ 08:00 구간은 요금 미부과
- **일일 최대**: 6,000원 (날짜가 바뀌면 일일 요금 초기화)
- 주차 시간은 `X일 X시 X분` 형식으로 출력

### 3. 정기권 확인 (`utils/season_pass.py`)
- 외부 JSON 파일(`vehicle_data.json`)에서 정기권 정보 로드
- 차량번호, 시작일, 만료일을 기준으로 당일 유효 여부 판단
- 정기권 차량은 요금 0원, 주차 시간 `-` 표시

---

## 데이터 흐름

```
사용자 입력 (차량번호 4자리)
    ↓
CSV 검색 (car_data.csv)
    ↓
정기권 확인 (vehicle_data.json)
    ↓ 정기권 아님
요금 계산 (calc_fee)
    ↓
결과 표시 → 결제
```

---

## 외부 의존 경로

| 경로 | 용도 |
|------|------|
| `static/data/car_data.csv` | 입차 차량 데이터 (차량번호, 입차시간) |
| `C:\SmartParkingSpotSolution\ShareSystem\Json\vehicle_data.json` | 정기권 차량 데이터 |
| `static/image/{차량번호}.jpg` | 차량 이미지 |

---

## 실행 방법

```bash
pip install flask
python app.py
```

기본 포트: `http://0.0.0.0:5000`

---

## 요금 계산 예시

| 주차 시간 | 요금 |
|-----------|------|
| 29분 이내 | 0원 (무료) |
| 30분 ~ 39분 | 400원 (기본 600 - 첫 구간 할인 200) |
| 40분 ~ 49분 | 600원 |
| 1시간 | 800원 |
| 일 최대 | 6,000원 |
