# 7장 전체 코드 - 살아 있는 데이터 병아리반(영화·서울) (2026-09-04, 점검 반영)
# 실행 조건: 스트림릿 클라우드 [Settings] → [Secrets]에 KOBIS_KEY, SEOUL_KEY 등록
import time
from datetime import date, timedelta

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# ── 극장가 리포트(KOBIS) ──────────────────────────────
DAILY_URL  = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
WEEKLY_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchWeeklyBoxOfficeList.json"
WEEKLY_CSV = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_weekly.csv"

@st.cache_data(ttl=3600)                      # 한 시간 동안은 같은 요청을 다시 보내지 않음
def load_daily(target_dt):
    res = requests.get(DAILY_URL, params={"key": st.secrets["KOBIS_KEY"], "targetDt": target_dt})
    return res.json()["boxOfficeResult"]["dailyBoxOfficeList"]

@st.cache_data
def collect_weekly(years=10):
    """주간 박스오피스를 최근 years년치 거슬러 받아 한 표로 합친다 (10년 = 약 520번 호출)."""
    rows, day = [], date.today() - timedelta(days=7)
    total = years * 52
    bar = st.progress(0, text="주간 박스오피스 받는 중...")
    for i in range(total):
        res = requests.get(WEEKLY_URL, params={"key": st.secrets["KOBIS_KEY"],
                                               "targetDt": day.strftime("%Y%m%d"), "weekGb": "0"})
        box = res.json()["boxOfficeResult"]
        for m in box["weeklyBoxOfficeList"]:
            rows.append({"주시작일": box["showRange"][:8], "순위": int(m["rank"]),
                         "영화코드": m["movieCd"],      # 이름이 같은 다른 영화를 구분하는 열
                         "영화명": m["movieNm"], "개봉일": m["openDt"],
                         "주간관객": int(m["audiCnt"]), "누적관객": int(m["audiAcc"])})
        day -= timedelta(days=7)
        time.sleep(0.3)                        # 서버에 부담을 주지 않게 잠깐 쉬기
        bar.progress((i + 1) / total, text=f"{i + 1}/{total}주")
    df = pd.DataFrame(rows)
    df["주시작일"] = pd.to_datetime(df["주시작일"])           # 예제 표와 같은 날짜형으로
    df["개봉일"] = pd.to_datetime(df["개봉일"], errors="coerce")
    st.download_button("주간 표 CSV로 내려받기", df.to_csv(index=False).encode("utf-8-sig"),
                       "kobis_weekly.csv", "text/csv")
    return df

@st.cache_data
def load_weekly_csv():
    """예제 저장소에 미리 모아 둔 2004년~ 주간 표 (기다리기 어려울 때)."""
    w = pd.read_csv(WEEKLY_CSV)
    w["주시작일"] = pd.to_datetime(w["주시작일"].astype(str))
    w["개봉일"] = pd.to_datetime(w["개봉일"], errors="coerce")
    return w

st.header("극장가 리포트")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["어제의 Top 10", "역대 기록", "롱런·최장 1위·역주행", "연도별 흐름과 장르", "스크린과 관객"])

# 탭 ① 어제의 Top 10 + 1위 점유율
yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
df = pd.DataFrame(load_daily(yesterday))
for col in ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]:
    df[col] = df[col].astype(int)              # 문자열로 오니 진짜 숫자로
df["구분"] = df["openDt"].str[:4].astype(int).apply(
    lambda y: f"{date.today().year}년 개봉" if y >= date.today().year else "그 전에 개봉(재개봉)")
with tab1:
    st.dataframe(df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc"]]
                 .rename(columns={"rank": "순위", "movieNm": "영화명", "openDt": "개봉일",
                                  "audiCnt": "관객수", "audiAcc": "누적관객"}))
    fig = px.bar(df.sort_values("rank", ascending=False), y="movieNm", x="audiCnt",
                 orientation="h", color="구분", labels={"movieNm": "", "audiCnt": "관객 수"})
    st.plotly_chart(fig)
    top1 = df[df["rank"] == 1].iloc[0]
    share = pd.DataFrame({"기준": ["스크린 수", "상영 횟수", "관객 수"],
                          "점유율(%)": [round(top1[c] / df[c].sum() * 100, 1)
                                     for c in ["scrnCnt", "showCnt", "audiCnt"]]})
    st.plotly_chart(px.bar(share, x="기준", y="점유율(%)", text="점유율(%)"))

# 주간 표: 직접 모으기(10년) 또는 예제 저장소 표(2004년~)
w = load_weekly_csv()                          # collect_weekly(10) 으로 바꾸면 직접 모은다
final = w.groupby("영화명").agg(누적관객=("누적관객", "max"), 개봉일=("개봉일", "first")).reset_index()

