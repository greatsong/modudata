# 9장 4절·5절(영화) - 첫 달 관객으로 최종 관객 맞히기 (인증키 불필요)
# 문화빅데이터플랫폼 "KOBIS 박스오피스 영화정보" 월별 CSV 28개(2024-01 ~ 2026-04)를
# 예제 저장소 주소(data/boxoffice_monthly/)에서 읽어 합치고, 전처리하고, 회귀와 군집까지 이어서 진행한다.
# 책에서는 내려받은 28개 파일을 직접 올리지만, 이 앱은 같은 파일을 저장소 주소에서 읽는다.
# 영화진흥위원회 답변(2026-10-02): 문화빅데이터플랫폼 CSV는 활용 제한 없음.
import re
from calendar import monthrange

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.preprocessing import StandardScaler

# 열 이름 열여덟 개의 뜻 (프롬프트 '파일 28개를 한 표로 합치기')
COLUMN_MEANING = {
    "NO": "그달 관객 수 순위",
    "MOVIE_NM": "영화명",
    "DRCTR_NM": "감독",
    "MAKR_NM": "제작사",
    "INCME_CMPNY_NM": "수입사",
    "DISTB_CMPNY_NM": "배급사",
    "OPN_DE": "개봉일",
    "MOVIE_TY_NM": "영화 유형(개봉영화·재개봉영화)",
    "MOVIE_STLE_NM": "영화 형태(장편·단편)",
    "NLTY_NM": "국적",
    "TOT_SCRN_CO": "상영한 스크린 수",
    "SALES_PRICE": "매출액(원)",
    "VIEWNG_NMPR_CO": "관객 수(명)",
    "SEOUL_SALES_PRICE": "서울 매출액(원)",
    "SEOUL_VIEWNG_NMPR_CO": "서울 관객 수(명)",
    "GENRE_NM": "장르",
    "GRAD_NM": "관람 등급",
    "MOVIE_SDIV_NM": "구분(일반영화·독립예술영화)",
}
NUM_COLS = ["NO", "TOT_SCRN_CO", "SALES_PRICE", "VIEWNG_NMPR_CO",
            "SEOUL_SALES_PRICE", "SEOUL_VIEWNG_NMPR_CO"]
TEXT_COLS = ["MOVIE_NM", "DRCTR_NM", "MAKR_NM", "INCME_CMPNY_NM", "DISTB_CMPNY_NM",
             "MOVIE_TY_NM", "MOVIE_STLE_NM", "NLTY_NM", "GENRE_NM", "GRAD_NM",
             "MOVIE_SDIV_NM"]
DEFECT_YM = "202511"          # 관객 수 합계가 이웃 달의 10분의 1인 달
BASE_URL = ("https://raw.githubusercontent.com/greatsong/modudata/main/data/"
            "boxoffice_monthly/KC_KOBIS_BOX_OFFIC_MOVIE_INFO_{}.csv")
YMS = [ts.strftime("%Y%m") for ts in pd.date_range("2024-01", "2026-04", freq="MS")]
EXCEL_EPOCH = pd.Timestamp("1899-12-30")


# ---------------------------------------------------------------- 프롬프트 '파일 28개를 한 표로 합치기'
def to_number(s):
    """쉼표와 공백을 지운 뒤 숫자로 바꾼다. 파일마다 표기가 달라서 필요하다."""
    cleaned = s.astype(str).str.replace(r'[",\s]', "", regex=True)
    return pd.to_numeric(cleaned.replace({"": None, "nan": None}), errors="coerce")


def file_ym(name):
    """파일 이름 끝 여섯 자리가 연월이다."""
    m = re.search(r"(\d{6})\.csv$", str(name))
    return m.group(1) if m else None


@st.cache_data
def load_files(files):
    """CSV 주소 목록을 받아 한 표로 합치고, 파일별 행 수를 함께 돌려준다."""
    frames, counts = [], []
    for f in files:
        name = getattr(f, "name", str(f))
        ym = file_ym(name)
        one = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        one.columns = [c.strip().lstrip("﻿") for c in one.columns]
        one["연월"] = ym
        counts.append({"파일": name.split("/")[-1], "연월": ym, "행 수": len(one)})
        frames.append(one)
    df = pd.concat(frames, ignore_index=True).sort_values("연월", kind="stable")
    for c in NUM_COLS:
        df[c] = to_number(df[c])
    for c in TEXT_COLS:
        df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan, "": np.nan})
    df["개봉일_원본"] = df["OPN_DE"].astype(str).str.replace('"', "", regex=False).str.strip()
    df["개봉일"] = pd.to_datetime(df["개봉일_원본"], format="%Y%m%d", errors="coerce")
    return df.reset_index(drop=True), pd.DataFrame(counts).sort_values("연월")


