# 영화코드별 장르·국가 표를 만든다 — kobis_genres.csv (당곡고 데이터과학 영화 API 프로젝트용)
# KOBIS 영화 상세 API(searchMovieInfo)를 코드마다 한 번씩 부른다.
#   · 대상: kobis_weekly.csv에 등장한 영화코드 전체
#   · 키의 일 호출 한도가 있어 한 번 실행에 MAX_CALLS까지만 채우고 다음 실행에서 이어 간다
#   · 이미 채운 코드는 다시 부르지 않는다 (여러 번 실행해도 안전)
# 컬럼: 영화코드,영화명,개봉일,장르,대표장르,국가,대표국가
#   장르·국가는 여러 개면 쉼표로 잇고, 대표장르·대표국가는 첫 번째 값이다.
import csv
import os
import time
from urllib.parse import urlencode

import requests

KEY = os.environ["KOBIS_KEY"]              # 키는 코드 밖, GitHub 시크릿에서
URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"
SRC = "data/kobis_weekly.csv"
OUT = "data/kobis_genres.csv"
HEADER = ["영화코드", "영화명", "개봉일", "장르", "대표장르", "국가", "대표국가"]
MAX_CALLS = 2400                           # 한 번 실행의 호출 상한 (일 한도 3,000 안쪽)


def load_done():
    if not os.path.exists(OUT):
        return {}, []
    with open(OUT, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return {r[0] for r in rows[1:] if r}, [r for r in rows[1:] if r]


def targets():
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        return sorted({r["영화코드"] for r in csv.DictReader(f)})


def fetch(code):
    res = requests.get(f"{URL}?{urlencode({'key': KEY, 'movieCd': code})}", timeout=20)
    res.raise_for_status()
    info = res.json()["movieInfoResult"]["movieInfo"]
    genres = [g["genreNm"] for g in info.get("genres", [])]
    nations = [n["nationNm"] for n in info.get("nations", [])]
    return [code, info.get("movieNm", ""), info.get("openDt", ""),
            ",".join(genres), genres[0] if genres else "",
            ",".join(nations), nations[0] if nations else ""]


done, rows = load_done()
todo = [c for c in targets() if c not in done]
print(f"대상 {len(done) + len(todo)}편 · 남은 {len(todo)}편")

calls = 0
for code in todo:
    if calls >= MAX_CALLS:
        break
    try:
        rows.append(fetch(code))
    except Exception as e:                 # 응답이 없는 코드는 빈 값으로 남겨 다시 부르지 않는다
        rows.append([code, "", "", "", "", "", ""])
        print(f"  {code} 실패: {e}")
    calls += 1
    time.sleep(0.1)
    if calls % 500 == 0:
        print(f"  {calls}편 진행")

if calls:
    rows.sort(key=lambda r: r[0])
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(rows)

left = len(todo) - calls
print(f"{calls}편 수집 · 총 {len(rows)}편 · 남은 {left}편" + (" — 완료" if left == 0 else ""))
