# 서울 주요 23곳 실시간 혼잡도 매시간 수집 (9장 '자동 수집' 예제 실물)
# GitHub Actions가 매시간 실행 → data/seoul_congestion_log.csv 에 한 줄씩 쌓음
import os, csv, requests
from datetime import datetime, timezone, timedelta
import pandas as pd

KEY = os.environ["SEOUL_KEY"]
BASE = "http://openapi.seoul.go.kr:8088"
KST = timezone(timedelta(hours=9))
now = datetime.now(KST).strftime("%Y-%m-%d %H:00")

xy = pd.read_csv("data/seoul_area_xy.csv")  # 코드·지역명·위도·경도 (23곳)
out = "data/seoul_congestion_log.csv"
is_new = not os.path.exists(out)

n = 0
with open(out, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if is_new:
        w.writerow(["시각", "코드", "지역명", "혼잡도", "인구min", "인구max", "위도", "경도"])
    for _, r in xy.iterrows():
        try:
            url = f"{BASE}/{KEY}/json/citydata_ppltn/1/5/{r['코드']}"
            d = requests.get(url, timeout=20).json()["SeoulRtd.citydata_ppltn"][0]
            w.writerow([now, r["코드"], d["AREA_NM"], d["AREA_CONGEST_LVL"],
                        d.get("AREA_PPLTN_MIN"), d.get("AREA_PPLTN_MAX"), r["위도"], r["경도"]])
            n += 1
        except Exception as e:
            print("skip", r["코드"], e)
print(now, "수집", n, "곳")
