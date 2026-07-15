# 행안부 연령별 주민등록 인구로 population_latest.csv 자동 최신화 (4·8·11장 데이터)
# GitHub Actions가 매월 1일 자정(KST) 실행 → '지난달' 전국 데이터를 내려받아
#   · data/population_latest.csv   : 항상 최신 월 (고정 파일명 — 강의·교재가 참조)
#   · data/archive/population_YYYY_MM.csv : 월별 스냅샷 보관
# 원본 형식 유지: cp949 인코딩 · 천단위 쉼표 · 합계행 포함 (교재의 '전처리 배우기' 소재 그대로)
# 이미 최신이면 아무것도 안 함(멱등) → 1일 실패 시 2일 재시도가 안전하게 동작
#
# ⚠️ 초안 주의: FORM 파라미터는 jumin.mois.go.kr 이 브라우저에서 쓰는 값을 그대로 재현한 것.
#    사이트 개편 시 깨질 수 있으니, 첫 가동 전에 브라우저 개발자도구(Network 탭)에서
#    'CSV 다운로드' 클릭 시의 실제 요청(downloadCsvAge.do)의 Form Data 와 대조해 확인할 것.
import os
import shutil
from datetime import datetime, timedelta, timezone

import requests

CSV = "data/population_latest.csv"
KST = timezone(timedelta(hours=9))

# 1) 대상 월 = 지난달 (행안부는 매월 1일에 전월 통계 공개)
today = datetime.now(KST).date()
target = today.replace(day=1) - timedelta(days=1)          # 지난달 말일
ym = target.strftime("%Y%m")                               # 예: 202606
label = f"{target.year}년{target.month:02d}월"             # CSV 헤더에 박히는 문자열

# 2) 멱등 검사 — 이미 지난달 데이터면 종료 (재시도 실행이 중복 커밋을 안 만들게)
if os.path.exists(CSV):
    with open(CSV, encoding="cp949", errors="ignore") as f:
        if label in f.readline():
            print(f"이미 최신 ({label}) · 갱신 불필요")
            raise SystemExit(0)

# 3) 행안부 주민등록 인구통계에서 CSV 다운로드 (전국 · 연령별 · 계)
URL = "https://jumin.mois.go.kr/downloadCsvAge.do"
FORM = {                                                    # ⚠️ 브라우저 실제 요청과 대조 필요
    "searchYearMonth": "month",
    "searchYearStart": str(target.year), "searchMonthStart": f"{target.month:02d}",
    "searchYearEnd": str(target.year),   "searchMonthEnd": f"{target.month:02d}",
    "sltOrgType": "1",                                      # 전국
    "sltOrgLvl1": "A", "sltOrgLvl2": "A",
    "gender": "N",                                          # 계(남녀 합계)
    "sltUndefType": "N",
    "xlsStats": "1",
}
res = requests.post(URL, data=FORM, timeout=60,
                    headers={"Referer": "https://jumin.mois.go.kr/ageStatMonth.do"})
res.raise_for_status()

# 4) 검증 — 대상 월 문자열이 헤더에 있고 행 수가 그럴듯해야만 저장
text = res.content.decode("cp949", errors="ignore")
n_lines = text.count("\n")
if label not in text[:500] or n_lines < 1000:
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
