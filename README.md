# modudata — 『모두의 데이터 분석 with AI』 공개 예제 데이터

교재 실습에 쓰는 공개 데이터 모음입니다. 원본은 모두 공공 개방 데이터예요.

- `data/seoul.csv` — 서울 100년치 일별 기온 (기상청)
- `data/population_2026_05.csv` — 연령별 주민등록 인구 (행정안전부)
- `data/kobis.csv` — 영화 박스오피스 (영화진흥위원회 KOBIS) · **매일 자동 최신화**
- `data/subway_*.csv` — 서울 지하철 승하차 (서울 열린데이터광장)
- `data/seoul_congestion_log.csv` — 서울 실시간 혼잡도 누적 로그 · **매시간 자동 수집**
- `data/hangjeongdong.geojson`, `data/dong_centroids.csv` — 행정동 경계·중심점
- 그 외 검증·보조 데이터

## 자동 갱신 (GitHub Actions)
- `update-kobis.yml` — 매일 어제 박스오피스를 `kobis.csv`에 반영 (`KOBIS_KEY` 시크릿 필요)
- `collect-seoul.yml` — 매시간 서울 혼잡도를 `seoul_congestion_log.csv`에 누적 (`SEOUL_KEY` 시크릿 필요)
