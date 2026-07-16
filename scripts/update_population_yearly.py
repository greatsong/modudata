# 읍·면·동 '연도별'(매년 6월) 인구 시계열 자동 갱신 — 1세 단위 × 계·남·여
# population_yearly.csv.gz 에 없는 최신 연도(그해 6월)만 받아 append (키 불필요 · 공개 다운로드)
# 6월 데이터는 대략 7월 중순 공개 → 매년 7월 크론 실행. 실패해도 기존 데이터는 그대로, 다음 해 재시도.
import io, re, os
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd

CSV = "data/population_yearly.csv.gz"
URL = "https://jumin.mois.go.kr/downloadCsvAge.do?searchYearMonth=month&xlsStats=3"
KST = timezone(timedelta(hours=9))
PRE = re.compile(r"^\d{4}년\d{2}월_")

def fetch(y, m):
    s = requests.Session()
    s.get("https://jumin.mois.go.kr/ageStatMonth.do", headers={"User-Agent":"Mozilla/5.0"}, timeout=30)
    DATA = {"sltOrgType":"1","sltOrgLvl1":"A","sltOrgLvl2":"A",
            "searchYearStart":str(y),"searchMonthStart":f"{m:02d}",
            "searchYearEnd":str(y),"searchMonthEnd":f"{m:02d}",
            "sltOrderType":"1","sltOrderValue":"ASC","sltArgTypes":"1","sltArgTypeA":"0",
            "sltArgTypeB":"100","sum":"sum","gender":"gender","sltUndefType":"","category":"month","state":"3"}
    r = s.post(URL, data=DATA, timeout=180,
               headers={"User-Agent":"Mozilla/5.0","Referer":"https://jumin.mois.go.kr/ageStatMonth.do"})
    r.raise_for_status(); return r.content

def clean(raw, year):
    p = pd.read_csv(io.BytesIO(raw), encoding="cp949", thousands=",")
    p["코드"] = p["행정구역"].str.extract(r"\((\d+)\)")
    p["행정구역"] = p["행정구역"].str.replace(r"\(\d+\)","",regex=True).str.strip()
    ren = {c: PRE.sub("", c) for c in p.columns
           if re.search(r"_(계|남|여)_", c) and "세" in PRE.sub("", c).split("_")[-1]}
    p = p.rename(columns=ren); agecols = list(ren.values())
    gye = [c for c in agecols if c.startswith("계_")]
    p = p[p["행정구역"].str.endswith(("읍","면","동"))]
    p = p[p[gye].sum(axis=1) > 0].copy()
    parts = p["행정구역"].str.split(" ", n=1, expand=True)
    p["연도"]=year; p["시도"]=parts[0]; p["시군구"]=parts[1].str.split(" ").str[0]
    p["동"]=p["행정구역"].str.split(" ").str[-1]
    return p[["연도","시도","시군구","동","코드"]+agecols]

old = pd.read_csv(CSV)                                  # gz 자동 해제
present = set(old["연도"])
now = datetime.now(KST)
latest = now.year if now.month >= 7 else now.year - 1   # 그해 6월은 ~7월 중순 공개
todo = [y for y in range(max(present)+1, latest+1)]
if not todo:
    print(f"이미 최신 (최신 연도 {max(present)}) · 갱신 불필요"); raise SystemExit(0)

adds = []
for y in todo:
    try:
        adds.append(clean(fetch(y, 6), y)); print(f"{y}-06 수집 · 추가")
    except Exception as e:
        print(f"{y}-06 실패({e}) · 다음 실행 때 재시도")
if not adds:
    raise SystemExit(0)

new = pd.concat([old]+adds, ignore_index=True).sort_values(["연도","코드"])
new.to_csv(CSV, index=False, encoding="utf-8", compression="gzip")
print(f"완료 · 연도 {sorted(set(new['연도']))} · 행 {len(new):,}")
