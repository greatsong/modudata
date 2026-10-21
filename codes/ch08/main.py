"""8장 서울 실시간 혼잡도 - 서울 실시간 도시데이터 API로 121곳의 혼잡도와 연령대 비율을 지도에 표시한다.

실행 조건: 스트림릿 클라우드 [Settings] - [Secrets]에 SEOUL_KEY 등록
"""
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="서울혼잡도", page_icon="🗺️", layout="wide")

KST = timezone(timedelta(hours=9))
BASE_URL = "http://openapi.seoul.go.kr:8088"
AREA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul_area_all.csv"
FONT = "Apple SD Gothic Neo, Malgun Gothic, sans-serif"
CACHE_SECONDS = 300      # 한 번 받은 결과를 기억하는 시간(5분)
INTERVAL = 0.2           # 요청 사이의 간격(초)
TIMEOUT = 10             # 요청 하나에 허용하는 시간(초)

LEVEL_ORDER = ["여유", "보통", "약간 붐빔", "붐빔"]
LEVEL_COLOR = {"여유": "#2ca02c", "보통": "#bcbd22", "약간 붐빔": "#ff7f0e", "붐빔": "#d62728"}
AGE_COLUMNS = {
    "10대 미만": "PPLTN_RATE_0", "10대": "PPLTN_RATE_10", "20대": "PPLTN_RATE_20",
    "30대": "PPLTN_RATE_30", "40대": "PPLTN_RATE_40", "50대": "PPLTN_RATE_50",
    "60대": "PPLTN_RATE_60", "70대 이상": "PPLTN_RATE_70",
}

st.title("서울 실시간 혼잡도")

# ---------- 인증키 ----------
try:
    KEY = str(st.secrets.get("SEOUL_KEY", "")).strip()
except Exception:          # 비밀 정보 파일이 아예 없을 때
    KEY = ""
if not KEY:
    st.error("서울 열린데이터광장 인증키(SEOUL_KEY)가 없습니다.")
    st.markdown(
        """
**등록 방법**
1. https://data.seoul.go.kr 에 로그인한 뒤 [Open API] - [인증키 신청]에서 키를 발급받습니다.
2. 스트림릿 클라우드 앱의 [Settings] - [Secrets]에 다음 한 줄을 추가하고 저장합니다.

```
SEOUL_KEY = "발급받은 인증키"
```

3. 내 컴퓨터에서 실행할 때는 앱 폴더의 `.streamlit/secrets.toml` 파일에 같은 줄을 적습니다.
"""
    )
    st.stop()


# ---------- 데이터 불러오기 ----------
@st.cache_data(ttl=CACHE_SECONDS)
def load_areas() -> pd.DataFrame:
    areas = pd.read_csv(AREA_URL, dtype={"코드": str})
    areas.columns = [c.strip().lstrip("﻿") for c in areas.columns]
    return areas


@st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)
def fetch_one(area_name: str) -> tuple[dict, str]:
    """장소 하나의 실시간 인구 항목(LIVE_PPLTN_STTS)과 받은 시각을 돌려준다.
    실패하면 예외를 일으켜 결과를 기억하지 않는다(다음 조회 때 다시 시도)."""
    url = f"{BASE_URL}/{KEY}/json/citydata/1/5/{area_name}"
    res = requests.get(url, timeout=TIMEOUT)
    res.raise_for_status()
    stts = res.json().get("CITYDATA", {}).get("LIVE_PPLTN_STTS")
    if not stts:
        raise ValueError("응답에 실시간 인구 항목이 없습니다")
    time.sleep(INTERVAL)   # 요청 사이의 간격(기억한 결과를 쓸 때는 쉬지 않는다)
    return stts[0], datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def fetch_all(areas: pd.DataFrame, progress) -> tuple[pd.DataFrame, list[str], str]:
    """121곳을 차례대로 조회한다. 결과 표, 실패한 장소 이름, 불러온 시각을 돌려준다."""
    rows, failed, times = [], [], []
    total = len(areas)
    for i, area in enumerate(areas.itertuples(index=False), start=1):
        try:
            item, at = fetch_one(area.지역명)
        except (requests.RequestException, ValueError):
            failed.append(area.지역명)
        else:
            times.append(at)
            row = {
                "코드": area.코드, "지역명": area.지역명, "분류": area.분류,
                "위도": area.위도, "경도": area.경도,
                "혼잡도": item.get("AREA_CONGEST_LVL"),
                "인구min": pd.to_numeric(item.get("AREA_PPLTN_MIN"), errors="coerce"),
                "인구max": pd.to_numeric(item.get("AREA_PPLTN_MAX"), errors="coerce"),
                "비상주율": pd.to_numeric(item.get("NON_RESNT_PPLTN_RATE"), errors="coerce"),
                "기준시각": item.get("PPLTN_TIME") or "확인할 수 없음",
            }
            for label, field in AGE_COLUMNS.items():
                row[label] = pd.to_numeric(item.get(field), errors="coerce")
            rows.append(row)
        progress.progress(i / total, text=f"조회 중 {i}/{total}")
    fetched_at = max(times) if times else "-"
    return pd.DataFrame(rows), failed, fetched_at


try:
    areas = load_areas()
except Exception as err:
    st.error(f"장소 목록을 불러오지 못했습니다: {type(err).__name__}")
    st.stop()

progress_box = st.empty()
df, failed, fetched_at = fetch_all(areas, progress_box.progress(0.0, text="조회 준비"))
progress_box.empty()

