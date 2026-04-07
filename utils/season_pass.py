import os
import json
from datetime import datetime

def is_pass(car_num, json_path):
    if not os.path.exists(json_path):
        return False

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            today = datetime.now().date()
            for item in data.get("items", []):
                if item["car_number"] == car_num:
                    start = datetime.strptime(item["start_date"], "%Y-%m-%d").date()
                    end = datetime.strptime(item["end_date"], "%Y-%m-%d").date()
                    if start <= today <= end:
                        return True
    except Exception as e:
        print(f"PASS CHECK ERROR: {e}")
        return False

    return False