# ---------------------------------------------------------------- 프롬프트 '전처리 다섯 단계와 학습표 만들기'
def month_last_day(ts):
    return monthrange(ts.year, ts.month)[1]


def next_ym(ym):
    return (pd.Timestamp(ym + "01") + pd.offsets.MonthBegin(1)).strftime("%Y%m")


def clean_rows(df):
    """전처리 1~3단계. 단계마다 몇 행을 버리고 고쳤는지 기록한다."""
    log = []
    n0 = len(df)
    df = df.dropna(how="all", subset=list(COLUMN_MEANING))   # 원본 18개 열이 모두 빈 행
    log.append({"단계": "1. 내용이 전혀 없는 행 제거", "처리한 행": n0 - len(df), "남은 행": len(df)})

    n1 = len(df)
    df = df[df["NO"] <= 100]
    log.append({"단계": "2. 순위 100위까지만 남기기", "처리한 행": n1 - len(df), "남은 행": len(df)})

    serial = df["개봉일_원본"].str.fullmatch(r"\d{5}").fillna(False)
    df = df.copy()
    df.loc[serial, "개봉일"] = EXCEL_EPOCH + pd.to_timedelta(
        pd.to_numeric(df.loc[serial, "개봉일_원본"]), unit="D")
    log.append({"단계": "3. 개봉일 일련번호 복원", "처리한 행": int(serial.sum()), "남은 행": len(df)})
    return df.reset_index(drop=True), pd.DataFrame(log)


def build_movie_table(df):
    """전처리 4~5단계. 영화 한 편이 한 줄이 되게 표를 다시 만든다."""
    months = sorted(df["연월"].unique())
    first_ym, last_ym = months[0], months[-1]

    g = df.sort_values("연월").groupby(["MOVIE_NM", "개봉일"], dropna=False)
    rows = []
    for (name, opn), sub in g:
        yms = list(sub["연월"])
        aud = list(sub["VIEWNG_NMPR_CO"].fillna(0))
        rows.append({
            "영화명": name, "개봉일": opn,
            "첫달연월": yms[0], "마지막연월": yms[-1], "등장개월수": len(yms),
            "첫달관객": aud[0], "둘째달관객": (aud[1] if len(aud) > 1 else 0.0),
            "최종관객": float(np.sum(aud)),
            "스크린수": sub["TOT_SCRN_CO"].max(),
            "매출액": sub["SALES_PRICE"].fillna(0).sum(),
            "서울관객": sub["SEOUL_VIEWNG_NMPR_CO"].fillna(0).sum(),
            "장르": sub["GENRE_NM"].iloc[0], "국적": sub["NLTY_NM"].iloc[0],
            "등급": sub["GRAD_NM"].iloc[0], "배급사": sub["DISTB_CMPNY_NM"].iloc[0],
            "구분": sub["MOVIE_SDIV_NM"].iloc[0],
        })
    mv = pd.DataFrame(rows)
    mv["개봉연월"] = mv["개봉일"].dt.strftime("%Y%m")
    mv["첫달일수"] = mv["개봉일"].apply(
        lambda t: month_last_day(t) - t.day + 1 if pd.notna(t) else np.nan)

    log = []
    step = mv[mv["개봉연월"].between(first_ym, last_ym)]
    log.append({"단계": "개봉한 달이 자료 기간 안", "남은 편수": len(step)})
    step = step[step["개봉연월"] == step["첫달연월"]]
    log.append({"단계": "개봉한 달에 처음 나타남", "남은 편수": len(step)})
    step = step[step["첫달관객"] > 0]

    running = step[step["마지막연월"] == last_ym].copy()          # 아직 상영 중
    step = step[step["마지막연월"] != last_ym]
    log.append({"단계": f"{last_ym[:4]}년 {int(last_ym[4:])}월에 기록이 있는 영화 제외(상영 중)",
                "남은 편수": len(step)})

    hits = step["첫달연월"].apply(lambda y: DEFECT_YM in (y, next_ym(y)))
    step = step[~hits]
    log.append({"단계": f"{DEFECT_YM[:4]}년 {int(DEFECT_YM[4:])}월이 첫 달이거나 둘째 달인 영화 제외",
                "남은 편수": len(step)})

    train = step.reset_index(drop=True)
    train["첫달비율"] = train["첫달관객"] / train["최종관객"]
    running = running.reset_index(drop=True)
    for d in (train, running):                      # 표에 시각까지 나오지 않게 날짜만 남긴다
        d["개봉일"] = d["개봉일"].dt.date
    return train, running, pd.DataFrame(log), first_ym, last_ym


