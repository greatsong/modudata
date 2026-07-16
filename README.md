# modudata — 『모두의 데이터 분석 with AI』 공개 예제 데이터

교재 실습에 쓰는 **모든 데이터를 한곳에** 모았습니다. 전부 공개 개방 데이터이고, raw URL로 바로 읽어 쓸 수 있어요.

```
https://raw.githubusercontent.com/greatsong/modudata/main/data/<파일명>
```

---

## ⚡ 바로 쓰기 — 인코딩은 "유연하게"

관공서 데이터는 파일마다 인코딩이 **cp949**일 때도, **utf-8**일 때도 있고, **언제든 바뀔 수 있습니다.** 그래서 하나로 못 박지 말고 아래처럼 **유연하게** 읽으세요. (AI에게 시킬 땐 "인코딩은 utf-8이 안 되면 cp949로, 유연하게 읽어줘"라고 부탁하면 됩니다.)

```python
import pandas as pd

BASE = "https://raw.githubusercontent.com/greatsong/modudata/main/data"

def read_csv_flex(url, **kw):
    """utf-8로 먼저, 안 되면 cp949로 — 인코딩이 바뀌어도 안 깨짐"""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(url, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(url, encoding="utf-8", encoding_errors="replace", **kw)

temp = read_csv_flex(f"{BASE}/seoul.csv")                              # 기온
pop  = read_csv_flex(f"{BASE}/population_latest.csv", thousands=",")   # 인구(천단위 쉼표, 매월 자동 갱신)
```

> 💡 급하면 `pd.read_csv(url)` → 에러 나면 `encoding="cp949"` 한 줄만 붙여도 됩니다.

---

## 📂 한눈에 보기

| 파일 | 쓰는 곳 | 인코딩(현재) | 크기 | 무엇 |
|---|---|---|---|---|
| `seoul.csv` | 3·8장 | utf-8 (원본 cp949) | 1.2 MB | 서울 100년치 일별 기온 · **매일 자동 갱신** |
| `population_2026_05.csv` | 11장 | **cp949** | 6.2 MB | 연령별 주민등록 인구 (2026년 5월 스냅샷 — 11장 결과 재현용) |
| `population_latest.csv` | 4·8장 | **cp949** | 6.2 MB | 연령별 주민등록 인구 · **매월 1일 자동 갱신** (강의용, 항상 최신 월) |
| `subway_pay.csv` | 5장 | utf-8 (원본 cp949) | 5.5 MB | 지하철 유·무임 승하차(월별) |
| `subway_time.csv` | 5장 | utf-8 (원본 cp949) | 29 MB | 지하철 시간대별 승하차(월별) |
| `hangjeongdong.geojson` | 4·5장 | utf-8 | 33 MB | 전국 행정동 경계 |
| `dong_centroids.csv` | 11장 | utf-8 | 230 KB | 행정동 중심점 좌표 |
| `seoul_area_xy.csv` | 6·10장 | utf-8 | 1.6 KB | 서울 주요 명소 23곳 좌표 |
| `kobis.csv` | 8장 | utf-8 | 30 KB | 영화 박스오피스 · **매일 자동 갱신** |
| `seoul_congestion_log.csv` | 10장 | utf-8 | 260 KB | 서울 실시간 혼잡도 로그 · **매시간 자동 수집** |

보조·검증용: `seoul_daily/monthly/yearly.csv`(기온 집계본) · `mnist_small.npz`(손글씨) · `stars_검증데이터.csv` · `kobis_영화흥행_검증데이터.csv` · `seoul_yearly_real_검증데이터.csv`

> 인코딩 표기는 "현재 저장소 복사본" 기준입니다. **원본을 직접 받으면 cp949인 경우가 많고, 갱신·재저장 과정에서 바뀔 수 있습니다.** 그래서 위 `read_csv_flex`처럼 읽는 걸 권장합니다.

---

## 📜 원 출처 (반드시 확인)

이 저장소의 데이터는 아래 **공식 원 출처**에서 받아 실습용으로 정리·재배포한 것입니다. 파생 파일(직접 만든 것)은 어떤 원천에서 나왔는지도 함께 밝힙니다.

