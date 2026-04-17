from datetime import datetime, timedelta

def calc_fee(ent_str):
    ent = datetime.strptime(ent_str, "%Y-%m-%d %H:%M")
    ext = datetime.now()
    free_until = ent + timedelta(minutes=29)
    day_max = 6000
    cur_date = ent.date()
    day_fee = 0
    total = 0

    if ext <= free_until:
        mins = int((ext - ent).total_seconds() / 60)
        return fmt_minutes(mins), 0

    cur = free_until

    while cur < ext:
        if cur.date() != cur_date:
            cur_date = cur.date()
            day_fee = 0

        if 0 <= cur.hour < 8:
            cur = cur.replace(hour=8, minute=0, second=0, microsecond=0)
            continue

        if total == 0:
            # 첫 청구 스텝: 기본 요금 600원 (30~39분 구간)
            total += 600
            day_fee += 600
        elif day_fee + 200 <= day_max:
            # 이후 스텝: 10분당 200원 추가
            total += 200
            day_fee += 200

        cur += timedelta(minutes=10)

    mins = int((ext - ent).total_seconds() / 60)
    return fmt_minutes(mins), total

def fmt_minutes(mins):
    d = mins // (24 * 60)
    h = (mins % (24 * 60)) // 60
    m = mins % 60

    parts = []
    if d > 0:
        parts.append(f"{d} 일")
    if h > 0:
        parts.append(f"{h} 시")
    if m > 0 or not parts:
        parts.append(f"{m} 분")

    return ' '.join(parts)