# 탭 ② 역대 Top 10 + 지표 카드
with tab2:
    top10 = final.sort_values("누적관객", ascending=False).head(10)
    c1, c2, c3 = st.columns(3)
    c1.metric("역대 1위", top10.iloc[0]["영화명"])
    c2.metric("관객 수", f"{top10.iloc[0]['누적관객']:,}")
    c3.metric("1,000만 영화", f"{(final['누적관객'] >= 10_000_000).sum()}편")
    top10["천만"] = top10["누적관객"] >= 10_000_000
    fig = px.bar(top10.iloc[::-1], y="영화명", x="누적관객", orientation="h", color="천만",
                 labels={"영화명": "", "누적관객": "누적 관객"})
    st.plotly_chart(fig)
    st.caption("누적관객은 주간 박스오피스 기록으로 계산한 근삿값입니다")
    # 역대 누적 관객 Top 10 레이스: 달마다 그때까지의 누적을 다시 세어 순위를 매긴다
    race = w.sort_values("주시작일").copy()
    race["연월"] = race["주시작일"].dt.to_period("M").astype(str)
    frames = []
    for ym in sorted(race["연월"].unique()):
        upto = race[race["연월"] <= ym].groupby(["영화코드", "영화명"])["누적관객"].max().reset_index()
        top = upto.sort_values("누적관객", ascending=False).head(10).reset_index(drop=True)
        top["순위"] = top.index + 1
        top["연월"] = ym
        frames.append(top)
    race10 = pd.concat(frames)
    fig = px.bar(race10, x="누적관객", y=-race10["순위"], orientation="h", text="영화명",
                 animation_frame="연월", range_x=[0, 18_500_000], range_y=[-10.5, -0.5],
                 labels={"누적관객": "누적 관객", "y": ""})
    fig.update_yaxes(showticklabels=False)                          # 자리(순위)로만 오르내린다
    fig.update_traces(textposition="inside", insidetextanchor="start")
    st.plotly_chart(fig)                                            # 재생 버튼과 슬라이더가 저절로 붙는다

# 탭 ③ 롱런 Top 10 + 역주행 표
with tab3:
    weeks = w.groupby(["영화코드", "영화명"]).agg(주수=("주시작일", "size"), 개봉일=("개봉일", "first")).reset_index()
    longrun = weeks.sort_values("주수", ascending=False).head(10)
    longrun["표시"] = longrun["영화명"] + " (" + longrun["개봉일"].dt.year.astype(str) + ")"
    st.plotly_chart(px.bar(longrun.iloc[::-1], y="표시", x="주수", orientation="h",
                           labels={"표시": "", "주수": "주간 Top 10에 머문 주 수"}))
    # 역대급 역주행: 개봉 주 관객 대비 뒤 주 최고 관객의 배율 (정점 4주차 이후, 재개봉·사전 상영 제외, 영화 코드로 구분)
    ww = w[w["개봉일"].notna()].sort_values(["영화코드", "주시작일"])
    gap = (ww.groupby("영화코드")["주시작일"].first() - ww.groupby("영화코드")["개봉일"].first()).dt.days
    ww = ww[ww["영화코드"].isin(gap[(gap >= -6) & (gap <= 13)].index) & (ww["주시작일"] >= ww["개봉일"] - pd.Timedelta(days=6))]
    ww["주차"] = ww.groupby("영화코드").cumcount() + 1
    rv = ww.groupby("영화코드").agg(영화명=("영화명", "first"), 개봉주=("주간관객", "first"),
                                   최고주=("주간관객", "max"), 최고순위=("순위", "min"), 최종관객=("누적관객", "max"))
    rv["정점주차"] = ww.loc[ww.groupby("영화코드")["주간관객"].idxmax()].set_index("영화코드")["주차"]
    rv["배율"] = (rv["최고주"] / rv["개봉주"]).round(1)
    rv = rv[(rv["정점주차"] >= 4) & (rv["최고주"] >= 100_000) & (rv["개봉주"] >= 30_000)]
    st.subheader("역대급 역주행 Top 10 - 개봉 주보다 뒤 주에 관객이 늘어난 영화")
    st.dataframe(rv.sort_values("배율", ascending=False).head(10))
    ones = w[w["순위"] == 1].sort_values("주시작일")
    ones["run"] = (ones["영화명"] != ones["영화명"].shift()).cumsum()     # 영화가 바뀔 때마다 새 구간
    runs = ones.groupby(["run", "영화명"]).agg(연속주=("주시작일", "size"), 시작=("주시작일", "min")).reset_index()
    st.subheader("역대 최장 연속 1위 Top 5")
    st.dataframe(runs.sort_values("연속주", ascending=False).head(5)[["영화명", "연속주", "시작"]])


