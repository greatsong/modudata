# 매시간 임시 파일에 모은 혼잡도 기록을 하루 한 번 본 파일(data/seoul_congestion_log.csv)에 합친다
# 사용: python scripts/flush_congestion.py <임시 파일>
# 합친 뒤 임시 파일은 머리줄만 남긴다(커밋·푸시가 성공한 뒤에 비우도록 워크플로가 --clear로 다시 부른다)
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
with open(pending, encoding="utf-8") as f:
    rows = [r for r in csv.reader(f) if r and r != HEADER]
if not rows:
    print("합칠 기록 없음"); sys.exit(0)
with open(target, "a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows(rows)
print("합친 줄", len(rows))
