from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import csv
import os
import shutil
import base64
import requests as http_requests
from datetime import datetime
import threading
import logging

from utils.fee_calculator import calc_fee
from utils.season_pass import is_pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'parkinggo-secret-key-change-in-prod')

# ── 로깅 설정 ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

@app.after_request
def log_request(response):
    logger.info('%s %s %s', request.method, request.path, response.status_code)
    return response
# ─────────────────────────────────────────────────────────────────────────────

# ── 토스페이먼츠 키 설정 ──────────────────────────────────────────────────────
# 실제 서비스 시 환경변수로 관리 권장
# 대시보드: https://developers.tosspayments.com
TOSS_CLIENT_KEY = os.environ.get('TOSS_CLIENT_KEY', 'test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq')
TOSS_SECRET_KEY = os.environ.get('TOSS_SECRET_KEY', 'test_sk_zXLkKEypNArWmo50nX3lmeaxYG5R')
# ─────────────────────────────────────────────────────────────────────────────

CSV_PATH = os.path.join(app.root_path, 'static', 'data', 'car_data.csv')
PAYMENT_CSV_PATH = os.path.join(app.root_path, 'static', 'data', 'payment_history.csv')
PAID_CAR_CSV_PATH = os.path.join(app.root_path, 'static', 'data', 'paid_car_data.csv')

PAYMENT_CSV_HEADERS = ['차량번호', '결제시간', '결제금액', '주문번호', '결제수단', '승인키']
PAID_CAR_CSV_HEADERS = ['차량번호', '입차시간', '결제시간', '결제금액', '주문번호', '결제수단', '승인키']

IMAGE_DIR = os.path.join(app.root_path, 'static', 'image')
PAID_IMAGE_DIR = os.path.join(app.root_path, 'static', 'image', 'paid')

_csv_lock = threading.Lock()        # CSV 캐시 보호
_payment_csv_lock = threading.Lock() # 결제 CSV 쓰기 보호

def append_payment_record(car_num, amount, order_id, method, payment_key, approved_at):
    with _payment_csv_lock:
        file_exists = os.path.isfile(PAYMENT_CSV_PATH)
        with open(PAYMENT_CSV_PATH, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=PAYMENT_CSV_HEADERS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                '차량번호': car_num,
                '결제시간': approved_at,
                '결제금액': amount,
                '주문번호': order_id,
                '결제수단': method,
                '승인키': payment_key,
            })

def move_car_to_paid(car_num, approved_at, amount, order_id, method, payment_key):
    global _csv_cache, _csv_mtime

    entry_time = None
    with _csv_lock:
        remaining = []
        try:
            with open(CSV_PATH, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['차량번호'] == car_num:
                        entry_time = row['입차시간']
                    else:
                        remaining.append(row)
        except OSError:
            return

        with open(CSV_PATH, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['차량번호', '입차시간'])
            writer.writeheader()
            writer.writerows(remaining)

        _csv_cache = None
        _csv_mtime = None

    with _payment_csv_lock:
        file_exists = os.path.isfile(PAID_CAR_CSV_PATH)
        with open(PAID_CAR_CSV_PATH, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=PAID_CAR_CSV_HEADERS)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                '차량번호': car_num,
                '입차시간': entry_time or '',
                '결제시간': approved_at,
                '결제금액': amount,
                '주문번호': order_id,
                '결제수단': method,
                '승인키': payment_key,
            })

    src = os.path.join(IMAGE_DIR, f'{car_num}.jpg')
    if os.path.isfile(src):
        os.makedirs(PAID_IMAGE_DIR, exist_ok=True)
        shutil.move(src, os.path.join(PAID_IMAGE_DIR, f'{car_num}.jpg'))
PASS_PATH = r"C:\SmartParkingSpotSolution\ShareSystem\Json\vehicle_data.json"

_csv_cache = None
_csv_mtime = None

def read_data():
    global _csv_cache, _csv_mtime
    with _csv_lock:
        try:
            mtime = os.path.getmtime(CSV_PATH)
        except OSError:
            return _csv_cache or []

        if _csv_cache is not None and mtime == _csv_mtime:
            return _csv_cache

        data = []
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append({
                    'car_num': row['차량번호'],
                    'ent': row['입차시간'],
                    'discount': 0
                })
        _csv_cache = data
        _csv_mtime = mtime
        return _csv_cache

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    tail = request.json.get('carNumber')
    if not tail or len(tail) != 4:
        return jsonify({'error': '유효한 차량 번호를 입력해주세요.'}), 400

    cars = read_data()
    match = [c for c in cars if c['car_num'][-4:] == tail]

    if len(match) == 1:
        return jsonify({'redirect': url_for('result', carNumber=match[0]['car_num'])})
    elif len(match) > 1:
        return jsonify({'redirect': url_for('select', carNumber=tail)})
    else:
        return jsonify({'error': '차량 정보를 찾을 수 없습니다.'}), 404

