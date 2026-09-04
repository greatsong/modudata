# 10장 수집기 - 서울 121곳의 실시간 혼잡도를 매시간 한 줄씩 csv에 덧붙인다
# 깃허브 액션이 실행한다. 키는 코드가 아니라 깃허브 시크릿(환경변수)에서 읽는다.
import os, csv, time
from datetime import datetime, timezone, timedelta

import requests
import pandas as pd

KEY = os.environ["SEOUL_KEY"]                  # 화면이 없는 일꾼에겐 비밀 금고 대신 환경변수
BASE = "http://openapi.seoul.go.kr:8088"
KST = timezone(timedelta(hours=9))             # 깃허브 시계는 UTC라 한국 시간으로 바꿔 적는다
now = datetime.now(KST).strftime("%Y-%m-%d %H:00")

places = pd.read_csv("data/seoul_area_all.csv")        # 코드, 지역명, 분류, 위도, 경도 (121곳)
out = "data/seoul_congestion_log.csv"
is_new = not os.path.exists(out)

n = 0
with open(out, "a", newline="", encoding="utf-8") as f:  # "a" = 덧붙이기. 파일이 없으면 새로 만든다
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
            print("건너뜀", r["코드"], e)       # 한 곳이 실패해도 멈추지 않고 다음 곳으로
        time.sleep(0.2)                        # 서버에 부담을 주지 않게 잠깐 쉬기
print(now, "수집", n, "곳")
