# 7장 2절 주간 박스오피스 - 기준 날짜부터 7일씩 거슬러 올라가며 52주를 한 표로 합칩니다.
# 응답은 화면에서만 사용하고 파일로 내려받거나 올리지 않습니다.
# 그래서 표는 내려받기 메뉴가 있는 st.dataframe 대신 정적 표(st.table)로 보여 줍니다.
import time
from datetime import date, datetime, timedelta, timezone

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

WEEKLY_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchWeeklyBoxOfficeList.json"
WEEKS = 52           # 모을 주 수
SLEEP_SEC = 0.2      # 요청 사이에 두는 간격
TIMEOUT = 15         # 한 요청을 기다리는 최대 시간(초)
MAX_TRY = 3          # 한 요청당 최대 시도 횟수
KST = timezone(timedelta(hours=9))   # 서버 시계가 UTC여도 한국 시간으로 계산합니다

st.set_page_config(page_title="주간박스오피스", layout="wide")
st.title("최근 52주의 주간 박스오피스")


# ---------------------------------------------------------------- 인증키
def read_key():
    """스트림릿 비밀 정보(Secrets)에서 인증키를 읽습니다. 값은 화면에 표시하지 않습니다."""
    try:
        return str(st.secrets.get("KOBIS_KEY", "")).strip()
    except Exception:          # 비밀 정보 파일이 아예 없을 때
        return ""


def show_table(table, formats):
    """내려받기 메뉴가 없는 정적 표(st.table)로 보여 줍니다. 첫 열을 행 이름으로 사용합니다."""
    view = table.copy()
    first = view.columns[0]
    if pd.api.types.is_datetime64_any_dtype(view[first]):
        view[first] = view[first].dt.strftime("%Y-%m-%d")
    st.table(view.set_index(first).style.format(formats, na_rep=""))


KEY = read_key()
if not KEY:
    st.error(
        "KOBIS_KEY가 설정되어 있지 않습니다. "
        "스트림릿 클라우드의 [Settings] - [Secrets]에 "
        'KOBIS_KEY = "발급받은키" 형태로 저장한 뒤 앱을 다시 실행하십시오.'
    )
    st.stop()


def monday_of(d):
    """d가 속한 주의 월요일을 돌려줍니다."""
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------- 수집
@st.cache_data(ttl=600, show_spinner=False)
def collect_weekly(end_monday_iso, _key):
    """기준 날짜가 속한 주부터 7일씩 거슬러 올라가며 52주를 요청합니다.

    같은 집계 기간을 두 번 요청하지 않으며, 받은 응답은 표로만 사용합니다.
    캐시는 10분 동안만 유지되고 파일로 저장하지 않습니다.
    """
    end_monday = date.fromisoformat(end_monday_iso)
    rows, ok, fail, failed_weeks, seen, tries = [], 0, 0, [], set(), 0
    session = requests.Session()
    bar = st.progress(0.0, text="주간 박스오피스를 불러오는 중입니다.")
    started = time.time()
    day = end_monday
    for i in range(WEEKS):
        target = day.strftime("%Y%m%d")
        got = None
        for _ in range(MAX_TRY):
            tries += 1                    # 다시 시도한 요청까지 센 실제 요청 횟수
            try:
                res = session.get(
                    WEEKLY_URL,
                    params={"key": _key, "targetDt": target, "weekGb": "0"},
                    timeout=TIMEOUT,
                )
                res.raise_for_status()
                got = res.json()["boxOfficeResult"]
                break
            except Exception:
                time.sleep(SLEEP_SEC * 2)
        if got is None:
            fail += 1
            failed_weeks.append(target)   # 실패한 주는 관객 수 0으로 채우지 않고 비워 둡니다
        else:
            ok += 1
            week_start = str(got.get("showRange", target))[:8]
            if week_start not in seen:    # 같은 집계 기간은 한 번만 담습니다
                seen.add(week_start)
                for m in got.get("weeklyBoxOfficeList", []):
                    rows.append({
                        "집계기간": week_start,
                        "순위": m.get("rank"),
                        "영화코드": str(m.get("movieCd")),   # 영화 코드는 문자로 다룹니다
                        "영화명": m.get("movieNm"),
                        "개봉일": m.get("openDt"),
                        "주간관객": m.get("audiCnt"),
                        "누적관객": m.get("audiAcc"),
                    })
        day -= timedelta(days=7)
        time.sleep(SLEEP_SEC)
        bar.progress((i + 1) / WEEKS, text=f"{i + 1}/{WEEKS}주 ({time.time() - started:.0f}초 지남)")
    bar.empty()
    df = pd.DataFrame(rows, columns=["집계기간", "순위", "영화코드", "영화명", "개봉일", "주간관객", "누적관객"])
    return df, {"요청": WEEKS, "성공": ok, "실패": fail, "실패한주": failed_weeks, "시도": tries}


