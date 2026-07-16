# 행안부 연령별 주민등록 인구로 population_latest.csv 자동 최신화 (4·8·11장 데이터)
# GitHub Actions가 매월 1일 자정(KST) 실행 → '지난달' 전국(읍면동 전체) 데이터를 내려받아
#   · data/population_latest.csv   : 항상 최신 월 (고정 파일명 — 강의·교재가 참조)
#   · data/archive/population_YYYY_MM.csv : 월별 스냅샷 보관
# 원본 형식 유지: cp949 인코딩 · 천단위 쉼표 · 1세 단위(0~100세) · 시도~읍면동 전체
# 이미 최신이면 아무것도 안 함(멱등) → 1일 실패 시 2일 재시도가 안전하게 동작
# 파라미터는 jumin.mois.go.kr 의 '전체읍면동현황(state=3) CSV 다운로드' 요청을 재현 (2026-07 검증)
import os
import shutil
from datetime import datetime, timedelta, timezone

import requests

CSV = "data/population_latest.csv"
KST = timezone(timedelta(hours=9))

# 1) 대상 월 = 지난달 (행안부는 매월 1일에 전월 통계 공개)
today = datetime.now(KST).date()
target = today.replace(day=1) - timedelta(days=1)          # 지난달 말일
label = f"{target.year}년{target.month:02d}월"             # CSV 헤더에 박히는 문자열

# 2) 멱등 검사 — 이미 지난달 데이터면 종료 (재시도 실행이 중복 커밋을 안 만들게)
if os.path.exists(CSV):
    with open(CSV, encoding="cp949", errors="ignore") as f:
        if label in f.readline():
            print(f"이미 최신 ({label}) · 갱신 불필요")
            raise SystemExit(0)

# 3) 행안부 주민등록 인구통계에서 CSV 다운로드
#    xlsStats=3 & state=3 = '전체읍면동현황' · sltArgTypes=1 = 1세 단위(0~100세) · sum = 연령구간 합계 포함
URL = "https://jumin.mois.go.kr/downloadCsvAge.do?searchYearMonth=month&xlsStats=3"
DATA = {
    "sltOrgType": "1", "sltOrgLvl1": "A", "sltOrgLvl2": "A",   # 전국
    "searchYearStart": str(target.year), "searchMonthStart": f"{target.month:02d}",
    "searchYearEnd": str(target.year),   "searchMonthEnd": f"{target.month:02d}",
    "sltOrderType": "1", "sltOrderValue": "ASC",
    "sltArgTypes": "1", "sltArgTypeA": "0", "sltArgTypeB": "100",
    "sum": "sum", "sltUndefType": "", "category": "month", "state": "3",
}
s = requests.Session()                                      # 세션 쿠키 필요 → 페이지 먼저 방문
s.get("https://jumin.mois.go.kr/ageStatMonth.do",
      headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
res = s.post(URL, data=DATA, timeout=180,
             headers={"User-Agent": "Mozilla/5.0",
                      "Referer": "https://jumin.mois.go.kr/ageStatMonth.do"})
res.raise_for_status()

# 4) 검증 — 대상 월이 헤더에 있고 행 수가 그럴듯해야만 저장 (읍면동 전체 ≈ 3,900행)
text = res.content.decode("cp949", errors="ignore")
n_lines = len(text.splitlines())
if label not in text[:500] or n_lines < 3000:
    raise SystemExit(
        f"다운로드 검증 실패 — {label} 데이터가 아직 없거나 형식이 다름 "
        f"(행 {n_lines}) · 다음 실행 때 재시도"
    )

# 5) 저장 — 원본 바이트 그대로(cp949 유지) + 월별 아카이브
with open(CSV, "wb") as f:
    f.write(res.content)
os.makedirs("data/archive", exist_ok=True)
shutil.copyfile(CSV, f"data/archive/population_{target.year}_{target.month:02d}.csv")
print(f"{label} 반영 · {n_lines}행 · latest + archive 저장 완료")