# ---------- 요약 ----------
st.caption(f"데이터를 불러온 시각: {fetched_at} (한 번 받은 결과는 {CACHE_SECONDS // 60}분 동안 다시 요청하지 않습니다)")
c1, c2, c3 = st.columns(3)
c1.metric("조회 대상", f"{len(areas)}곳")
c2.metric("조회 성공", f"{len(df)}곳")
c3.metric("조회 실패", f"{len(failed)}곳")
if failed:
    with st.expander("불러오지 못한 장소"):
        st.write(", ".join(failed))
if df.empty:
    st.error("조회에 성공한 장소가 없습니다. 인증키와 네트워크 상태를 확인합니다.")
    st.stop()

df = df.copy()
df["인구 범위"] = df["인구min"].map("{:,.0f}".format) + " ~ " + df["인구max"].map("{:,.0f}".format) + "명"
df["혼잡도"] = pd.Categorical(df["혼잡도"], categories=LEVEL_ORDER)

# ---------- 분류 체크박스 ----------
st.subheader("분류 선택")
categories = list(areas["분류"].drop_duplicates())
cols = st.columns(len(categories))
picked = [c for c, col in zip(categories, cols) if col.checkbox(c, value=True, key=f"cat_{c}")]
shown = df[df["분류"].isin(picked)]
if shown.empty:
    st.info("분류를 하나 이상 고르면 지도에 표시됩니다.")
    st.stop()

# ---------- 지도 1: 혼잡도 ----------
st.subheader("현재 혼잡도 지도")
fig1 = px.scatter_map(
    shown, lat="위도", lon="경도", color="혼잡도", size="인구max", size_max=28,
    color_discrete_map=LEVEL_COLOR, category_orders={"혼잡도": LEVEL_ORDER},
    hover_name="지역명", hover_data={"분류": True, "혼잡도": True, "인구 범위": True,
                                   "비상주율": ":.1f", "기준시각": True,
                                   "위도": False, "경도": False, "인구max": False},
    zoom=10.3, center={"lat": 37.55, "lon": 126.98}, height=620, map_style="open-street-map",
)
fig1.update_layout(font_family=FONT, margin=dict(l=0, r=0, t=0, b=0), legend_title_text="혼잡도")
st.plotly_chart(fig1, width="stretch")
st.caption(f"조회 시각 {fetched_at} 기준. 점의 크기는 실시간 인구 최댓값에 비례합니다.")

# ---------- 청년 비율 ----------
st.subheader("20~30대 비율 지도")
df["청년 비율"] = df["20대"] + df["30대"]
bad_ratio = int(df["청년 비율"].isna().sum())
st.caption(f"청년 비율 = 20대 비율 + 30대 비율. 비율을 숫자로 바꾸지 못한 장소: {bad_ratio}곳")
shown2 = df[df["분류"].isin(picked) & df["청년 비율"].notna()]
fig2 = px.scatter_map(
    shown2, lat="위도", lon="경도", color="청년 비율", size="인구max", size_max=28,
    color_continuous_scale="Viridis",
    hover_name="지역명", hover_data={"분류": True, "청년 비율": ":.1f", "인구 범위": True,
                                   "위도": False, "경도": False, "인구max": False},
    zoom=10.3, center={"lat": 37.55, "lon": 126.98}, height=620, map_style="open-street-map",
)
fig2.update_layout(font_family=FONT, margin=dict(l=0, r=0, t=0, b=0),
                   coloraxis_colorbar=dict(title="청년 비율(%)"))
st.plotly_chart(fig2, width="stretch")

# ---------- 연령대 구성 비교 ----------
st.subheader("연령대 구성 비교")
valid = df.dropna(subset=list(AGE_COLUMNS))
valid = valid.assign(**{"60대 이상": valid["60대"] + valid["70대 이상"]})
top_young = valid.nlargest(6, "청년 비율")
top_old = valid.nlargest(6, "60대 이상")
age_labels = list(AGE_COLUMNS)


def stacked_bar(sub: pd.DataFrame, title: str):
    long = sub.melt(id_vars="지역명", value_vars=age_labels, var_name="연령대", value_name="비율")
    fig = px.bar(
        long, x="지역명", y="비율", color="연령대", barmode="stack",
        category_orders={"연령대": age_labels, "지역명": list(sub["지역명"])},
        color_discrete_sequence=px.colors.qualitative.Set2,
        hover_data={"지역명": True, "연령대": True, "비율": ":.1f"},
        title=title, height=480,
    )
    fig.update_layout(font_family=FONT, xaxis_title="", yaxis_title="비율(%)",
                      yaxis_range=[0, 100], legend_title_text="연령대",
                      margin=dict(l=10, r=10, t=60, b=10))
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: %{y:.1f}%<extra></extra>")
    return fig


left, right = st.columns(2)
with left:
    st.plotly_chart(stacked_bar(top_young, f"청년 비율 상위 6곳 ({fetched_at})"), width="stretch")
with right:
    st.plotly_chart(stacked_bar(top_old, f"60대 이상 비율 상위 6곳 ({fetched_at})"), width="stretch")

with st.expander("조회 결과 표"):
    st.dataframe(
        df[["지역명", "분류", "혼잡도", "인구min", "인구max", "청년 비율", "60대", "70대 이상", "비상주율", "기준시각"]]
        .sort_values("인구max", ascending=False),
        hide_index=True, width="stretch",
    )