@app.route('/select')
def select():
    tail = request.args.get('carNumber')
    cars = read_data()
    match = [c for c in cars if c['car_num'][-4:] == tail]

    # 템플릿에서 사용할 수 있도록 key 이름 매핑
    car_list = [
        {
            'carNumber': c['car_num'],
            'entryTime': c['ent']
        }
        for c in match
    ]

    return render_template('select.html', cars=car_list, carNumber=tail)


@app.route('/result')
def result():
    car_num = request.args.get('carNumber')
    if not car_num:
        return "차량 번호 정보가 없습니다.", 400

    cars = read_data()
    car = next((c for c in cars if c['car_num'] == car_num), None)

    if car:
        if is_pass(car_num, PASS_PATH):
            duration = "-"
            fee = 0
            total = "정기권 입니다"
        else:
            duration, fee = calc_fee(car['ent'])
            total = f"{fee:,}" if isinstance(fee, int) else str(fee)

        session['pending_car_num'] = car['car_num']
        return render_template(
            'result.html',
            carNumber=car['car_num'],
            entryTime=car['ent'],
            parkingTime=duration,
            parkingFee=fee,
            discount=0,
            total=total,
            carImage=f"/static/image/{car_num}.jpg",
            toss_client_key=TOSS_CLIENT_KEY,
        )
    else:
        return "차량 정보를 찾을 수 없습니다.", 404

@app.route('/payment', methods=['GET'])
def payment():
    car_num = request.args.get('carNumber')
    total = request.args.get('total')
    if not car_num or not total:
        return "결제 요청에 필요한 정보가 부족합니다.", 400

    session['pending_car_num'] = car_num
    return render_template('payment.html', carNumber=car_num, total=total,
                           toss_client_key=TOSS_CLIENT_KEY)

@app.route('/payment/success')
def payment_success():
    payment_key = request.args.get('paymentKey')
    order_id = request.args.get('orderId')
    amount = request.args.get('amount')

    if not all([payment_key, order_id, amount]):
        return "결제 정보가 올바르지 않습니다.", 400

    auth = base64.b64encode(f'{TOSS_SECRET_KEY}:'.encode()).decode()
    response = http_requests.post(
        'https://api.tosspayments.com/v1/payments/confirm',
        headers={
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/json'
        },
        json={
            'paymentKey': payment_key,
            'orderId': order_id,
            'amount': int(amount)
        },
        timeout=10
    )

    data = response.json()
    if response.status_code == 200:
        car_num = session.pop('pending_car_num', '알 수 없음')
        approved_at = data.get('approvedAt', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        paid_amount = data.get('totalAmount', 0)
        paid_order_id = data.get('orderId', order_id)
        paid_method = data.get('method', '')
        paid_key = data.get('paymentKey', payment_key)
        append_payment_record(
            car_num=car_num,
            amount=paid_amount,
            order_id=paid_order_id,
            method=paid_method,
            payment_key=paid_key,
            approved_at=approved_at,
        )
        move_car_to_paid(
            car_num=car_num,
            approved_at=approved_at,
            amount=paid_amount,
            order_id=paid_order_id,
            method=paid_method,
            payment_key=paid_key,
        )
        return render_template('payment_success.html', payment=data, carNumber=car_num)
    else:
        return render_template('payment_fail.html',
                               error_code=data.get('code', 'UNKNOWN'),
                               error_message=data.get('message', '알 수 없는 오류'))

@app.route('/payment/fail')
def payment_fail():
    error_code = request.args.get('code', 'UNKNOWN')
    error_message = request.args.get('message', '결제가 취소되었거나 오류가 발생했습니다.')
    return render_template('payment_fail.html',
                           error_code=error_code,
                           error_message=error_message)

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    from waitress import serve
    logger.info('서버 시작 - http://0.0.0.0:5000 (threads=16)')
    serve(app, host='0.0.0.0', port=5000, threads=16)
