# 서울열린데이터광장 API로 지하철 월별 승하차 2종 자동 최신화 (5장 데이터)
# GitHub Actions가 매월 초 실행 → 마지막 수록 월 다음 달부터 공개된 달까지 전부 추가 (백필)
#   · subway_pay.csv  : 유·무임 승하차 (CardSubwayPayFree)
#   · subway_time.csv : 시간대별 승하차 (CardSubwayTime)
# 형식 유지: utf-8 · 전체 따옴표 · 최신 월이 위(내림차순) · API 필드 순서 = CSV 컬럼 순서(1:1)
# 이미 최신이면 아무것도 안 함(멱등) · 시크릿 SEOUL_KEY 필요
import csv
import io
import os

import requests

KEY = os.environ["SEOUL_KEY"]              # 키는 코드 밖, GitHub 시크릿에서
BASE = "http://openapi.seoul.go.kr:8088"
TARGETS = [
    ("CardSubwayPayFree", "data/subway_pay.csv"),
    ("CardSubwayTime", "data/subway_time.csv"),
]


def next_month(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[4:])
    return f"{y + m // 12}{m % 12 + 1:02d}"


def fetch_month(service: str, ym: str) -> list[list[str]]:
    """한 달치 전체 행을 API 필드 순서 그대로 반환 (없으면 빈 리스트)"""
    rows, start = [], 1
    while True:
        url = f"{BASE}/{KEY}/json/{service}/{start}/{start + 999}/{ym}"
        d = requests.get(url, timeout=60).json()
        if service not in d:                       # INFO-200 = 해당 월 데이터 없음
            return []
        total = d[service]["list_total_count"]
        for r in d[service]["row"]:
            # 숫자는 float로 오므로 정수로, 문자열은 그대로 (필드 순서 = CSV 컬럼 순서)
            rows.append([str(int(v)) if isinstance(v, float) else str(v) for v in r.values()])
        if start + 999 >= total:
            return rows
        start += 1000


for service, path in TARGETS:
    with open(path, encoding="utf-8-sig") as f:
        header = f.readline()
        body = f.read()
    latest = body[: body.find("\n")].split(",")[0].strip('"')   # 첫 데이터 행 = 최신 월

    new_rows, ym = [], next_month(latest)
    while True:                                    # 공개된 달까지 계속 (백필)
        month_rows = fetch_month(service, ym)
        if not month_rows:
            break
        print(f"{service} · {ym} · {len(month_rows)}행")
        new_rows = month_rows + new_rows           # 더 최신 달이 위로
        ym = next_month(ym)

    if not new_rows:
        print(f"{service} · 이미 최신 ({latest})")
        continue

    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(new_rows)
    with open(path, "w", encoding="utf-8") as f:   # 내림차순 유지: 헤더 → 새 달 → 기존
        f.write(header + buf.getvalue() + body)
    print(f"{path} 갱신 완료")
