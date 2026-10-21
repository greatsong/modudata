# 7장 1절 일별 박스오피스 - 순위표·당일 관객 수 그래프와 1위 영화 집중도 도넛
# KOBIS 오픈API 응답은 실행 중에만 사용합니다. 파일로 저장하거나 내려받게 하지 않습니다.
# 그래서 표는 내려받기 메뉴가 있는 st.dataframe 대신 정적 표(st.table)로 보여 줍니다.
# 실행 조건: 스트림릿 클라우드 [Settings] - [Secrets]에 KOBIS_KEY 등록
from datetime import datetime, timedelta, timezone

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DAILY_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
KST = timezone(timedelta(hours=9))   # 서버 시계가 UTC여도 한국 날짜로 계산합니다

st.set_page_config(page_title="박스오피스", layout="wide")
st.title("일별 박스오피스")


def read_key():
    """스트림릿 비밀 정보(Secrets)에서 인증키를 읽습니다. 값은 화면에 표시하지 않습니다."""
    try:
        return str(st.secrets.get("KOBIS_KEY", "")).strip()
    except Exception:          # 비밀 정보 파일이 아예 없을 때
        return ""


def show_table(table, formats):
    """내려받기 메뉴가 없는 정적 표(st.table)로 보여 줍니다. 첫 열을 행 이름으로 사용합니다."""
    st.table(table.set_index(table.columns[0]).style.format(formats, na_rep=""))


KEY = read_key()
if not KEY:
    st.error(
        "KOBIS_KEY가 설정되어 있지 않습니다. "
        "스트림릿 클라우드의 [Settings] - [Secrets]에 "
        'KOBIS_KEY = "발급받은키" 형태로 저장한 뒤 앱을 다시 실행하십시오.'
    )
    st.stop()

pick = st.date_input("날짜", value=datetime.now(KST).date() - timedelta(days=1))   # 기본값은 한국 시간 기준 어제


@st.cache_data(ttl=600, show_spinner=False)
def load_daily(target_dt, _key):
    res = requests.get(DAILY_URL, params={"key": _key, "targetDt": target_dt}, timeout=10)
    res.raise_for_status()
    box = res.json()["boxOfficeResult"]
    return box.get("boxofficeType", ""), box.get("showRange", ""), box.get("dailyBoxOfficeList", [])


try:
    kind, show_range, rows = load_daily(pick.strftime("%Y%m%d"), KEY)
except Exception:
    st.error("정보를 불러오지 못했습니다. 인증키, 날짜, 인터넷 연결을 확인하십시오.")
    st.stop()

if not rows:
    st.warning("불러온 영화가 없습니다. 다른 날짜를 선택하십시오.")
    st.stop()

df = pd.DataFrame(rows)
bad = {}
for col, name in [("rank", "순위"), ("audiCnt", "당일 관객 수"), ("audiAcc", "누적 관객 수"),
                  ("scrnCnt", "스크린 수"), ("showCnt", "상영 횟수")]:
    df[name] = pd.to_numeric(df[col], errors="coerce")
    bad[name] = int(df[name].isna().sum())
df["영화명"] = df["movieNm"]
df["개봉일"] = df["openDt"]

st.write(
    f"조회 기간은 {show_range}이고, 불러온 영화는 {len(df)}편입니다. "
    "숫자로 바꾸지 못한 값은 " + ", ".join(f"{k} {v}개" for k, v in bad.items()) + "입니다."
)

COMMA = "{:,.0f}"   # 천 단위 쉼표
show_table(
    df[["순위", "영화명", "개봉일", "당일 관객 수", "누적 관객 수", "스크린 수", "상영 횟수"]],
    {"당일 관객 수": COMMA, "누적 관객 수": COMMA, "스크린 수": COMMA, "상영 횟수": COMMA},
)

st.subheader("당일 관객 수 기준 그래프")
fig = px.bar(df.sort_values("당일 관객 수"), x="당일 관객 수", y="영화명", orientation="h",
             hover_data=["개봉일", "누적 관객 수"], labels={"영화명": ""})
fig.update_layout(margin=dict(t=20, l=10, r=10, b=40))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- 1위 영화 집중도
st.subheader("1위 영화 집중도 분석")
top = df.sort_values("당일 관객 수", ascending=False).iloc[0]


def donut(value, rest, title, color):
    total = value + rest
    share = value / total * 100 if total else 0
    f = go.Figure(go.Pie(
        labels=["1위 영화", "나머지 9편"], values=[value, rest], hole=0.55, sort=False,
        marker=dict(colors=[color, "#d9d9d9"]),
        texttemplate="%{percent:.1%}",
        hovertemplate="%{label}: %{value:,}<br>상위 10편 합계: " + f"{total:,}" + "<br>비율 %{percent:.1%}<extra></extra>",
    ))
    f.update_layout(title=dict(text=title), margin=dict(t=60, l=10, r=10, b=10), height=420,
                    annotations=[dict(text=f"{share:.1f}%", x=0.5, y=0.5, font_size=30, showarrow=False)])
    return f, share


c1, c2 = st.columns(2)
f1, s1 = donut(int(top["당일 관객 수"]), int(df["당일 관객 수"].sum() - top["당일 관객 수"]),
               "상위 10편의 관객 중 1위 영화의 비율", "#ef553b")
f2, s2 = donut(int(top["상영 횟수"]), int(df["상영 횟수"].sum() - top["상영 횟수"]),
               "상위 10편의 상영 횟수 중 1위 영화의 비율", "#636efa")
c1.plotly_chart(f1, use_container_width=True)
c2.plotly_chart(f2, use_container_width=True)
st.caption(f"분석 대상 1위 영화: {top['영화명']} (개봉일 {top['개봉일']}) · 조회 기간 {show_range}")