# ---------------------------------------------------------------- 프롬프트 '선형회귀 학습하고 평가하기'
CV = KFold(n_splits=5, shuffle=True, random_state=0)


def cv_scores(X, y, log=False):
    """5겹 교차검증으로 R²와 평균 절대 오차를 구한다. 예측값도 함께 돌려준다."""
    target = np.log1p(y) if log else y
    pred = cross_val_predict(LinearRegression(), X, target, cv=CV)
    if log:
        pred = np.expm1(pred)
    return r2_score(y, pred), mean_absolute_error(y, pred), pred


# ---------------------------------------------------------------- 화면 시작
st.set_page_config(page_title="첫 달 관객으로 최종 관객 맞히기", layout="wide")
st.title("첫 달 관객으로 최종 관객을 맞힐 수 있을까")

files = [BASE_URL.format(ym) for ym in YMS]

# ── 프롬프트 '파일 28개를 한 표로 합치기' ────────────────────────────
st.header("1. 파일을 합치고 열을 훑어보기")
st.subheader("열 이름 열여덟 개의 뜻")
st.dataframe(pd.DataFrame({"열 이름": list(COLUMN_MEANING),
                           "뜻": list(COLUMN_MEANING.values())}),
             hide_index=True, use_container_width=True)

raw, file_counts = load_files(files)
c1, c2 = st.columns([1, 2])
with c1:
    st.write(f"불러온 파일 {len(file_counts)}개")
    st.dataframe(file_counts[["연월", "행 수"]], hide_index=True, height=320)
with c2:
    보여줄열 = list(COLUMN_MEANING) + ["연월"]
    st.write(f"합친 표 {len(raw):,}행 × {len(보여줄열)}열")
    st.dataframe(raw[보여줄열].head(5), hide_index=True)

miss = (raw[list(COLUMN_MEANING)].isna().mean() * 100).round(1).reset_index()
miss.columns = ["열 이름", "빈 값 비율(%)"]
st.write("열별 빈 값의 비율")
st.dataframe(miss, hide_index=True, use_container_width=True)

# ── 프롬프트 '월별 합계를 그려 확인하기' ─────────────────────────────
st.header("2. 합계가 이상한 달 찾기")
monthly = raw.groupby("연월").agg(관객수합계=("VIEWNG_NMPR_CO", "sum")).reset_index()
top1 = raw.sort_values("NO").groupby("연월").first()["MOVIE_NM"]
monthly["1위 영화"] = monthly["연월"].map(top1)
monthly["연월표시"] = monthly["연월"].str[:4] + "." + monthly["연월"].str[4:]
fig = px.bar(monthly, x="연월표시", y="관객수합계", hover_data=["1위 영화"],
             labels={"연월표시": "연월", "관객수합계": "관객 수 합계(명)"})
fig.update_xaxes(type="category")     # 연월을 날짜가 아니라 글자로 다뤄야 눈금이 28개 그대로 나온다
st.plotly_chart(fig, use_container_width=True)

check = raw.groupby("연월").agg(국적_종류=("NLTY_NM", "nunique")).reset_index()
last100 = raw[raw["NO"] == 100].set_index("연월")["VIEWNG_NMPR_CO"]
check["100위 영화 관객 수"] = check["연월"].map(last100)
check = check.merge(monthly[["연월", "관객수합계"]], on="연월")
st.dataframe(check, hide_index=True, use_container_width=True)

