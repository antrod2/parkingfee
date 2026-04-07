from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import os

from utils.fee_calculator import calc_fee
from utils.season_pass import is_pass

app = Flask(__name__)

CSV_PATH = os.path.join(app.root_path, 'static', 'data', 'car_data.csv')
PASS_PATH = r"C:\SmartParkingSpotSolution\ShareSystem\Json\vehicle_data.json"

_csv_cache = None
_csv_mtime = None

def read_data():
    global _csv_cache, _csv_mtime
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

        return render_template(
            'result.html',
            carNumber=car['car_num'],
            entryTime=car['ent'],
            parkingTime=duration,
            parkingFee=fee,
            discount=0,
            total=total,
            carImage=f"/static/image/{car_num}.jpg"
        )
    else:
        return "차량 정보를 찾을 수 없습니다.", 404

@app.route('/payment', methods=['GET'])
def payment():
    car_num = request.args.get('carNumber')
    total = request.args.get('total')
    if not car_num or not total:
        return "결제 요청에 필요한 정보가 부족합니다.", 400

    return render_template('payment.html', carNumber=car_num, total=total)

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
