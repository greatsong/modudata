# 감독별 과거 흥행 기록을 만든다 — 주간 박스오피스(2004~)에서 영화별 최종 누적을 모으고,
# 각 영화의 감독을 KOBIS 상세 API로 받아 붙인다.
#   · 당곡고 7차시 심화 프로젝트용. "감독의 이전 작품 성적"이라는 속성을 만들 수 있게 한다.
#   · 이미 받아 둔 감독은 다시 묻지 않는다(파일에 누적).
#   · 한 번에 받는 수를 MAX로 제한한다. 여러 번 실행하면 이어서 채운다.
# 컬럼: movieCd,movieNm,openDt,director,total_audi
import csv
import os
import time

import requests

KEY = os.environ["KOBIS_KEY"]
INFO = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"
WEEKLY = "data/kobis_weekly.csv"
OUT = "data/kobis_directors.csv"
COLS = ["movieCd", "movieNm", "openDt", "director", "total_audi"]
MAX = int(os.environ.get("MAX_FETCH", "1200"))


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# 1) 주간 표에서 영화별 최종 누적과 개봉일을 모은다
films = {}
for r in read_csv(WEEKLY):
    code = r.get("영화코드")
    if not code:
        continue
    f = films.setdefault(code, {"movieNm": r["영화명"], "openDt": r.get("개봉일", ""), "total_audi": 0})
    try:
        f["total_audi"] = max(f["total_audi"], int(r.get("누적관객") or 0))
    except ValueError:
        pass
    if r.get("개봉일"):
        f["openDt"] = r["개봉일"]

# 2) 이미 아는 감독은 재사용
known = {r["movieCd"]: r["director"] for r in read_csv(OUT) if r.get("director")}
todo = [c for c in films if c not in known]
print(f"주간 표 영화 {len(films)}편 · 이미 아는 감독 {len(known)}편 · 이번에 받을 것 {min(len(todo), MAX)}편")

fetched = failed = 0
for code in todo[:MAX]:
    try:
        res = requests.get(INFO, params={"key": KEY, "movieCd": code}, timeout=20)
        res.raise_for_status()
        info = res.json()["movieInfoResult"]["movieInfo"]
        known[code] = "/".join(d.get("peopleNm", "") for d in info.get("directors", []))
        fetched += 1
    except Exception as exc:
        failed += 1
        if failed <= 3:
            print(f"  조회 실패 {code}: {exc}")
    time.sleep(0.15)

rows = []
for code, f in sorted(films.items()):
    rows.append({"movieCd": code, "movieNm": f["movieNm"], "openDt": f["openDt"],
                 "director": known.get(code, ""), "total_audi": f["total_audi"]})
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
have = sum(1 for r in rows if r["director"])
print(f"kobis_directors.csv · 영화 {len(rows)}편 · 감독 확보 {have}편 · 이번에 받은 것 {fetched}편 · 실패 {failed}편")
if have < len(rows):
    print(f"남은 {len(rows) - have}편은 워크플로를 다시 실행하면 이어서 채운다.")