empty_row = raw[list(COLUMN_MEANING)].isna().all(axis=1)
all_empty = int(empty_row.sum())
bad_date = int((~raw.loc[~empty_row, "개봉일_원본"].str.fullmatch(r"\d{8}").fillna(False)).sum())
over100 = int((raw["NO"] > 100).sum())
st.write(f"모든 열이 비어 있는 행 {all_empty}행 · "
         f"그 밖의 행 가운데 개봉일이 여덟 자리 날짜가 아닌 행 {bad_date}행 · "
         f"순위가 100을 넘는 행 {over100}행")

# ── 프롬프트 '전처리 다섯 단계와 학습표 만들기' ─────────────────────
st.header("3. 학습표 만들기")
clean, row_log = clean_rows(raw)
train, running, movie_log, FIRST_YM, LAST_YM = build_movie_table(clean)
c1, c2 = st.columns(2)
c1.dataframe(row_log, hide_index=True)
c2.dataframe(movie_log, hide_index=True)
st.write(f"학습표 {len(train):,}편 · 최종 관객 중앙값 {train['최종관객'].median():,.0f}명 · "
         f"최종 관객 100만 명 이상 {(train['최종관객'] >= 1_000_000).sum()}편 · "
         f"아직 상영 중이라 따로 보관한 영화 {len(running)}편")
SHOW = ["영화명", "개봉일", "첫달일수", "첫달관객", "둘째달관객", "최종관객", "등장개월수", "스크린수"]
st.dataframe(train.nlargest(10, "최종관객")[SHOW], hide_index=True, use_container_width=True)

# ── 프롬프트 '첫 달 관객과 최종 관객의 관계 보기' ────────────────────
st.header("4. 어떤 값이 예측에 도움이 될까")
train["구분색"] = np.where(train["영화명"].isin(train.nlargest(5, "최종관객")["영화명"]),
                           train["영화명"], "그 밖")
fig = px.scatter(train, x="첫달관객", y="최종관객", color="구분색",
                 log_x=True, log_y=True,
                 hover_data=["영화명", "개봉일", "첫달일수"],
                 labels={"첫달관객": "첫 달 관객(명)", "최종관객": "최종 관객(명)",
                         "구분색": ""})
st.plotly_chart(fig, use_container_width=True)

# ── 프롬프트 '첫 달 일수 확인하기' ──────────────────────────────────
band = pd.cut(train["첫달일수"], [0, 7, 14, 21, 31],
              labels=["1~7일", "8~14일", "15~21일", "22~31일"])
by_band = train.groupby(band, observed=False).agg(
    편수=("첫달관객", "size"),
    첫달관객중앙값=("첫달관객", "median"),
    첫달비율중앙값=("첫달비율", "median")).reset_index()
fig = px.bar(by_band, x="첫달일수", y="첫달비율중앙값",
             hover_data=["편수", "첫달관객중앙값"],
             labels={"첫달일수": "첫 달 일수", "첫달비율중앙값": "첫 달 관객 ÷ 최종 관객(중앙값)"})
st.plotly_chart(fig, use_container_width=True)
st.dataframe(by_band, hide_index=True, use_container_width=True)
st.write("구간마다 최종 관객이 가장 많은 영화 세 편")
st.dataframe(train.assign(구간=band).sort_values("최종관객", ascending=False)
             .groupby("구간", observed=False).head(3)
             .sort_values(["구간", "최종관객"], ascending=[True, False])
             [["구간"] + SHOW[:6]], hide_index=True, use_container_width=True)

# ── 프롬프트 '선형회귀 학습하고 평가하기' ───────────────────────────
st.header("5. 첫 달 관객에 얼마를 곱하면 될까")
y = train["최종관객"].values.astype(float)
r2_a, mae_a, _ = cv_scores(train[["첫달관객"]], y)
r2_b, mae_b, pred_b = cv_scores(train[["첫달관객", "첫달일수"]], y)

line = LinearRegression().fit(train[["첫달관객"]], y)
st.write(f"최종 관객 = {line.intercept_:,.0f} + {line.coef_[0]:.3f} × 첫 달 관객")

# ── 프롬프트 '로그로 바꿔 다시 학습하기' ────────────────────────────
log_feat = pd.DataFrame({"첫달관객_로그": np.log1p(train["첫달관객"]),
                         "첫달일수": train["첫달일수"]})
