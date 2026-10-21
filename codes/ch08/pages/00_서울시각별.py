"""8장 서울 시각별 - 예제 저장소에 쌓아 둔 혼잡도 기록으로 장소별 시각별 평균 인구를 비교한다(인증키 불필요)."""
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="서울시각별", page_icon="⏰", layout="wide")

LOG_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul_congestion_log.csv"
FONT = "Apple SD Gothic Neo, Malgun Gothic, sans-serif"
DEFAULT_PLACE = "홍대입구역(2호선)"

st.title("서울 장소별 시각 비교")


@st.cache_data(ttl=3600)
def load_log() -> pd.DataFrame:
    df = pd.read_csv(LOG_URL, encoding="utf-8", dtype={"코드": str})
    df.columns = [c.strip().lstrip("﻿") for c in df.columns]
    return df


try:
    raw = load_log()
except Exception as err:
    st.error(
        f"기록을 불러오지 못했습니다({type(err).__name__}). "
        "인터넷 연결과 다음 주소가 열리는지 확인합니다."
    )
    st.code(LOG_URL)
    st.stop()

needed = {"시각", "코드", "지역명", "혼잡도", "인구min", "인구max", "위도", "경도"}
missing = needed - set(raw.columns)
if missing:
    st.error(f"기록에 필요한 열이 없습니다: {sorted(missing)}")
    st.stop()

df = raw.copy()
df["시각"] = pd.to_datetime(df["시각"], errors="coerce")
df["인구min"] = pd.to_numeric(df["인구min"], errors="coerce")
df["인구max"] = pd.to_numeric(df["인구max"], errors="coerce")
bad_time = int(df["시각"].isna().sum())
bad_pop = int(df["인구max"].isna().sum())
df = df.dropna(subset=["시각", "인구max"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("기록 시작", df["시각"].min().strftime("%Y-%m-%d"))
c2.metric("기록 마지막", df["시각"].max().strftime("%Y-%m-%d"))
c3.metric("장소 수", f"{df['지역명'].nunique()}곳")
c4.metric("전체 행 수", f"{len(raw):,}행")
st.caption(f"시각으로 바꾸지 못한 값 {bad_time}개, 인구로 바꾸지 못한 값 {bad_pop}개는 계산에서 제외했습니다.")

places = sorted(df["지역명"].dropna().unique())
default_index = places.index(DEFAULT_PLACE) if DEFAULT_PLACE in places else 0
place = st.selectbox("장소", places, index=default_index)

sub = df[df["지역명"] == place].copy()
sub["시"] = sub["시각"].dt.hour
sub["날"] = sub["시각"].dt.date

# 같은 장소·같은 시각의 기록이 중복되어 있는지 확인합니다.
dup = int(sub.duplicated(subset=["시각"]).sum())
if dup:
    sub = sub.drop_duplicates(subset=["시각"], keep="last")

hourly = (
    sub.groupby("시").agg(평균인구=("인구max", "mean"), 기록수=("인구max", "size"), 날짜수=("날", "nunique"))
    .reindex(range(24))
    .reset_index()
)
hourly["기록수"] = hourly["기록수"].fillna(0).astype(int)
hourly["날짜수"] = hourly["날짜수"].fillna(0).astype(int)
empty_hours = int(hourly["평균인구"].isna().sum())

fig = px.bar(
    hourly, x="시", y="평균인구",
    title=f"{place} 시각별 추정 인구 상한의 평균",
    height=460,
)
fig.update_traces(
    marker_color="#1f77b4",
    hovertemplate="%{x}시<br>추정 인구 상한의 평균 %{y:,.0f}명<br>기록 %{customdata[0]}건<br>관측 날짜 %{customdata[1]}일<extra></extra>",
    customdata=hourly[["기록수", "날짜수"]].to_numpy(),
)
fig.update_layout(
    font_family=FONT, xaxis_title="시각", yaxis_title="추정 인구 상한의 평균(명)",
    xaxis=dict(tickmode="array", tickvals=list(range(24)), ticktext=[f"{h}시" for h in range(24)]),
    margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig, width="stretch")

st.caption(
    f"{place}: 기록 {len(sub):,}건 "
    f"({sub['시각'].min():%Y-%m-%d} ~ {sub['시각'].max():%Y-%m-%d}). "
    f"기록이 하나도 없는 시각은 {empty_hours}개이며 그래프에서 비워 두었습니다. "
    f"시각마다 관측한 날짜 수는 {hourly['날짜수'].min()}일에서 {hourly['날짜수'].max()}일까지 다릅니다."
    + (f" 같은 시각의 중복 기록 {dup}건은 하나만 남겼습니다." if dup else "")
)
st.info("인구max는 실시간 인구 추정값의 상한입니다. 이 그래프는 남아 있는 기록만으로 계산한 추정 인구 상한의 평균이며, 기록이 빠진 시각이 있으므로 완전한 하루의 기록이 아닙니다.")
