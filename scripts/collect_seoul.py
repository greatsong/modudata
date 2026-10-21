# 서울 실시간 혼잡도 자동 수집 (9장 '자동 수집' 예제 실물)
# GitHub Actions가 매시간 실행 → 임시 파일(CONGESTION_OUT)에 쌓고, 하루 한 번 flush_congestion.py가 본 파일에 합친다
# CONGESTION_OUT을 주지 않으면 data/seoul_congestion_log.csv 에 바로 쌓는다(직접 실행할 때)
# 매시간 121곳 전체 (data/seoul_area_all.csv). 서울 열린데이터광장 일반 오픈API는 호출 횟수 제한이 없다
# (1일 1,000회 제한은 실시간 지하철 API에만 해당). 하루 121 × 24 = 2,904회.
import os, sys, csv, time, requests
from datetime import datetime, timezone, timedelta
import pandas as pd

KEY = os.environ["SEOUL_KEY"]
BASE = "http://openapi.seoul.go.kr:8088"
KST = timezone(timedelta(hours=9))
now_dt = datetime.now(KST)
now = now_dt.strftime("%Y-%m-%d %H:00")
places = pd.read_csv("data/seoul_area_all.csv")       # 코드·지역명·분류·위도·경도 (121곳)

out = os.environ.get("CONGESTION_OUT", "data/seoul_congestion_log.csv")
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
is_new = not os.path.exists(out)

n, failed = 0, []
with open(out, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    if is_new:
        w.writerow(["시각", "코드", "지역명", "혼잡도", "인구min", "인구max", "위도", "경도"])
    for _, r in places.iterrows():
        url = f"{BASE}/{KEY}/json/citydata_ppltn/1/5/{r['코드']}"
        for attempt in range(2):                  # 일시 오류면 한 번 더
            try:
                res = requests.get(url, timeout=20)
                res.raise_for_status()
                d = res.json()["SeoulRtd.citydata_ppltn"][0]
                w.writerow([now, r["코드"], d["AREA_NM"], d["AREA_CONGEST_LVL"],
                            d.get("AREA_PPLTN_MIN"), d.get("AREA_PPLTN_MAX"), r["위도"], r["경도"]])
                n += 1
                break
            except Exception as e:
                if attempt == 1:   # 오류 문장에는 키가 든 주소가 들어갈 수 있어 종류·상태 코드만 출력
                    status = getattr(getattr(e, "response", None), "status_code", "")
                    failed.append(r["코드"]); print("skip", r["코드"], type(e).__name__, status)
                else:
                    time.sleep(1)
        time.sleep(0.2)                       # 서버에 부담을 주지 않게 잠깐 쉬기
print(now, "수집", n, "곳", f"/ 실패 {len(failed)}곳" if failed else "")
if n == 0:
    sys.exit("한 곳도 수집하지 못했습니다(키·서비스 상태 확인)")
