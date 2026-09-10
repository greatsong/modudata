# kobis_movies.csv의 영화마다 감독·배우 정보를 붙여 kobis_people.csv를 만든다.
#   · 당곡고 데이터과학 7차시 실험실 — "속성을 더 모으면 결과가 달라진다"를 확인하는 자료.
#   · KOBIS 영화 상세 API에서 감독 이름, 배우 수를 받아 온다. 이미 아는 영화는 다시 묻지 않는다.
#   · 감독의 지난 흥행은 이 표를 쓰는 쪽에서 계산한다(그 영화보다 먼저 개봉한 작품만 세도록).
# 컬럼: movieCd,movieNm,openDt,director,actors_n,lead_n,showTm,watchGrade,company
import csv
import os
import time

import requests

KEY = os.environ["KOBIS_KEY"]
INFO = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"
SRC = "data/kobis_movies.csv"
OUT = "data/kobis_people.csv"
COLS = ["movieCd", "movieNm", "openDt", "director", "actors_n", "lead_n", "showTm", "watchGrade", "company"]
LEAD = 3          # 배우 목록 앞쪽 몇 명을 주연으로 볼지 (KOBIS는 비중 순으로 준다)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fetch(code):
    res = requests.get(INFO, params={"key": KEY, "movieCd": code}, timeout=20)
    res.raise_for_status()
    info = res.json()["movieInfoResult"]["movieInfo"]
    actors = info.get("actors", [])
    dirs = info.get("directors", [])
    audits = info.get("audits", [])
    comps = [c for c in info.get("companys", []) if c.get("companyPartNm") == "배급사"]
    return {
        "director": "/".join(d.get("peopleNm", "") for d in dirs),
        "actors_n": len(actors),
        "lead_n": min(len(actors), LEAD),
        "showTm": info.get("showTm", ""),
        "watchGrade": audits[0].get("watchGradeNm", "") if audits else "",
        "company": comps[0].get("companyNm", "") if comps else "",
    }


movies = read_csv(SRC)
known = {r["movieCd"]: r for r in read_csv(OUT) if r.get("director")}
out, fetched, failed = [], 0, 0
for m in movies:
    code = m["movieCd"]
    row = {"movieCd": code, "movieNm": m["movieNm"], "openDt": m["openDt"]}
    if code in known:
        row.update({k: known[code].get(k, "") for k in COLS[3:]})
    else:
        try:
            row.update(fetch(code))
            fetched += 1
            time.sleep(0.2)
        except Exception as exc:
            print(f"  상세 조회 실패 {code}: {exc}")
            row.update({k: "" for k in COLS[3:]})
            failed += 1
    out.append(row)

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(out)
print(f"kobis_people.csv 생성 · 영화 {len(out)}편 · 새로 조회 {fetched}편 · 실패 {failed}편")
