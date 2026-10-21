# 서울(지점 108) 일별 기온으로 seoul.csv 자동 최신화 (3·8장 데이터)
# 마지막 날짜 다음 날부터 '어제'까지 빠진 날을 전부 append (백필 — 하루 실패해도 다음 실행이 메꿈)
# 컬럼: 날짜,지점,평균기온,최저기온,최고기온 (기존 seoul.csv 형식 그대로)
#
# 데이터 출처 2중화 (키가 있는 쪽을 자동 선택):
#   · DATA_GO_KR_KEY — 공공데이터포털 ASOS 일자료 (GitHub Actions용 — 해외 IP 허용)
#   · KMA_KEY        — 기상청 API허브 (한국 IP 전용 → 로컬 실행용. GitHub 러너에서는 차단됨)
import os
import requests
from datetime import datetime, timedelta, timezone

CSV = "data/seoul.csv"
STN = "108"                                # 서울
KST = timezone(timedelta(hours=9))

# 1) 지금 CSV의 마지막 날짜 확인 → 그 다음 날부터 어제(KST)까지가 수집 구간
with open(CSV, encoding="utf-8-sig") as f:
    last = f.read().rstrip().rsplit("\n", 1)[-1].split(",")[0]   # 예: 2026-06-25
start = datetime.strptime(last, "%Y-%m-%d").date() + timedelta(days=1)
end = datetime.now(KST).date() - timedelta(days=1)               # 어제까지만 (오늘은 미확정)
if start > end:
    print(f"이미 최신 ({last}) · 추가할 날 없음")
    raise SystemExit(0)


def fetch_datago(key):
    """공공데이터포털 ASOS 일자료 → [(날짜, 평균, 최저, 최고)]"""
    url = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
    out, page = [], 1
    while True:
        d = requests.get(url, params={
            "serviceKey": key, "dataType": "JSON", "dataCd": "ASOS", "dateCd": "DAY",
            "startDt": start.strftime("%Y%m%d"), "endDt": end.strftime("%Y%m%d"),
            "stnIds": STN, "numOfRows": "300", "pageNo": str(page),
        }, timeout=60).json()
        body = d["response"]["body"]
        items = body["items"].get("item", [])
        for it in items:
            if it.get("avgTa") and it.get("minTa") and it.get("maxTa"):
                out.append((it["tm"], it["avgTa"], it["minTa"], it["maxTa"]))
        if page * 300 >= int(body["totalCount"]):
            return out
        page += 1


def fetch_apihub(key):
    """기상청 API허브 일자료(한국 IP 전용) → [(날짜, 평균, 최저, 최고)]"""
    res = requests.get("https://apihub.kma.go.kr/api/typ01/url/kma_sfcdd3.php", params={
        "tm1": start.strftime("%Y%m%d"), "tm2": end.strftime("%Y%m%d"),
        "stn": STN, "help": "1", "authKey": key,
    }, timeout=30)
    res.raise_for_status()
    lines = res.text.splitlines()
    cols = next((ln.lstrip("#").split() for ln in lines
                 if ln.startswith("#") and "TA_AVG" in ln and "TM" in ln), None)
    if cols is None:
        raise SystemExit(f"응답에서 컬럼 헤더를 못 찾음 — 활용신청/키 확인 필요\n{res.text[:300]}")
    i = {c: cols.index(c) for c in ("TM", "TA_AVG", "TA_MAX", "TA_MIN")}
    out = []
    for ln in lines:
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        tm, avg, tmax, tmin = p[i["TM"]], p[i["TA_AVG"]], p[i["TA_MAX"]], p[i["TA_MIN"]]
        if any(float(v) <= -90 for v in (avg, tmax, tmin)):     # 결측
            continue
        out.append((f"{tm[:4]}-{tm[4:6]}-{tm[6:8]}", avg, tmin, tmax))
    return out


# 2) 키가 있는 출처로 수집
if os.environ.get("DATA_GO_KR_KEY"):
    fetched = fetch_datago(os.environ["DATA_GO_KR_KEY"])
elif os.environ.get("KMA_KEY"):
    fetched = fetch_apihub(os.environ["KMA_KEY"])
else:
    raise SystemExit("키 없음 — DATA_GO_KR_KEY 또는 KMA_KEY 환경변수 필요")

rows = [f"{d},{STN},{avg},{tmin},{tmax}" for d, avg, tmin, tmax in fetched]

# 3) append 저장 (파일 끝에 줄바꿈 없으면 먼저 보정)
if rows:
    with open(CSV, "rb") as f:
        f.seek(-1, 2)
        needs_nl = f.read(1) != b"\n"
    with open(CSV, "a", encoding="utf-8") as f:
        if needs_nl:
            f.write("\n")
        f.write("\n".join(rows) + "\n")
print(f"{start}~{end} 구간 · {len(rows)}일 추가 · 마지막 {rows[-1].split(',')[0] if rows else last}")

# 4) 파생 파일 재생성 — seoul_daily(지점 컬럼 제외) · seoul_yearly(완결연도 연평균)
import csv

by_year = {}
with open(CSV, encoding="utf-8-sig") as f, \
     open("data/seoul_daily.csv", "w", encoding="utf-8", newline="") as fd:
    w = csv.writer(fd)
    w.writerow(["날짜", "평균기온", "최저기온", "최고기온"])
    for r in csv.DictReader(f):
        w.writerow([r["날짜"], r["평균기온"], r["최저기온"], r["최고기온"]])
        if r["평균기온"]:
            by_year.setdefault(r["날짜"][:4], []).append(float(r["평균기온"]))
with open("data/seoul_yearly.csv", "w", encoding="utf-8", newline="") as fy:
    w = csv.writer(fy)
    w.writerow(["연도", "평균기온"])
    for y in sorted(by_year):
        if len(by_year[y]) >= 300 and y != str(end.year):   # 관측 부족(1907·1950·1953)·진행 중인 해 제외
            w.writerow([y, round(sum(by_year[y]) / len(by_year[y]), 1)])
print("파생 재생성 완료: seoul_daily.csv · seoul_yearly.csv")