# 탭 ④ 연도별 관객 + 장르 비중
GENRE_CSV = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_genres.csv"
with tab4:
    w["연도"] = w["주시작일"].dt.year
    yearly = w[(w["연도"] >= 2005) & (w["연도"] <= 2025)].groupby("연도")["주간관객"].sum().reset_index()
    st.plotly_chart(px.line(yearly, x="연도", y="주간관객", markers=True, labels={"주간관객": "관객(주간 Top 10 합계)"}))
    genres = pd.read_csv(GENRE_CSV)[["영화코드", "대표장르"]]
    wg = w.merge(genres, on="영화코드", how="left").dropna(subset=["대표장르"])
    wg = wg[(wg["연도"] >= 2005) & (wg["연도"] <= 2025)]
    top6 = wg.groupby("대표장르")["주간관객"].sum().nlargest(6).index
    wg["장르"] = wg["대표장르"].where(wg["대표장르"].isin(top6), "기타")
    share = wg.pivot_table(index="연도", columns="장르", values="주간관객", aggfunc="sum").fillna(0)
    share = share.div(share.sum(axis=1), axis=0) * 100
    long = share.reset_index().melt(id_vars="연도", var_name="장르", value_name="비중(%)")
    st.plotly_chart(px.area(long, x="연도", y="비중(%)", color="장르"))
    fg = w.groupby(["영화코드", "영화명"]).agg(누적관객=("누적관객", "max")).reset_index().merge(genres, on="영화코드", how="left")
    pick = st.selectbox("장르", sorted(fg["대표장르"].dropna().unique()), index=sorted(fg["대표장르"].dropna().unique()).index("애니메이션"))
    gtop = fg[fg["대표장르"] == pick].sort_values("누적관객", ascending=False).head(10)
    st.plotly_chart(px.bar(gtop.iloc[::-1], y="영화명", x="누적관객", orientation="h", labels={"영화명": ""}))
    nation = pd.read_csv(GENRE_CSV)[["영화코드", "대표국가"]]
    fn = fg.merge(nation, on="영화코드", how="left").dropna(subset=["대표장르", "대표국가"])
    fn["국가"] = fn["대표국가"].where(fn["대표국가"].isin(["한국", "미국", "일본"]), "그 밖")
    top8 = fn.groupby("대표장르")["누적관객"].sum().nlargest(8).index
    fn["장르"] = fn["대표장르"].where(fn["대표장르"].isin(top8), "기타 장르")
    st.plotly_chart(px.sunburst(fn, path=["국가", "장르"], values="누적관객"))          # 안쪽 국가 → 바깥 장르
    top6 = fn[fn["장르"] != "기타 장르"].sort_values("누적관객", ascending=False).groupby("장르").head(6)
    st.plotly_chart(px.treemap(top6, path=["장르", "영화명"], values="누적관객"))     # 장르 상자 안의 영화 칸
    st.subheader("장르별 역대 1위")
    st.dataframe(fg.sort_values("누적관객", ascending=False).drop_duplicates("대표장르")[["대표장르", "영화명", "누적관객"]].head(12))

# 탭 ⑤ 스크린과 관객 산점도 (8장 학습 재료 kobis.csv)
with tab5:
    k = pd.read_csv("https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis.csv")
    k = k[k["스크린수"] >= 50]                                       # 스크린 50개 미만은 사전 상영
    k = k.merge(pd.read_csv(GENRE_CSV).drop_duplicates("영화명")[["영화명", "대표장르"]], on="영화명", how="left")
    k["대표장르"] = k["대표장르"].fillna("기타")             # kobis.csv에는 장르가 없어 이름으로 붙인다
    st.plotly_chart(px.scatter(k, x="스크린수", y="최종관객", color="대표장르", hover_name="영화명", hover_data=["개봉일", "관객수"]))

# ── 서울 실시간 혼잡도 지도 ────────────────────────────
KEY = st.secrets["SEOUL_KEY"]
BASE = "http://openapi.seoul.go.kr:8088"
# 121곳의 코드, 지역명, 위도, 경도, 분류 (5장처럼 raw 주소로 바로 읽기)
coords = pd.read_csv("https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul_area_all.csv")
pick = st.multiselect("분류", sorted(coords["분류"].unique()), default=sorted(coords["분류"].unique()))
coords = coords[coords["분류"].isin(pick)]

