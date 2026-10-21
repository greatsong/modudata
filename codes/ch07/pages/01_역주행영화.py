# 7장 2절 역주행 영화 - 주간 박스오피스 API로 뒤늦게 관객이 늘어난 영화 찾기
# 응답은 화면에서만 사용하고 파일로 저장하거나 내려받게 하지 않습니다.
# 그래서 표는 내려받기 메뉴가 있는 st.dataframe 대신 정적 표(st.table)로 보여 줍니다.
import time
from datetime import date, datetime, timedelta, timezone

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

WEEKLY_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchWeeklyBoxOfficeList.json"
SLEEP_SEC = 0.2      # 요청 사이에 두는 간격
TIMEOUT = 15         # 한 요청을 기다리는 최대 시간(초)
MAX_TRY = 3          # 한 요청당 최대 시도 횟수
SEC_PER_CALL = 1.0   # 예상 소요 시간을 계산할 때 사용하는 한 요청당 평균 시간(초)
KST = timezone(timedelta(hours=9))   # 서버 시계가 UTC여도 한국 시간으로 계산합니다

st.set_page_config(page_title="역주행영화", layout="wide")
st.title("뒤늦게 관객이 늘어난 영화 찾기")


# ---------------------------------------------------------------- 인증키
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


# ---------------------------------------------------------------- 날짜 도우미
def monday_of(d):
    """d가 속한 주의 월요일을 돌려줍니다."""
    return d - timedelta(days=d.weekday())


def last_complete_monday(today=None):
    """집계가 끝난 가장 최근 주(지난주)의 월요일입니다."""
    today = today or datetime.now(KST).date()
    return monday_of(today) - timedelta(days=7)


# ---------------------------------------------------------------- 수집
@st.cache_data(ttl=600, show_spinner=False)
def collect_weekly(years, end_monday_iso, _key):
    """지난주부터 7일씩 거슬러 올라가며 주간 박스오피스를 요청합니다.

    한 주에 한 번씩 요청하고, 받은 응답은 표로만 사용합니다.
    캐시는 10분 동안만 유지되며 파일로 저장하지 않습니다.
    """
    end_monday = date.fromisoformat(end_monday_iso)
    weeks = years * 52
    rows, ok, fail, failed_weeks, tries = [], 0, 0, [], 0
    session = requests.Session()
    bar = st.progress(0.0, text="주간 박스오피스를 불러오는 중입니다.")
    started = time.time()
    day = end_monday
    for i in range(weeks):
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
            for m in got.get("weeklyBoxOfficeList", []):
                rows.append({
                    "주시작일": week_start,
                    "순위": m.get("rank"),
                    "영화코드": str(m.get("movieCd")),   # 영화 코드는 문자로 다룹니다
                    "영화명": m.get("movieNm"),
                    "개봉일": m.get("openDt"),
                    "주간관객": m.get("audiCnt"),
                    "누적관객": m.get("audiAcc"),
                })
        day -= timedelta(days=7)
        time.sleep(SLEEP_SEC)
        bar.progress((i + 1) / weeks, text=f"{i + 1}/{weeks}주 ({time.time() - started:.0f}초 지남)")
    bar.empty()
    df = pd.DataFrame(rows, columns=["주시작일", "순위", "영화코드", "영화명", "개봉일", "주간관객", "누적관객"])
    return df, {"요청": weeks, "성공": ok, "실패": fail, "실패한주": failed_weeks, "시도": tries}


