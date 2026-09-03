# 서울 실시간 혼잡도 자동 수집 (9장 '자동 수집' 예제 실물)
# GitHub Actions가 매시간 실행 → data/seoul_congestion_log.csv 에 한 줄씩 쌓음
# 매시간 121곳 전체 (data/seoul_area_all.csv). 서울 열린데이터광장 일반 오픈API는 호출 횟수 제한이 없다
# (1일 1,000회 제한은 실시간 지하철 API에만 해당). 하루 121 × 24 = 2,904회.
import os, csv, time, requests
from datetime import datetime, timezone, timedelta
import pandas as pd

KEY = os.environ["SEOUL_KEY"]
BASE = "http://openapi.seoul.go.kr:8088"
KST = timezone(timedelta(hours=9))
now_dt = datetime.now(KST)
now = now_dt.strftime("%Y-%m-%d %H:00")
places = pd.read_csv("data/seoul_area_all.csv")       # 코드·지역명·분류·위도·경도 (121곳)

out = "data/seoul_congestion_log.csv"
is_new = not os.path.exists(out)

n = 0
with open(out, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if is_new:
        w.writerow(["시각", "코드", "지역명", "혼잡도", "인구min", "인구max", "위도", "경도"])
    for _, r in places.iterrows():
        try:
            url = f"{BASE}/{KEY}/json/citydata_ppltn/1/5/{r['코드']}"
            d = requests.get(url, timeout=20).json()["SeoulRtd.citydata_ppltn"][0]
            w.writerow([now, r["코드"], d["AREA_NM"], d["AREA_CONGEST_LVL"],
                        d.get("AREA_PPLTN_MIN"), d.get("AREA_PPLTN_MAX"), r["위도"], r["경도"]])
            n += 1
        except Exception as e:
            print("skip", r["코드"], e)
        time.sleep(0.2)                       # 서버에 부담을 주지 않게 잠깐 쉬기
print(now, "수집", n, "곳")