@st.cache_data(ttl=300)                        # 5분 동안은 기억해 둔 결과 재사용
def load_congestion(codes):
    rows = []
    for cd in codes:                           # 한 번에 한 곳씩 (단순 반복은 AI에게)
        r = requests.get(f"{BASE}/{KEY}/json/citydata_ppltn/1/5/{cd}")
        p = r.json()["SeoulRtd.citydata_ppltn"][0]
        age = {f"{k}대": float(p[f"PPLTN_RATE_{k}"]) for k in [0, 10, 20, 30, 40, 50, 60, 70]}
        rows.append({"코드": cd, "지역명": p["AREA_NM"], "혼잡도": p["AREA_CONGEST_LVL"],
                     "인구min": int(p["AREA_PPLTN_MIN"]), "인구max": int(p["AREA_PPLTN_MAX"]),
                     "비거주율": float(p["NON_RESNT_PPLTN_RATE"]),
                     "청년비율": age["20대"] + age["30대"], **age})
        time.sleep(0.1)
    return pd.DataFrame(rows)

order = ["여유", "보통", "약간 붐빔", "붐빔"]
size_map = {"여유": 9, "보통": 11, "약간 붐빔": 16, "붐빔": 22}   # 붐비는 곳은 큰 점

def congestion_map(df):
    df = df.copy(); df["크기"] = df["혼잡도"].map(size_map)
    return px.scatter_map(df, lat="위도", lon="경도", color="혼잡도", size="크기", size_max=22,
                          category_orders={"혼잡도": order}, color_discrete_sequence=["green", "gold", "orange", "red"],
                          hover_name="지역명", zoom=10, map_style="carto-positron")

now = load_congestion(tuple(coords["코드"])).merge(coords[["코드", "위도", "경도", "분류"]], on="코드")
st.subheader(f"지금 서울 {len(now)}곳")
st.plotly_chart(congestion_map(now))

# 누가 채우나: 청년 비율 지도 + 연령대 구성 + 비거주 버블
st.subheader("누가 채우고 있나")
st.plotly_chart(px.scatter_map(now, lat="위도", lon="경도", color="청년비율", size="인구max", size_max=26,
                               color_continuous_scale="Turbo", hover_name="지역명",
                               hover_data=["혼잡도", "비거주율"], zoom=10, map_style="carto-positron"))
AGES = [f"{k}대" for k in [0, 10, 20, 30, 40, 50, 60, 70]]
now["60대이상"] = now["60대"] + now["70대"]
pick12 = pd.concat([now.nlargest(6, "청년비율"), now.nlargest(6, "60대이상")])
long = pick12.melt(id_vars="지역명", value_vars=AGES, var_name="연령대", value_name="비율(%)")
st.plotly_chart(px.bar(long, x="지역명", y="비율(%)", color="연령대", barmode="stack",
                       category_orders={"연령대": AGES}))
st.plotly_chart(px.scatter(now, x="비거주율", y="청년비율", size="인구max", color="분류", size_max=40,
                           hover_name="지역명", hover_data=["혼잡도"],
                           labels={"비거주율": "비거주 인구 비율(%)", "청년비율": "20~30대 비율(%)"}))

# 실제 기록으로 보는 낮과 밤 (23곳, 10장에서 매시간 쌓는 표)
log = pd.read_csv("https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul_congestion_log.csv")
log["시각"] = pd.to_datetime(log["시각"]); log["시"] = log["시각"].dt.hour; log["일"] = log["시각"].dt.date
day = pd.Timestamp("2026-08-20").date()
c1, c2, c3 = st.columns(3)
for col, hour, label in [(c1, 14, "낮 2시"), (c2, 19, "저녁 7시"), (c3, 22, "밤 10시")]:
    snap = log[(log["일"] == day) & (log["시"] == hour)].drop_duplicates("지역명")
    col.caption(f"8월 20일 목요일 {label}")
    col.plotly_chart(congestion_map(snap), width="stretch")

hour = st.slider("시각을 골라 하루를 넘겨 보세요", 0, 23, 14)          # 0시부터 23시까지
pick_snap = log[(log["일"] == day) & (log["시"] == hour)].drop_duplicates("지역명")
st.plotly_chart(congestion_map(pick_snap), key="slider_map")          # 앞의 지도와 구분되게 이름표를 붙인다

level = {"여유": 0, "보통": 1, "약간 붐빔": 2, "붐빔": 3}
period = log[(log["일"] >= pd.Timestamp("2026-08-15").date()) & (log["일"] <= pd.Timestamp("2026-08-26").date())]
period = period.assign(등급=period["혼잡도"].map(level))
heat = period.pivot_table(index="지역명", columns="시", values="등급", aggfunc="mean")
heat = heat.loc[heat.mean(axis=1).sort_values(ascending=False).index]      # 붐비는 곳이 위에
st.plotly_chart(px.imshow(heat, color_continuous_scale=["green", "gold", "orange", "red"], zmin=0, zmax=3,
                          labels=dict(x="시각", y="", color="혼잡 등급"), aspect="auto"))
