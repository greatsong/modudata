# KOBIS 일별 박스오피스를 kobis_daily.csv에 날짜별로 누적 (당곡고 데이터과학 3·4장 데이터)
# GitHub Actions가 매일 실행 → 파일의 마지막 날짜 다음 날부터 '어제'(한국 시간)까지 하루씩 채운다.
#   · 이미 들어 있는 날짜는 건너뛴다 (여러 번 실행해도 안전)
#   · UNTIL 이후로는 채우지 않는다 — 수업이 공통 스냅샷을 전제로 하므로 학기 중에는 표를 동결한다
#   · 하루당 TOP10 열 줄, 원본 응답의 순서 그대로
# 컬럼: 날짜,순위,영화코드,영화명,일관객,누적관객,스크린수,상영횟수
import csv
import os
import time
from datetime import date, datetime, timedelta, timezone

import requests

KEY = os.environ["KOBIS_KEY"]              # 키는 코드 밖, GitHub 시크릿에서
URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
CSV = "data/kobis_daily.csv"
KST = timezone(timedelta(hours=9))
MAX_DAYS = 40                              # 한 번에 채우는 상한 (API 과다 호출 방지)
UNTIL = "20260831"                         # 공통 스냅샷 종료일 — 다음 학기에 이 날짜만 옮기면 다시 쌓인다


def read_rows():
    with open(CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, [r for r in reader if r]


def fetch(target):
    res = requests.get(URL, params={"key": KEY, "targetDt": target}, timeout=20)
    res.raise_for_status()
    payload = res.json()["boxOfficeResult"]["dailyBoxOfficeList"]
    return [
        [
            target,
            m["rank"],
            m["movieCd"],
            m["movieNm"],
            m["audiCnt"],
            m["audiAcc"],
            m["scrnCnt"],
            m["showCnt"],
        ]
        for m in payload
    ]


header, rows = read_rows()
have = {r[0] for r in rows}
last = max(have)
start = datetime.strptime(last, "%Y%m%d").date() + timedelta(days=1)
end = datetime.now(KST).date() - timedelta(days=1)          # 어제(한국 시간)까지
end = min(end, datetime.strptime(UNTIL, "%Y%m%d").date())   # 단, 스냅샷 종료일을 넘지 않는다

added_days = 0
day = start
while day <= end and added_days < MAX_DAYS:
    target = day.strftime("%Y%m%d")
    if target not in have:
        new_rows = fetch(target)
        if new_rows:
            rows.extend(new_rows)
            added_days += 1
            print(f"{target} {len(new_rows)}행 추가")
        else:
            print(f"{target} 응답 없음 — 건너뜀")
        time.sleep(0.5)
    day += timedelta(days=1)

if added_days:
    rows.sort(key=lambda r: (r[0], int(r[1])))
    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, lineterminator="\r\n")
        writer.writerow(header)
        writer.writerows(rows)

days = len({r[0] for r in rows})
print(f"{added_days}일 추가 · 총 {days}일 {len(rows)}행 (마지막 {max(r[0] for r in rows)})")
