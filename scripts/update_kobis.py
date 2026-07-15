# KOBIS 일별 박스오피스로 kobis.csv 자동 최신화 (6·8장 데이터)
# GitHub Actions가 매일 실행 → '어제' TOP10을 반영:
#   · 새 영화  : '개봉 초기 성적'(스크린·상영·순위·관객)을 한 줄로 추가
#   · 기존 영화: '최종관객'(누적)만 더 큰 값으로 갱신 (초기 성적은 그대로 보존)
# 컬럼: 영화명,개봉일,스크린수,상영횟수,순위,관객수,최종관객
import os
import requests
from datetime import date, timedelta
import pandas as pd

KEY = os.environ["KOBIS_KEY"]              # 키는 코드 밖, GitHub 시크릿에서
URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
CSV = "data/kobis.csv"

target = (date.today() - timedelta(days=1)).strftime("%Y%m%d")   # 어제 = 가장 최신
res = requests.get(URL, params={"key": KEY, "targetDt": target}, timeout=20)
movies = res.json()["boxOfficeResult"]["dailyBoxOfficeList"]

df = pd.read_csv(CSV)
names = set(df["영화명"])
added = updated = 0

for m in movies:
    name = m["movieNm"]
    audi_acc = int(m["audiAcc"])           # 개봉일부터의 누적 = '최종관객'에 근접

    if name in names:
        # 이미 있는 영화 → 누적 관객이 늘었으면 '최종관객'만 갱신
        idx = df.index[df["영화명"] == name][0]
        if audi_acc > int(df.at[idx, "최종관객"]):
            df.at[idx, "최종관객"] = audi_acc
            updated += 1
    else:
        # 새 영화 → 지금(개봉 초기) 성적을 한 줄로 추가
        df.loc[len(df)] = {
            "영화명": name,
            "개봉일": m["openDt"],
            "스크린수": int(m["scrnCnt"]),
            "상영횟수": int(m["showCnt"]),
            "순위": int(m["rank"]),
            "관객수": int(m["audiCnt"]),    # 처음 잡힌 날(개봉 초기)의 관객수
            "최종관객": audi_acc,
        }
        names.add(name)
        added += 1

df.to_csv(CSV, index=False, encoding="utf-8-sig")
print(f"{target} 반영 · 새 영화 {added}편 · 최종관객 갱신 {updated}편 · 총 {len(df)}편")
