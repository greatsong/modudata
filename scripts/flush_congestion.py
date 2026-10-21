# 매시간 임시 파일에 모은 혼잡도 기록을 하루 한 번 본 파일(data/seoul_congestion_log.csv)에 합친다
# 사용: python scripts/flush_congestion.py <임시 파일>          → 본 파일에 없는 (시각, 코드)만 덧붙인다(여러 번 돌려도 같은 결과)
#       python scripts/flush_congestion.py <임시 파일> --clear  → 임시 파일을 머리줄만 남기고 비운다
import csv, os, sys

pending = sys.argv[1]
target = "data/seoul_congestion_log.csv"
HEADER = ["시각", "코드", "지역명", "혼잡도", "인구min", "인구max", "위도", "경도"]

if "--clear" in sys.argv:
    with open(pending, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HEADER)
    print("임시 파일 비움")
    sys.exit(0)

if not os.path.exists(pending):
    print("임시 파일 없음"); sys.exit(0)
seen = set()
if os.path.exists(target):
    with open(target, encoding="utf-8") as f:
        for r in csv.reader(f):
            if len(r) >= 2: seen.add((r[0], r[1]))
new = []
with open(pending, encoding="utf-8") as f:
    for r in csv.reader(f):
        if not r or r == HEADER or len(r) < 2: continue
        if (r[0], r[1]) in seen: continue      # 이미 있는 시각·장소는 건너뜀
        seen.add((r[0], r[1])); new.append(r)
if not new:
    print("합칠 새 기록 없음"); sys.exit(0)
with open(target, "a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows(new)
print("합친 줄", len(new))