r2_c, mae_c, pred_c = cv_scores(log_feat, y, log=True)

score = pd.DataFrame([
    {"모델": "① 첫 달 관객", "R²": r2_a, "평균 절대 오차(명)": mae_a},
    {"모델": "② 첫 달 관객 + 첫 달 일수", "R²": r2_b, "평균 절대 오차(명)": mae_b},
    {"모델": "③ ②를 로그로 바꿔 학습", "R²": r2_c, "평균 절대 오차(명)": mae_c},
])
st.dataframe(score.style.format({"R²": "{:.3f}", "평균 절대 오차(명)": "{:,.0f}"}),
             hide_index=True, use_container_width=True)

# ── 프롬프트 '크게 빗나간 영화 찾기' ────────────────────────────────
st.header("6. 크게 빗나간 영화 살펴보기")
train["예측값"] = pred_b
train["오차"] = train["최종관객"] - train["예측값"]
fig = px.scatter(train, x="예측값", y="최종관객", log_x=True, log_y=True,
                 hover_data=["영화명"],
                 labels={"예측값": "예측한 최종 관객(명)", "최종관객": "실제 최종 관객(명)"})
lim = [train[["예측값", "최종관객"]].values.min(), train[["예측값", "최종관객"]].values.max()]
fig.add_trace(go.Scatter(x=lim, y=lim, mode="lines", name="예측 = 실제"))
st.plotly_chart(fig, use_container_width=True)

MISS = ["영화명", "개봉일", "첫달일수", "첫달관객", "둘째달관객", "최종관객", "예측값", "오차"]
under, over = train.nlargest(6, "오차"), train.nsmallest(6, "오차")
st.write("실제가 예측보다 훨씬 큰 영화")
st.dataframe(under[MISS].round(0), hide_index=True, use_container_width=True)
st.write(f"첫 달 일수 평균 {under['첫달일수'].mean():.1f}일")
st.write("예측이 실제보다 훨씬 큰 영화")
st.dataframe(over[MISS].round(0), hide_index=True, use_container_width=True)
st.write(f"첫 달 일수 평균 {over['첫달일수'].mean():.1f}일")

st.header("7. 로그 스케일로 바꿔 다시 학습하기")
train["로그예측값"] = pred_c
train["두모델차이"] = (train["로그예측값"] - train["예측값"]).abs()
st.write("바꾸기 전 모델과 로그 모델의 예측값 차이가 가장 큰 영화 다섯 편")
st.dataframe(train.nlargest(5, "두모델차이")
             [["영화명", "개봉일", "첫달일수", "첫달관객", "최종관객", "예측값", "로그예측값"]].round(0),
             hide_index=True, use_container_width=True)

# ── 프롬프트 '흥행 예측 카드 만들기' ────────────────────────────────
st.header("8. 흥행 예측 카드")
log_model = LinearRegression().fit(log_feat, np.log1p(y))
running = running.sort_values("첫달관객", ascending=False)
pick = st.selectbox("아직 상영 중이어서 학습표에서 뺀 영화", running["영화명"].tolist())
row = running[running["영화명"] == pick].iloc[0]
c1, c2 = st.columns(2)
m1 = c1.number_input("첫 달 관객(명)", value=int(row["첫달관객"]), step=1000)
days = c2.number_input("첫 달 일수(일)", value=int(row["첫달일수"]), min_value=1, max_value=31)

card = float(np.expm1(log_model.predict(pd.DataFrame(
    {"첫달관객_로그": [np.log1p(m1)], "첫달일수": [days]}))[0]))
c1, c2 = st.columns(2)
c1.metric("예측한 최종 관객", f"{card:,.0f}명")
c2.metric(f"{LAST_YM[:4]}년 {int(LAST_YM[4:])}월까지 파일에 쌓인 관객 수", f"{row['최종관객']:,.0f}명")
st.caption(
    f"학습에 사용한 영화 {len(train):,}편 · 자료 기간 {FIRST_YM[:4]}년 {int(FIRST_YM[4:])}월 ~ "
    f"{LAST_YM[:4]}년 {int(LAST_YM[4:])}월 · "
    f"로그 모델 R² {r2_c:.3f}, 평균 절대 오차 {mae_c:,.0f}명. "
    "이 예측은 첫 달 기록만 사용한 값입니다. 첫 달 기록이 비슷했던 과거 영화들이 "
    "평균적으로 어디까지 갔는지를 나타낸 값이므로 개별 영화는 여기서 크게 벗어날 수 있습니다.")