def tidy(df):
    """날짜와 숫자를 계산할 수 있는 형태로 바꾸고, 바꾸지 못한 값의 수를 함께 돌려줍니다."""
    out = df.copy()
    bad = {}
    out["주시작일"] = pd.to_datetime(out["주시작일"], format="%Y%m%d", errors="coerce")
    bad["주시작일"] = int(out["주시작일"].isna().sum())
    out["개봉일"] = pd.to_datetime(out["개봉일"], errors="coerce")
    bad["개봉일"] = int(out["개봉일"].isna().sum())
    for col in ["순위", "주간관객", "누적관객"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        bad[col] = int(out[col].isna().sum())
    out = out.drop_duplicates(subset=["영화코드", "주시작일"])
    return out, bad


# ---------------------------------------------------------------- 역주행 계산
def add_week_no(df):
    """개봉일이 속한 주의 월요일을 1주차로 보고 주차를 매깁니다."""
    out = df.dropna(subset=["주시작일", "개봉일"]).copy()
    open_monday = out["개봉일"] - pd.to_timedelta(out["개봉일"].dt.weekday, unit="D")
    out["주차"] = ((out["주시작일"] - open_monday).dt.days // 7) + 1
    return out


def find_candidates(df):
    """1주차와 2주차를 초반으로, 3주차부터 8주차까지를 이후 구간으로 보고 역주행 후보를 찾습니다."""
    early = df[(df["주차"] >= 1) & (df["주차"] <= 8)]
    rows, no_early, zero_early = [], 0, 0
    for code, g in early.groupby("영화코드"):
        weeks = set(g["주차"])
        if not ({1, 2} <= weeks):           # 1주차와 2주차 기록이 모두 있어야 비교합니다
            continue
        if len(g) < 4:                      # 첫 8주 안에 기록이 4개 이상 있어야 남깁니다
            continue
        first = g[g["주차"].isin([1, 2])]["주간관객"].max()
        later = g[g["주차"].between(3, 8)].dropna(subset=["주간관객"])
        if later.empty:
            no_early += 1
            continue
        peak_row = later.loc[later["주간관객"].idxmax()]
        peak = peak_row["주간관객"]
        if pd.isna(first) or first <= 0:    # 초반 관객 수가 0이거나 비어 있으면 배율을 계산하지 않습니다
            zero_early += 1
            continue
        rows.append({
            "영화코드": code,
            "영화명": g["영화명"].iloc[0],
            "개봉일": g["개봉일"].iloc[0],
            "초반 관객 수": int(first),
            "정점 주차": int(peak_row["주차"]),
            "정점 관객 수": int(peak),
            "증가 배율": round(peak / first, 2),
        })
    table = pd.DataFrame(rows)
    if not table.empty:
        table = table[table["정점 관객 수"] > table["초반 관객 수"]]
        table = table.sort_values("증가 배율", ascending=False).reset_index(drop=True)
    return table, {"3주차부터 8주차까지 기록 없음": no_early, "초반 관객 수가 0이거나 빈 값": zero_early}


# ---------------------------------------------------------------- 화면
years = st.slider("분석할 기간(년)", min_value=1, max_value=10, value=5,
                  help="기간이 길수록 후보가 늘어나지만 불러오는 시간도 길어집니다.")
calls = years * 52
est_min = calls * (SEC_PER_CALL + SLEEP_SEC) / 60
end_monday = last_complete_monday()
start_monday = end_monday - timedelta(days=7 * (calls - 1))

c1, c2, c3 = st.columns([1, 1, 2])
c1.metric("요청 횟수", f"{calls}회")
c2.metric("예상 소요 시간", f"약 {est_min:.0f}분")
c3.metric("조회 기간", f"{start_monday} ~ {end_monday + timedelta(days=6)}")
st.caption(
    "주간 박스오피스 API를 한 주에 한 번씩 요청합니다. "
    "받은 응답은 화면에서만 사용하고 파일로 저장하지 않으며, 10분 동안만 앱이 기억합니다."
)

if st.button("불러오기", type="primary"):
    started = time.time()
    raw, stat = collect_weekly(years, end_monday.isoformat(), KEY)
    st.session_state["raw"] = raw
    st.session_state["stat"] = stat
    st.session_state["seconds"] = time.time() - started
    st.session_state["at"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

if "raw" not in st.session_state:
    st.info("기간을 정하고 [불러오기]를 누르십시오.")
    st.stop()

raw, stat = st.session_state["raw"], st.session_state["stat"]
st.write(
    f"요청 {stat['요청']}회 가운데 성공 {stat['성공']}회, 실패 {stat['실패']}회입니다. "
    f"불러오는 데 {st.session_state['seconds']:.0f}초 걸렸으며, "
    f"{st.session_state['at']}에 불러온 데이터입니다."
)
retries = stat.get("시도", stat["요청"]) - stat["요청"]
if retries > 0:
    st.caption(f"불러오지 못해 다시 보낸 요청 {retries}회를 포함하면 실제로 보낸 요청은 {stat['시도']}회입니다.")
if stat["성공"] == 0:
    st.error("한 주도 불러오지 못했습니다. 인증키와 인터넷 연결을 확인한 뒤 다시 불러오십시오.")
    st.stop()
if stat["실패"]:
    st.warning("불러오지 못한 주는 빈 값으로 두었습니다. 관객 수 0으로 바꾸지 않았습니다.")

data, bad = tidy(raw)
st.write(
    f"서로 다른 주 {data['주시작일'].nunique()}개, 영화 {data['영화코드'].nunique()}편, "
    f"전체 {len(data)}행입니다. 형태를 바꾸지 못한 값은 "
    + ", ".join(f"{k} {v}개" for k, v in bad.items())
    + "입니다."
)

table, dropped = find_candidates(add_week_no(data))
if table.empty:
    st.warning("정해 둔 조건을 만족하는 역주행 후보가 없습니다. 기간을 늘려 다시 시도하십시오.")
    st.stop()

st.subheader("역주행 후보 10편")
st.caption(
    "개봉일이 속한 주를 1주차로 보고, 1주차와 2주차 관객 수 가운데 큰 값을 초반 관객 수로, "
    "3주차부터 8주차까지 가운데 가장 큰 값을 정점 관객 수로 정했습니다. "
    f"제외한 영화는 {', '.join(f'{k} {v}편' for k, v in dropped.items())}입니다."
)
top = table.head(10)
COMMA = "{:,.0f}"   # 천 단위 쉼표
show_table(
    top[["영화명", "개봉일", "초반 관객 수", "정점 주차", "정점 관객 수", "증가 배율"]],
    {"개봉일": "{:%Y-%m-%d}", "초반 관객 수": COMMA, "정점 관객 수": COMMA, "증가 배율": "{:.2f}"},
)

fig = px.bar(
    top.sort_values("증가 배율"), x="증가 배율", y="영화명", orientation="h",
    hover_data=["개봉일", "초반 관객 수", "정점 주차", "정점 관객 수"],
    labels={"증가 배율": "증가 배율(배)", "영화명": ""},
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("선택한 영화의 개봉 후 첫 20주")
picked = st.selectbox("후보 가운데 한 편을 선택하십시오.", top["영화명"])
code = top.loc[top["영화명"] == picked, "영화코드"].iloc[0]
one = add_week_no(data)
one = one[(one["영화코드"] == code) & one["주차"].between(1, 20)]
line = (one.set_index("주차")
           .reindex(range(1, 21))          # 기록이 없는 주는 빈 값으로 남깁니다
           .reset_index())
line["영화명"] = picked
fig2 = px.line(
    line, x="주차", y="주간관객", markers=True,
    hover_data=["영화명", "주시작일", "순위"],
    labels={"주차": "개봉 후 주차", "주간관객": "주간 관객 수(명)"},
)
fig2.update_traces(connectgaps=False)       # 기록이 없는 구간은 선으로 잇지 않습니다
st.plotly_chart(fig2, use_container_width=True)

st.info(
    "이 표는 역주행을 확정한 결과가 아니라 위에서 정한 조건으로 찾은 후보입니다. "
    "주간 박스오피스에는 매주 상위 10편만 들어 있으므로 그 밖의 영화는 비교에서 빠집니다. "
    "조회 시점에 따라 결과가 달라집니다."
)
