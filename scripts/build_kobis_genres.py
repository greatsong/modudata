# 영화코드별 장르·국가 표를 만든다 — kobis_genres.csv (당곡고 데이터과학 영화 API 프로젝트용)
# KOBIS 영화 상세 API(searchMovieInfo)를 코드마다 한 번씩 부른다.
#   · 대상: kobis_weekly.csv에 등장한 영화코드 전체
#   · 일 호출 한도가 있어 한 번 실행에 MAX_CALLS까지만 채우고 다음 실행에서 이어 간다
#   · 호출이 실패하면 줄을 남기지 않는다 → 다음 실행에서 다시 부른다
#   · 응답은 왔는데 장르가 없는 영화는 영화명을 적어 두고 장르는 빈칸으로 둔다(다시 부르지 않는다)
#   · 실패가 잇달으면(한도 소진으로 보면) 그 자리에서 멈춘다
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
STOP_AFTER_FAILS = 20                      # 잇단 실패가 이만큼이면 멈춘다 (한도 소진으로 본다)


def load_done():
    """이미 확인이 끝난 줄만 남긴다. 영화명이 비어 있으면 실패한 줄이므로 버리고 다시 부른다."""
    if not os.path.exists(OUT):
        return {}
    with open(OUT, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))[1:]
    return {r[0]: r for r in rows if r and r[1]}


def targets():
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        return sorted({r["영화코드"] for r in csv.DictReader(f)})


def fetch(code):
    """성공하면 한 줄을 돌려주고, 호출이 실패하면 None을 돌려준다."""
    res = requests.get(f"{URL}?{urlencode({'key': KEY, 'movieCd': code})}", timeout=20)
    res.raise_for_status()
    body = res.json().get("movieInfoResult")
    if not body or "movieInfo" not in body:          # 안내문이 온 경우 — 실패로 본다
        return None
    info = body["movieInfo"]
    if not info.get("movieCd"):                      # KOBIS에 정보가 없는 코드
        return [code, "(정보 없음)", "", "", "", "", ""]
    genres = [g["genreNm"] for g in info.get("genres", [])]
    nations = [n["nationNm"] for n in info.get("nations", [])]
    return [code, info.get("movieNm", ""), info.get("openDt", ""),
            ",".join(genres), genres[0] if genres else "",
            ",".join(nations), nations[0] if nations else ""]


done = load_done()
todo = [c for c in targets() if c not in done]
print(f"확인 끝난 편수 {len(done):,} · 남은 편수 {len(todo):,}")

calls = fails = 잇단실패 = 0
for code in todo:
    if calls >= MAX_CALLS or 잇단실패 >= STOP_AFTER_FAILS:
        break
    try:
        row = fetch(code)
    except Exception as e:
        row = None
        if fails == 0:
            print(f"  첫 실패 {code}: {e}")
    calls += 1
    if row is None:
        fails += 1
        잇단실패 += 1
    else:
        done[code] = row
        잇단실패 = 0
    time.sleep(0.1)
    if calls % 500 == 0:
        print(f"  {calls}편 호출 · 실패 {fails}편")

if done:
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows([done[c] for c in sorted(done)])

장르있음 = sum(1 for r in done.values() if r[3])
남은 = len([c for c in targets() if c not in done])   # 대상 밖 코드가 섞여도 음수가 되지 않게
멈춤 = " — 잇단 실패로 중단(한도 소진으로 보임)" if 잇단실패 >= STOP_AFTER_FAILS else ""
print(f"{calls}편 호출 · 실패 {fails}편 · 확인 끝난 편수 {len(done):,} "
      f"(장르 있음 {장르있음:,}) · 남은 편수 {남은:,}{멈춤}"
      + (" — 완료" if 남은 == 0 else ""))
