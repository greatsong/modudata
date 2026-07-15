# 서울(지점 108) 일별 기온으로 seoul.csv 자동 최신화 (3·8장 데이터)
# GitHub Actions가 매일 아침 실행 → 마지막 날짜 다음 날부터 '어제'까지 빠진 날을 전부 append
#   · 하루 실패해도 다음 실행이 자동으로 메꿈 (백필 방식)
#   · 컬럼: 날짜,지점,평균기온,최저기온,최고기온  (기존 seoul.csv 형식 그대로)
# 출처: 기상청 API허브(apihub.kma.go.kr) 지상관측 일자료 · 시크릿 KMA_KEY 필요
import os
import requests
from datetime import date, datetime, timedelta, timezone

KEY = os.environ["KMA_KEY"]                # 키는 코드 밖, GitHub 시크릿에서
URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfcdd3.php"
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

# 2) API 호출 (구간 조회) — 응답은 '#' 주석 헤더 + 공백 구분 텍스트
res = requests.get(URL, params={
    "tm1": start.strftime("%Y%m%d"), "tm2": end.strftime("%Y%m%d"),
    "stn": STN, "help": "1", "authKey": KEY,
}, timeout=30)
res.raise_for_status()
lines = res.text.splitlines()

# 3) 헤더(주석)에서 컬럼 위치 찾기 → 순서가 바뀌어도 안전
cols = None
for ln in lines:
    if ln.startswith("#") and "TA_AVG" in ln and "TM" in ln:
        cols = ln.lstrip("#").split()
        break
if cols is None:
    raise SystemExit(f"응답에서 컬럼 헤더를 못 찾음 — 키/파라미터 확인 필요\n{res.text[:300]}")
i_tm, i_avg = cols.index("TM"), cols.index("TA_AVG")
i_max, i_min = cols.index("TA_MAX"), cols.index("TA_MIN")

# 4) 데이터 줄 파싱 → 결측(-9 계열)은 건너뜀(다음 실행 때 재시도)
rows = []
for ln in lines:
    if ln.startswith("#") or not ln.strip():
        continue
    p = ln.split()
    tm, avg, tmax, tmin = p[i_tm], p[i_avg], p[i_max], p[i_min]
    if any(float(v) <= -90 for v in (avg, tmax, tmin)):         # 미확정/결측
        print("결측 건너뜀:", tm)
        continue
    d = f"{tm[:4]}-{tm[4:6]}-{tm[6:8]}"
    rows.append(f"{d},{STN},{avg},{tmin},{tmax}")               # 평균,최저,최고 순서 주의

# 5) append 저장 (파일 끝에 줄바꿈 없으면 먼저 보정)
if rows:
    with open(CSV, "rb") as f:
        f.seek(-1, 2)
        needs_nl = f.read(1) != b"\n"
    with open(CSV, "a", encoding="utf-8") as f:
        if needs_nl:
            f.write("\n")
        f.write("\n".join(rows) + "\n")
print(f"{start}~{end} 구간 · {len(rows)}일 추가 · 마지막 {rows[-1].split(',')[0] if rows else last}")