# ── 프롬프트 '다섯 특성으로 영화 묶기' ──────────────────────────────
st.header("9. 영화는 몇 가지 유형일까")
grp = train[train["최종관객"] >= 30_000].copy()
grp["둘째달비율"] = grp["둘째달관객"] / grp["최종관객"]
grp["서울관객비율"] = grp["서울관객"] / grp["최종관객"]
grp["1인당매출"] = grp["매출액"] / grp["최종관객"]
FEATS = ["첫달비율", "둘째달비율", "등장개월수", "서울관객비율", "1인당매출"]
grp = grp.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATS)
st.write(f"최종 관객 3만 명 이상 {len(grp)}편")

k = st.slider("군집 수", 3, 8, 6)
grp["군집"] = KMeans(n_clusters=k, n_init=30, random_state=0).fit_predict(
    StandardScaler().fit_transform(grp[FEATS])).astype(str)

mean_by = grp.groupby("군집")[FEATS].mean()
TYPE_ORDER = ["단기 소진형", "두 달 지속형", "월말 개봉형",
              "서울 예술영화형", "롱런형", "특별관·공연 실황형"]


def name_clusters(mean_by):
    """군집 번호는 실행할 때마다 달라질 수 있으므로 특성 평균을 보고 이름을 붙인다."""
    남은, 이름 = list(mean_by.index), {}
    for 열, 방향, 값 in [("1인당매출", "max", "특별관·공연 실황형"),
                         ("서울관객비율", "max", "서울 예술영화형"),
                         ("등장개월수", "max", "롱런형"),
                         ("첫달비율", "max", "단기 소진형"),
                         ("첫달비율", "min", "월말 개봉형")]:
        고른것 = (mean_by.loc[남은, 열].idxmax() if 방향 == "max"
                  else mean_by.loc[남은, 열].idxmin())
        이름[고른것] = 값
        남은.remove(고른것)
    이름[남은[0]] = "두 달 지속형"
    return 이름


# 여섯 군집일 때만 이름을 붙인다. 군집 수를 바꾸면 번호를 그대로 사용한다.
유형이름 = name_clusters(mean_by) if k == 6 else {c: c for c in mean_by.index}
grp["유형"] = grp["군집"].map(유형이름)
순서 = TYPE_ORDER if k == 6 else sorted(mean_by.index)

# 가로축은 1인당 매출, 세로축은 서울 관객 비율.
# 첫 달 비율과 둘째 달 비율은 합이 1에 가까워 점이 한 줄로 늘어서므로 축으로 쓰지 않는다.
fig = px.scatter(grp, x="1인당매출", y="서울관객비율", color="유형", size="최종관객",
                 category_orders={"유형": 순서}, size_max=28,
                 hover_data=["영화명", "첫달비율", "둘째달비율", "등장개월수"],
                 labels={"1인당매출": "1인당 매출(원)", "서울관객비율": "서울 관객 비율",
                         "유형": ""})
st.plotly_chart(fig, use_container_width=True)

summary = grp.groupby("군집").agg(
    편수=("영화명", "size"), 첫달비율=("첫달비율", "mean"), 둘째달비율=("둘째달비율", "mean"),
    등장개월수=("등장개월수", "mean"), 서울관객비율=("서울관객비율", "mean"),
    일인당매출=("1인당매출", "mean"), 최종관객중앙값=("최종관객", "median")).reset_index()
summary.insert(0, "유형", summary["군집"].map(유형이름))
summary["대표 영화"] = summary["군집"].map(
    grp.sort_values("최종관객", ascending=False).groupby("군집")["영화명"]
    .apply(lambda s: ", ".join(s.head(5))))
if k == 6:
    summary = summary.set_index("유형").loc[순서].reset_index()
st.dataframe(summary.style.format({"첫달비율": "{:.3f}", "둘째달비율": "{:.3f}",
                                   "등장개월수": "{:.2f}", "서울관객비율": "{:.3f}",
                                   "일인당매출": "{:,.0f}", "최종관객중앙값": "{:,.0f}"}),
             hide_index=True, use_container_width=True)
