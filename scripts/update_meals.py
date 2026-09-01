# 당곡고 급식을 danggok_meals_live.csv에 날짜별로 누적 (당곡고 데이터과학 5·12장 데이터)
# GitHub Actions가 매일 실행 → 파일의 마지막 날짜 다음 날부터 '어제'(한국 시간)까지 하루씩 채운다.
#   · 하루씩 물으면 응답이 한두 건이라 나이스 인증키가 필요 없다(키 없이 부르면 목록이 다섯 건까지만 온다)
#   · 급식이 없는 날(방학·주말)은 건너뛴다
#   · 이미 들어 있는 날짜는 다시 부르지 않는다 (여러 번 실행해도 안전)
#
# 수업용 스냅샷 danggok_meals.csv는 손대지 않는다 — 5·12차시의 실측 수치가 그 파일 기준이다.
# 컬럼: 날짜,식사,메뉴  (메뉴는 낱개를 세로막대로 이음, 알레르기 번호는 뗀다)
import csv
import os
import re
import shutil
import time
from datetime import datetime, timedelta, timezone

import requests

URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
BASE = "data/danggok_meals.csv"        # 수업용 스냅샷 (읽기만 한다)
CSV = "data/danggok_meals_live.csv"    # 이어 쌓는 파일
ATPT, SCHUL = "B10", "7010073"         # 서울특별시교육청 · 당곡고등학교
KST = timezone(timedelta(hours=9))
MAX_DAYS = 60                          # 한 번에 채우는 상한


def clean(dish):
    """API의 메뉴 문자열을 스냅샷과 같은 표기로 다듬는다."""
    items = []
    for raw in dish.split("<br/>"):
        name = re.sub(r"\([\d.\s]*\)", "", raw)      # 알레르기 번호 제거
        name = name.replace("*", "").strip()
        if name:
            items.append(name)
    return "|".join(items)


def fetch(ymd):
    res = requests.get(URL, params={
        "Type": "json", "ATPT_OFCDC_SC_CODE": ATPT, "SD_SCHUL_CODE": SCHUL,
        "MLSV_FROM_YMD": ymd, "MLSV_TO_YMD": ymd,
    }, timeout=20)
    res.raise_for_status()
    body = res.json()
    if "mealServiceDietInfo" not in body:             # 급식이 없는 날
        return []
    return [[ymd, r["MMEAL_SC_NM"], clean(r["DDISH_NM"])]
            for r in body["mealServiceDietInfo"][1]["row"]]


if not os.path.exists(CSV):                            # 첫 실행: 스냅샷을 씨앗으로 복사
    shutil.copyfile(BASE, CSV)

with open(CSV, encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = [r for r in reader if r]

have = {r[0] for r in rows}
start = datetime.strptime(max(have), "%Y%m%d").date() + timedelta(days=1)
end = datetime.now(KST).date() - timedelta(days=1)

added = days = 0
day = start
while day <= end and days < MAX_DAYS:
    ymd = day.strftime("%Y%m%d")
    if ymd not in have:
        new = fetch(ymd)
        if new:
            rows.extend(new)
            added += len(new)
            print(f"{ymd} {len(new)}건 추가")
        days += 1
        time.sleep(0.3)
    day += timedelta(days=1)

if added:
    rows.sort(key=lambda r: (r[0], r[1]))
    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        w.writerows(rows)

print(f"{added}행 추가 · 총 {len(rows)}행 (마지막 {max(r[0] for r in rows)})")