| 데이터 | 원 출처 (제공 기관) | 원천 포털 / 링크 |
|---|---|---|
| `seoul.csv` (+ 집계본 `seoul_daily/monthly/yearly`) | **기상청** — 종관기상관측(ASOS) 일자료 | 기상자료개방포털 [data.kma.go.kr](https://data.kma.go.kr) |
| `population_2026_05.csv`, `population_latest.csv` | **행정안전부** — 주민등록 인구통계(연령별 인구현황) | [jumin.mois.go.kr](https://jumin.mois.go.kr) |
| `subway_pay.csv`, `subway_time.csv` | **서울교통공사** 제공, **서울특별시** 배포 | 서울 열린데이터광장 [data.seoul.go.kr](https://data.seoul.go.kr) |
| `hangjeongdong.geojson` | **vuski/admdongkor** (행정동 경계, **통계청** 통계지리정보 기반) | [github.com/vuski/admdongkor](https://github.com/vuski/admdongkor) |
| `dong_centroids.csv` | *파생* — 위 `hangjeongdong.geojson`(vuski/admdongkor)에서 각 동 중심점 계산 | (파생물) |
| `seoul_area_xy.csv` | *파생* — **서울특별시** 실시간 도시데이터(citydata) 주요 명소 좌표 | 서울 열린데이터광장 [data.seoul.go.kr](https://data.seoul.go.kr) |
| `kobis.csv` | **영화진흥위원회(KOFIC)** — 영화관입장권 통합전산망 일별 박스오피스 | KOBIS Open API [kobis.or.kr](https://www.kobis.or.kr/kobisopenapi) |
| `seoul_congestion_log.csv` | **서울특별시** — 실시간 도시데이터(citydata_ppltn) | 서울 열린데이터광장 [data.seoul.go.kr](https://data.seoul.go.kr) |

**API로 받는 데이터의 원 출처**: 야후 파이낸스(yfinance)·**Google**(YouTube Data API, Gemini)·**영화진흥위원회**(KOBIS)·**서울특별시**(실시간 도시데이터)·**행정안전부**(공공데이터포털 data.go.kr, 제공기관은 데이터별 상이)·**카카오**(로컬 API)·**GBIF**·**NASA**·**USGS**. 발급·엔드포인트는 아래 [API 데이터](#-api-데이터--키-획득-방법) 표 참고.

> 대부분 **공공누리(출처표시)** 계열의 공개 데이터입니다. 정확한 이용조건·라이선스는 각 포털의 표기를 확인하세요. `seoul_daily/monthly/yearly`·`mnist_small.npz`·`stars_검증데이터.csv` 등은 교재 본문에 쓰이지 않는 **보조·실험용**입니다.

---

## 📄 파일 데이터 — 출처 · 수집 경로 · 주의사항

교재는 실습 편의를 위해 **원본을 짧은 파일명으로 바꿔** 이 저장소에 올려 두었습니다. "직접 받는 법"과 "교재에서 쓰는 이름"을 함께 적었어요.

### `seoul.csv` — 서울 100년치 일별 기온
- **출처**: 기상청 **기상자료개방포털** ([data.kma.go.kr](https://data.kma.go.kr)) · 지상 → 종관기상관측(ASOS) 일자료 · 지점 **서울(108)**
- **직접 받으면**: 조회조건 기반의 긴 한글 파일명 · **원본 인코딩은 보통 cp949(EUC-KR)** · 교재는 `seoul.csv`로 정리(현재 저장소 복사본은 utf-8) → *그래서 유연 읽기 권장*
- **열**: `날짜, 지점, 평균기온, 최저기온, 최고기온` (약 42,937행, 1907.10~)
- **주의**: 평균기온 결측 약 756개(특히 1950~53 전쟁기) · `날짜`는 `pd.to_datetime`으로 변환

### `population_2026_05.csv` — 연령별 주민등록 인구
- **출처**: 행정안전부 **주민등록 인구통계** ([jumin.mois.go.kr](https://jumin.mois.go.kr)) · [연령별 인구현황] → 지역 **전국** · 시점 **2026년 5월** · **읍면동** · **1세 단위** → CSV
- **직접 받으면**: 보통 한글 데이터셋 이름(예: `연령별인구현황…csv`, 조회조건·날짜 포함) · **cp949 인코딩** · 교재는 `population_2026_05.csv`로
- **주의(전처리 포인트)**:
  - **천 단위 쉼표**(`9,295,082`) → `thousands=","`
  - **합계 행 혼입**(`서울특별시`, `서울특별시 종로구` 등 시·도/시·군·구 행) → 읍·면·동만 남기기
  - 인구 0인 행정용 행 제거
  - **긴 열 이름**(`2026년05월_계_0세` → `0세`) 정리
  - 다른 표와 합칠 땐 **이름 아닌 행정구역 코드**(괄호 속 숫자, 예 `1168060000`)로
  - 원본 (3,918행, 310열) → 정리 후 읍·면·동 약 3,558곳

### `subway_pay.csv` / `subway_time.csv` — 지하철 승하차
- **출처**: 서울 **열린데이터광장** ([data.seoul.go.kr](https://data.seoul.go.kr)) · 검색 '지하철' → **유·무임 승하차** / **시간대별 승하차** → CSV
- **직접 받으면**: 데이터셋 한글명 CSV · **원본 cp949**(저장소 복사본은 utf-8) · 교재는 `subway_pay.csv` / `subway_time.csv`로
- **주의**: 월별(2015.1~2026.5) · **서울 1~9호선만** 필터(그 외 노선은 집계 방식이 달라 섞으면 안 됨) · '같은 이름 다른 호선'(시청·종로3가) · `subway_time`은 시간대가 열로 넓게 → `melt`로 긴 형태 변환

### `hangjeongdong.geojson` — 전국 행정동 경계
- **출처**: 예제 저장소 제공 · 원본은 GitHub **`vuski/admdongkor`**(전국 행정동 경계)
- **주의**: 단계구분도용 · 인구표와 짝지을 땐 `properties`의 **행정구역 코드**로 매칭(이름 X)

### `dong_centroids.csv` — 행정동 중심점 좌표
- **출처**: *파생물* · 원 출처는 `hangjeongdong.geojson`(**vuski/admdongkor**, 통계청 기반) — 각 동 경계의 중심점을 계산
- **열**: `코드, lat, lon` (3,558행) · **주의**: 인구표의 행정구역 코드와 **`코드`로 병합**(이름으로 하면 절반만 매칭)

### `seoul_area_xy.csv` — 서울 주요 명소 23곳 좌표
- **출처**: *파생물* · 원 출처는 **서울특별시** 실시간 도시데이터(citydata, 서울 열린데이터광장)의 주요 명소 좌표를 정리
- **열**: `코드(POI…), 지역명, 위도, 경도` (+ 예시 스냅샷 열) · 서울 혼잡도 API 응답과 지역명/코드로 merge

### `kobis.csv` — 영화 박스오피스 (🔄 매일 자동 갱신)
- **출처**: KOBIS 일별 박스오피스 API로 축적(아래 '자동 갱신')
- **열**: `영화명, 개봉일, 스크린수, 상영횟수, 순위, 관객수, 최종관객` · **주의**: 최종관객은 수십 배 편차 → `log1p` 변환 권장 · '열기'(관객수 ÷ 상영횟수) 특성 만들기

### `seoul_congestion_log.csv` — 서울 실시간 혼잡도 로그 (🔄 매시간 자동 수집)
- **출처**: 서울 실시간 도시데이터 API를 GitHub Actions가 매시간 append(아래 '자동 갱신')
- **열**: `시각, 코드, 지역명, 혼잡도, 인구min, 인구max, 위도, 경도` · **주의**: 빈 시각 생길 수 있음(직전 값으로 채우기) · 앱에서 읽을 때 `ttl=0`

---

## 🔑 API 데이터 — 키 획득 방법

파일이 아니라 **실시간으로 받아오는** 데이터입니다. 키가 필요한 건 아래 방법으로 무료 발급(결제정보 불필요), **키는 코드에 쓰지 말고 `secrets`에**.

| API | 챕터 | 키 | 발급 방법 (secrets 변수명) |
|---|---|---|---|
| yfinance (주가) | 2장 | 불필요 | 라이브러리(`pip install yfinance`) · `005930.KS`(한국)·`AAPL`(미국) |
| catfact.ninja / randomuser.me | 6장 | 불필요 | 연습용 · `https://catfact.ninja/fact`, `https://randomuser.me/api/` |
| **YouTube Data API v3** | 6·7장 | 필요 | [console.cloud.google.com](https://console.cloud.google.com) → 새 프로젝트 → 라이브러리에서 'YouTube Data API v3' 사용 설정 → 사용자 인증정보 → API 키. **`YOUTUBE_API_KEY`** (6·7장 재사용) |
| **KOBIS 일별 박스오피스** | 6장 | 필요 | [kobis.or.kr/kobisopenapi](https://www.kobis.or.kr/kobisopenapi) → [키 발급/관리]. **`KOBIS_KEY`** · 엔드포인트 `…/rest/boxoffice/searchDailyBoxOfficeList.json?key=&targetDt=YYYYMMDD` |
| **서울 실시간 도시데이터** | 6·10장 | 필요 | [data.seoul.go.kr](https://data.seoul.go.kr) → [Open API] → [인증키 신청]. **`SEOUL_KEY`** · `http://openapi.seoul.go.kr:8088/{KEY}/json/citydata_ppltn/1/5/{지역코드}` |
| **Gemini** | 7장 | 필요 | [aistudio.google.com](https://aistudio.google.com) → Get API key(2단계). **`GEMINI_API_KEY`** · 모델 `gemini-2.5-flash` |
| **공공데이터포털** | 부록 | 필요 | [data.go.kr](https://www.data.go.kr) 가입 → 활용신청 → 마이페이지에서 serviceKey. 인코딩/디코딩 키 2종·`_type=json`·호출한도 주의 |
| **카카오 로컬(지오코딩)** | 부록 | 필요 | [developers.kakao.com](https://developers.kakao.com) → 앱 → **REST API 키**. **`KAKAO_KEY`** · 헤더 `Authorization: KakaoAK {키}` |
| GBIF / NASA NeoWs / USGS | 부록 | GBIF·USGS 불필요 / NASA 권장 | NASA: [api.nasa.gov](https://api.nasa.gov)에서 무료 키(→ `st.secrets`) |

---

## 🔄 자동 갱신 (GitHub Actions)

아래 데이터는 매번 직접 안 모아도 되게 **자동으로 최신화**됩니다. (워크플로 파일은 `.github/workflows/`에 포함 — 각 시크릿을 등록해야 동작합니다.)

- **`kobis.csv`** — 매일 '어제' 박스오피스 TOP10 반영(새 영화 추가 + 최종관객 갱신) · 시크릿 `KOBIS_KEY` · 스크립트 `scripts/update_kobis.py`
- **`seoul_congestion_log.csv`** — 매시간 서울 혼잡도 append · 시크릿 `SEOUL_KEY` · 스크립트 `scripts/collect_seoul.py`
- **`seoul.csv`** — 매일 아침(KST 07시) 빠진 날짜를 어제까지 백필 · 시크릿 `KMA_KEY`(기상청 API허브) · 스크립트 `scripts/update_seoul_temp.py`
- **`population_latest.csv`** — 매월 1일 자정(KST) 지난달 데이터로 교체, 실패 시 2일 재시도 · 시크릿 불필요 · 스크립트 `scripts/update_population.py` (월별 스냅샷은 `data/archive/`)
- **`subway_pay.csv` / `subway_time.csv`** — 매월 5일(재시도 9일) 새벽 공개된 달을 append · 시크릿 `SEOUL_KEY` · 스크립트 `scripts/update_subway.py`
- `seoul.csv` 갱신 시 파생 파일(`seoul_daily.csv`·`seoul_yearly.csv`)도 자동 재생성됩니다.

시크릿 추가: 저장소 **Settings → Secrets and variables → Actions → New repository secret**.

---

*원본은 모두 공개 개방 데이터입니다(기상청·행정안전부·서울 열린데이터광장·영화진흥위원회 등). 실습·학습용으로 정리해 재배포합니다.*
