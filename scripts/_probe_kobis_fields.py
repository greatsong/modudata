# KOBIS 영화 상세·목록 API가 주는 필드를 한 번 찍어 본다(일회성 확인용).
import os, json, requests
KEY = os.environ["KOBIS_KEY"]
INFO = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"
LIST = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json"
code = os.environ.get("PROBE_CODE", "20255393")
d = requests.get(INFO, params={"key": KEY, "movieCd": code}, timeout=20).json()["movieInfoResult"]["movieInfo"]
print("=== searchMovieInfo 최상위 키 ===");  print(sorted(d.keys()))
for k in ("directors", "actors", "companys", "audits", "staffs", "genres", "nations", "showTypes"):
    v = d.get(k)
    if isinstance(v, list):
        print(f"\n[{k}] {len(v)}개 · 첫 항목 키: {sorted(v[0].keys()) if v else '없음'}")
        for x in v[:4]: print("   ", json.dumps(x, ensure_ascii=False)[:160])
print("\n영화명:", d.get("movieNm"), "· 개봉일:", d.get("openDt"), "· 상영시간:", d.get("showTm"))
l = requests.get(LIST, params={"key": KEY, "itemPerPage": 3, "openStartDt": 2026}, timeout=20).json()["movieListResult"]["movieList"]
print("\n=== searchMovieList 첫 항목 ===");  print(json.dumps(l[0], ensure_ascii=False)[:400] if l else "없음")
