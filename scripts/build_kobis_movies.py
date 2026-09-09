# kobis_daily.csv(일별 TOP10 축적)에서 영화 단위 표 kobis_movies.csv를 다시 만든다.
#   · 한 줄 = 영화 한 편. 당곡고 데이터과학 7차시(다중 회귀)의 실습 자료.
#   · genre·nation은 KOBIS 영화 상세 API에서 받아 오고, 이미 아는 영화는 기존 파일 값을 재사용한다(호출 절약).
#   · 재개봉·재상영(첫 등장이 개봉 60일 뒤)은 제외하고, 개봉 전 예매 집계도 빼고 센다 — 개봉 초기 성적을 다루는 표이기 때문
#   · 나머지 열은 모두 일별 표에서 계산한다 — 새 자료가 하루 쌓이면 이 표도 하루만큼 바뀐다.
# 컬럼: movieCd,movieNm,openDt,genre,nation,first_scrn,first_show,first_date,peak,first_week_audi,total_audi,days_in_top10
import csv
import os
import time
from datetime import datetime, timedelta

import requests

KEY = os.environ["KOBIS_KEY"]
INFO = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"
DAILY = "data/kobis_daily.csv"
OUT = "data/kobis_movies.csv"
PEAK_MONTHS = {1, 7, 8, 12}          # 성수기 개봉 — 겨울·여름 방학
COLS = ["movieCd", "movieNm", "openDt", "genre", "nation", "first_scrn", "first_show",
        "first_date", "peak", "first_week_audi", "total_audi", "days_in_top10"]


def read_daily():
    with open(DAILY, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_known():
    """기존 표에서 영화 상세(장르·국적·개봉일)를 재사용한다."""
    known = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("genre") and r.get("nation"):
                    known[r["movieCd"]] = (r["openDt"], r["genre"], r["nation"])
    return known


def fetch_info(code):
    """장르·국적·개봉일. 실패하면 빈 값으로 두고 다음 실행에서 다시 시도한다."""
    try:
        res = requests.get(INFO, params={"key": KEY, "movieCd": code}, timeout=20)
        res.raise_for_status()
        info = res.json()["movieInfoResult"]["movieInfo"]
        genre = "/".join(g["genreNm"] for g in info.get("genres", []))
        nation = "/".join(n["nationNm"] for n in info.get("nations", []))
        return info.get("openDt", ""), genre, nation
    except Exception as exc:                      # 개별 영화 실패가 전체를 멈추지 않게 한다
        print(f"  상세 조회 실패 {code}: {exc}")
        return "", "", ""


rows = read_daily()
known = read_known()
by_movie = {}
for r in rows:
    by_movie.setdefault(r["영화코드"], []).append(r)

out, fetched, skipped = [], 0, 0
for code, recs in by_movie.items():
    recs.sort(key=lambda r: r["날짜"])
    first = recs[0]
    name = recs[-1]["영화명"]
    if code in known:
        open_dt, genre, nation = known[code]
    else:
        open_dt, genre, nation = fetch_info(code)
        fetched += 1
        time.sleep(0.2)                            # API 예의
    base = open_dt or first["날짜"]
    # 개봉 전 기록(예매·시사회로 10위권에 든 날) 제외 — 첫 관측일 스크린 수가 한두 관으로 잡히는 것을 막는다
    if open_dt:
        after = [r for r in recs if r["날짜"] >= open_dt]
        if after:
            recs = after
            first = recs[0]
    # 재개봉·재상영 제외 — 첫 등장이 개봉일보다 두 달 넘게 늦으면 '개봉 초기 성적'이라 부를 수 없다
    try:
        gap = (datetime.strptime(first["날짜"], "%Y%m%d") - datetime.strptime(base, "%Y%m%d")).days
    except ValueError:
        gap = 0
    if gap > 60:
        skipped += 1
        continue
    # 재상영·재개봉 두 번째 거름망 — 첫 기록의 누적 관객이 그날 관객보다 훨씬 크면 이미 상영 이력이 있는 영화다.
    # (개봉일이 재개봉일로 기록되어 위 검사를 통과하는 경우를 잡는다)
    try:
        if int(first["누적관객"]) > int(first["일관객"]) * 3:
            skipped += 1
            continue
    except (ValueError, KeyError):
        pass
    try:
        peak = 1 if datetime.strptime(base, "%Y%m%d").month in PEAK_MONTHS else 0
    except ValueError:
        peak = 0
    # 첫 등장일부터 7일 안의 일관객 합 — 개봉 첫 주 성적
    start = datetime.strptime(first["날짜"], "%Y%m%d").date()
    week_end = start + timedelta(days=6)
    week = sum(int(r["일관객"]) for r in recs
               if start <= datetime.strptime(r["날짜"], "%Y%m%d").date() <= week_end)
    out.append({
        "movieCd": code,
        "movieNm": name,
        "openDt": base,
        "genre": genre,
        "nation": nation,
        "first_scrn": first["스크린수"],
        "first_show": first["상영횟수"],
        "first_date": first["날짜"],
        "peak": peak,
        "first_week_audi": week,
        "total_audi": max(int(r["누적관객"]) for r in recs),
        "days_in_top10": len(recs),
    })

out.sort(key=lambda r: r["movieCd"])
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(out)
print(f"kobis_movies.csv 다시 생성 · 영화 {len(out)}편 · 상세 조회 {fetched}편 · 재개봉 제외 {skipped}편")
