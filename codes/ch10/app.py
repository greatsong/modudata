# 10장 앱 - 매시간 쌓인 혼잡도 기록을 읽는다 (키가 필요 없다)
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul_congestion_log.csv"
ORDER = ["여유", "보통", "약간 붐빔", "붐빔"]
COLOR = {"여유": "#2E9E5B", "보통": "#F4B400", "약간 붐빔": "#E8930C", "붐빔": "#D64545"}
LEVEL = {"여유": 0, "보통": 1, "약간 붐빔": 2, "붐빔": 3}
DAYS = ["월", "화", "수", "목", "금", "토", "일"]

st.set_page_config(page_title="서울의 일주일", layout="wide")
st.title("쌓인 기록으로 보는 서울")


@st.cache_data(ttl=600)                       # 새 줄이 곧 보이도록 10분만 기억한다
def load():
    df = pd.read_csv(URL)
    df = df.drop_duplicates(subset=["시각", "코드"], keep="last")   # 같은 시각 같은 장소는 한 줄만
    df["시각"] = pd.to_datetime(df["시각"])
    df["날짜"] = df["시각"].dt.date
    df["시"] = df["시각"].dt.hour
    df["요일"] = df["시각"].dt.dayofweek.map(lambda i: DAYS[i])
    df["주말"] = df["시각"].dt.dayofweek >= 5
    df["등급"] = df["혼잡도"].map(LEVEL)
    return df


df = load()
tab1, tab2 = st.tabs(["일주일의 리듬", "하루의 드라마"])

# ── 탭 ① 요일×시각 히트맵과 평일·주말 차이 ─────────────
with tab1:
    names = sorted(df["지역명"].dropna().unique())
    place = st.selectbox("장소", names, index=names.index("강남역") if "강남역" in names else 0)
    one = df[df["지역명"] == place]
    st.caption(f"{one['날짜'].min()} ~ {one['날짜'].max()} · {one['날짜'].nunique()}일치 기록")

    heat = one.pivot_table(index="요일", columns="시", values="등급", aggfunc="mean").reindex(DAYS)
    fig = px.imshow(heat, color_continuous_scale=["#2E9E5B", "#F4B400", "#E8930C", "#D64545"],
                    zmin=0, zmax=3, aspect="auto",
                    labels=dict(x="시각", y="", color="혼잡 등급"))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

    gap = (one[one["주말"]].groupby("시")["등급"].mean() - one[~one["주말"]].groupby("시")["등급"].mean()).reset_index(name="차이")
    bar = px.bar(gap, x="시", y="차이", labels={"차이": "주말 평균 − 평일 평균"},
                 color="차이", color_continuous_scale=["#2A78D6", "#DDDDDD", "#EB6834"], range_color=[-1.5, 1.5])
    bar.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
    st.plotly_chart(bar, width="stretch")

# ── 탭 ② 그날의 시각 슬라이더 지도 ─────────────────────
with tab2:
    dates = sorted(df["날짜"].unique())
    day = st.selectbox("날짜", dates, index=len(dates) - 1)
    one_day = df[df["날짜"] == day].copy()
    one_day["점크기"] = one_day["혼잡도"].map({"여유": 9, "보통": 13, "약간 붐빔": 19, "붐빔": 26}).fillna(9)
    one_day["시각표시"] = one_day["시"].map(lambda h: f"{h:02d}시")

    # 어떤 시각에는 네 등급이 다 나오지 않는다. 빈 행을 채워 슬라이더를 밀어도 점이 사라지지 않게 한다.
    blank = pd.DataFrame([{"시각표시": t, "혼잡도": c, "위도": np.nan, "경도": np.nan, "지역명": "", "점크기": 9}
                          for t in one_day["시각표시"].unique() for c in ORDER])
    frames = pd.concat([one_day, blank], ignore_index=True).sort_values(["시각표시", "혼잡도"])
    fig = px.scatter_map(frames, lat="위도", lon="경도", color="혼잡도", size="점크기", size_max=26,
                         animation_frame="시각표시", category_orders={"혼잡도": ORDER},
                         color_discrete_map=COLOR, hover_name="지역명",
                         center=dict(lat=37.55, lon=127.0), zoom=9.6, map_style="carto-positron")
    fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, width="stretch")