def tidy(df):
    """날짜와 숫자를 계산할 수 있는 형태로 바꾸고, 바꾸지 못한 값의 수를 함께 돌려줍니다."""
    out = df.copy()
    bad = {}
    out["집계기간"] = pd.to_datetime(out["집계기간"], format="%Y%m%d", errors="coerce")
    bad["집계기간"] = int(out["집계기간"].isna().sum())
    out["개봉일"] = pd.to_datetime(out["개봉일"], errors="coerce")
    bad["개봉일"] = int(out["개봉일"].isna().sum())
    for col in ["순위", "주간관객", "누적관객"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        bad[col] = int(out[col].isna().sum())
    return out, bad


# ---------------------------------------------------------------- 화면
base = st.date_input("기준 날짜", value=datetime.now(KST).date() - timedelta(days=7),   # 기본값은 지난주
                     help="이 날짜가 속한 주부터 7일씩 거슬러 올라가며 52주를 모읍니다.")
end_monday = monday_of(base)
start_monday = end_monday - timedelta(days=7 * (WEEKS - 1))

c1, c2 = st.columns([1, 2])
c1.metric("요청 횟수", f"{WEEKS}회")
c2.metric("모을 기간", f"{start_monday} ~ {end_monday + timedelta(days=6)}")
st.caption(
    "주간 박스오피스 API를 한 주에 한 번씩 요청합니다. "
    "받은 응답은 화면에서만 사용하고 파일로 저장하지 않으며, 10분 동안만 앱이 기억합니다."
)

if st.button("불러오기", type="primary"):
    started = time.time()
    raw, stat = collect_weekly(end_monday.isoformat(), KEY)
    st.session_state["weekly_raw"] = raw
    st.session_state["weekly_stat"] = stat
    st.session_state["weekly_seconds"] = time.time() - started
    st.session_state["weekly_at"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

if "weekly_raw" not in st.session_state:
    st.info("기준 날짜를 정하고 [불러오기]를 누르십시오.")
    st.stop()

raw, stat = st.session_state["weekly_raw"], st.session_state["weekly_stat"]
st.write(
    f"요청 {stat['요청']}회 가운데 성공 {stat['성공']}회, 실패 {stat['실패']}회입니다. "
    f"불러오는 데 {st.session_state['weekly_seconds']:.0f}초 걸렸으며, "
    f"{st.session_state['weekly_at']}에 불러온 데이터입니다."
)
retries = stat.get("시도", stat["요청"]) - stat["요청"]
if retries > 0:
    st.caption(f"불러오지 못해 다시 보낸 요청 {retries}회를 포함하면 실제로 보낸 요청은 {stat['시도']}회입니다.")
if stat["실패"]:
    st.warning("불러오지 못한 주는 빈 값으로 두었습니다. 관객 수 0으로 바꾸지 않았습니다.")

data, bad = tidy(raw)
dup = int(data.duplicated(subset=["영화코드", "집계기간"]).sum())
weeks_got = data["집계기간"].dropna()
if weeks_got.empty:
    st.error("불러온 주간 박스오피스가 없어 분석할 수 없습니다. 인증키, 기준 날짜, 인터넷 연결을 확인한 뒤 다시 불러오십시오.")
    st.stop()
st.write(
    f"실제로 불러온 집계 기간은 {weeks_got.min():%Y-%m-%d}부터 {weeks_got.max():%Y-%m-%d}까지 "
    f"서로 다른 {weeks_got.nunique()}주이고, 영화 {data['영화코드'].nunique()}편, 전체 {len(data)}행입니다. "
    "형태를 바꾸지 못한 값은 "
    + ", ".join(f"{k} {v}개" for k, v in bad.items())
    + f"이고, 영화 코드와 집계 기간이 같은 중복은 {dup}건입니다."
)

COMMA, DAY = "{:,.0f}", "{:%Y-%m-%d}"   # 천 단위 쉼표, 연-월-일
with st.container(height=420):          # 행이 많으므로 이 높이 안에서 스크롤합니다
    show_table(
        data[["집계기간", "순위", "영화코드", "영화명", "개봉일", "주간관객", "누적관객"]],
        {"순위": COMMA, "개봉일": DAY, "주간관객": COMMA, "누적관객": COMMA},
    )


# ---------------------------------------------------------------- 첫 번째 기준: 누적 관객 수
FETCHED = st.session_state["weekly_at"]
PERIOD = f"{weeks_got.min():%Y-%m-%d} ~ {weeks_got.max():%Y-%m-%d}"
NWEEK = weeks_got.nunique()
SUB = f"분석 기간 {PERIOD} · 수집한 주 {NWEEK}주 · {FETCHED}에 API로 불러온 데이터"


def titled(fig, text):
    fig.update_layout(title=dict(text=f"{text}<br><sup>{SUB}</sup>"),
                      margin=dict(t=90, l=10, r=10, b=40))
    return fig


st.subheader("영화별 최근 누적 관객 수 TOP 10")
st.caption(f"분석에 사용한 데이터: {FETCHED}에 API로 불러온 주간 박스오피스 {NWEEK}주 기록")

latest = data.dropna(subset=["집계기간"]).sort_values("집계기간").groupby("영화코드").tail(1)
appear = data.groupby("영화코드")["집계기간"].nunique().rename("등장 주 수")
acc = (latest.join(appear, on="영화코드")
       .rename(columns={"집계기간": "가장 최근 집계 기간", "누적관객": "누적 관객 수"}))
top_acc = acc.sort_values("누적 관객 수", ascending=False).head(10)

show_table(
    top_acc[["영화명", "개봉일", "가장 최근 집계 기간", "누적 관객 수", "등장 주 수"]],
    {"개봉일": DAY, "가장 최근 집계 기간": DAY, "누적 관객 수": COMMA},
)
fig_acc = px.bar(top_acc.sort_values("누적 관객 수"), x="누적 관객 수", y="영화명", orientation="h",
                 hover_data=["개봉일", "가장 최근 집계 기간", "등장 주 수"],
                 labels={"영화명": "", "누적 관객 수": "누적 관객 수(명)"})
st.plotly_chart(titled(fig_acc, "영화별 최근 누적 관객 수 TOP 10"), use_container_width=True)


# ---------------------------------------------------------------- 두 번째 기준: 연속 1위 기간
st.subheader("연속 1위 기간이 긴 영화 TOP 10")
st.caption(f"분석에 사용한 데이터: {FETCHED}에 API로 불러온 주간 박스오피스 {NWEEK}주 기록")

ones = data[(data["순위"] == 1)].dropna(subset=["집계기간"]).sort_values("집계기간").copy()
끊김 = (ones["영화코드"] != ones["영화코드"].shift()) | \
      ((ones["집계기간"] - ones["집계기간"].shift()).dt.days != 7)   # 빠진 주가 있으면 연속으로 세지 않습니다
ones["구간"] = 끊김.cumsum()
runs = ones.groupby(["구간", "영화코드"]).size().rename("연속").reset_index()
best = runs.groupby("영화코드")["연속"].max().rename("가장 긴 연속 1위 기간")
total = ones.groupby("영화코드").size().rename("전체 1위 횟수")
info = ones.groupby("영화코드").agg(영화명=("영화명", "first"), 개봉일=("개봉일", "first"))
rank1 = info.join(total).join(best).reset_index()
top_run = rank1.sort_values(["가장 긴 연속 1위 기간", "전체 1위 횟수"], ascending=False).head(10)
if top_run.empty:
    st.warning("불러온 기록에 순위 1위가 없어 연속 1위 기간과 두 기준 비교를 계산하지 않았습니다.")
    st.stop()

show_table(top_run[["영화명", "개봉일", "전체 1위 횟수", "가장 긴 연속 1위 기간"]], {"개봉일": DAY})
fig_run = px.bar(top_run.sort_values(["가장 긴 연속 1위 기간", "전체 1위 횟수"]),
                 x="가장 긴 연속 1위 기간", y="영화명", orientation="h",
                 hover_data=["개봉일", "전체 1위 횟수"],
                 labels={"영화명": "", "가장 긴 연속 1위 기간": "가장 긴 연속 1위 기간(주)"})
st.plotly_chart(titled(fig_run, "연속 1위 기간이 긴 영화 TOP 10"), use_container_width=True)


# ---------------------------------------------------------------- 두 기준 비교
st.subheader("누적 관객 수와 연속 1위 기간 비교")
st.caption(f"분석에 사용한 데이터: {FETCHED}에 API로 불러온 주간 박스오피스 {NWEEK}주 기록")

cmp = rank1.merge(acc[["영화코드", "가장 최근 집계 기간", "누적 관객 수"]], on="영화코드", how="left")
king_acc = acc.sort_values("누적 관객 수", ascending=False).iloc[0]["영화명"]
king_run = top_run.iloc[0]["영화명"]
cmp["구분"] = "그 밖의 영화"
cmp.loc[cmp["영화명"] == king_acc, "구분"] = "누적 관객 수 1위"
cmp.loc[cmp["영화명"] == king_run, "구분"] = "연속 1위 기간 1위"
if king_acc == king_run:
    cmp.loc[cmp["영화명"] == king_acc, "구분"] = "두 기준 모두 1위"
    verdict = f"누적 관객 수 1위와 연속 1위 기간 1위가 같습니다: {king_acc}"
else:
    verdict = f"누적 관객 수 1위는 {king_acc}, 연속 1위 기간 1위는 {king_run}입니다."

fig_cmp = px.scatter(
    cmp, x="누적 관객 수", y="가장 긴 연속 1위 기간", size="전체 1위 횟수", color="구분",
    size_max=26, hover_name="영화명",
    hover_data=["개봉일", "가장 최근 집계 기간", "전체 1위 횟수"],
    labels={"누적 관객 수": "가장 최근 누적 관객 수(명)", "가장 긴 연속 1위 기간": "가장 긴 연속 1위 기간(주)"},
)
st.markdown(f"**{verdict}**")
st.plotly_chart(titled(fig_cmp, "누적 관객 수와 연속 1위 기간 비교"), use_container_width=True)
