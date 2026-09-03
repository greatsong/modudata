# 8장 전체 코드 - 머신러닝 병아리반 '작은 AI 실험실' (2026-09-04)
# 데이터는 예제 저장소 raw 주소로 바로 읽는다. 키가 필요 없어 배포에 시크릿이 없다.
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

RAW = "https://raw.githubusercontent.com/greatsong/modudata/main/data/"
st.title("작은 AI 실험실")
tab1, tab2, tab3 = st.tabs(["2050년 서울 기온", "흥행 계산기", "우리 동네는 무슨 무리"])

# ── 탭 ① 회귀: 서울은 정말 더워지는가 ──────────────────────
@st.cache_data
def load_temp():
    df = pd.read_csv(RAW + "seoul_daily.csv")
    df["날짜"] = pd.to_datetime(df["날짜"]); df["연도"] = df["날짜"].dt.year
    return df
df = load_temp()
g = df.dropna(subset=["평균기온"]).groupby("연도")
yearly = g["평균기온"].mean()[g["평균기온"].count() >= 350].reset_index()   # 반쪽짜리 해는 뺀다
yearly.columns = ["연도", "연평균기온"]
tropical = df[df["연도"].isin(yearly["연도"])].groupby("연도").agg(열대야=("최저기온", lambda s: int((s >= 25).sum())),
                                                               폭염=("최고기온", lambda s: int((s >= 33).sum()))).reset_index()
with tab1:
    hot = yearly.nlargest(5, "연평균기온")["연도"]; cold = yearly.nsmallest(5, "연평균기온")["연도"]
    yearly["구분"] = np.where(yearly["연도"].isin(hot), "가장 더운 5년", np.where(yearly["연도"].isin(cold), "가장 추운 5년", "그 밖"))
    st.plotly_chart(px.scatter(yearly, x="연도", y="연평균기온", color="구분", hover_data=["연도", "연평균기온"]))

    lin = LinearRegression().fit(yearly[["연도"]], yearly["연평균기온"])       # 학습은 이 한 줄
    st.write("R²:", round(r2_score(yearly["연평균기온"], lin.predict(yearly[["연도"]])), 2),
             "| 100년당 상승:", round(lin.coef_[0] * 100, 1), "℃")
    # 과적합 실험: 2005년 이전은 공부용, 이후는 시험용, 차수는 슬라이더로
    tr, te = yearly[yearly["연도"] < 2005], yearly[yearly["연도"] >= 2005]
    deg = st.slider("곡선의 차수", 1, 9, 1)
    m = make_pipeline(PolynomialFeatures(deg), StandardScaler(), LinearRegression()).fit(tr[["연도"]], tr["연평균기온"])
    mae = mean_absolute_error(te["연평균기온"], m.predict(te[["연도"]]))
    st.write(f"{deg}차 - 시험 오차 {mae:.2f}℃ / 2050년 {m.predict(pd.DataFrame({'연도': [2050]}))[0]:.1f}℃")
    xs = pd.DataFrame({"연도": range(1908, 2051)})
    fig = go.Figure(); fig.add_scatter(x=yearly["연도"], y=yearly["연평균기온"], mode="markers", name="실제")
    fig.add_scatter(x=xs["연도"], y=m.predict(xs), mode="lines", name=f"{deg}차 곡선"); st.plotly_chart(fig)

    # 예측기: 연도 슬라이더 → 연평균기온·열대야 카드
    lin_t = LinearRegression().fit(tropical[["연도"]], tropical["열대야"])
    year = st.slider("예측할 연도", 2026, 2100, 2050)
    c1, c2 = st.columns(2)
    c1.metric(f"{year}년 예측 연평균기온", f"{lin.predict(pd.DataFrame({'연도': [year]}))[0]:.1f}℃")
    c2.metric(f"{year}년 예측 열대야", f"{max(0, lin_t.predict(pd.DataFrame({'연도': [year]}))[0]):.0f}일")
    if year > 2050:
        st.caption("학습한 범위 밖이라 참고만 하세요")
    st.plotly_chart(px.bar(tropical[tropical["연도"] >= 1990].melt(id_vars="연도", var_name="종류", value_name="일수"),
                           x="연도", y="일수", color="종류", barmode="group"))

# ── 탭 ② 트리 세 형제: 흥행 예측 (7장 kobis.csv) ─────────────
@st.cache_data
def load_box():
    box = pd.read_csv(RAW + "kobis.csv")
    box["개봉일"] = pd.to_datetime(box["개봉일"], errors="coerce")
    two_months_ago = pd.Timestamp.today() - pd.Timedelta(days=60)
    box = box[(box["개봉일"] <= two_months_ago) & (box["스크린수"] >= 50)].dropna(subset=["최종관객"])  # 두 달 규칙 + 사전 상영 제외
    box["열기"] = box["관객수"] / box["상영횟수"]                                                       # 개봉 당일 관객 ÷ 상영 횟수
    return box
box = load_box()
with tab2:
    st.write("학습에 쓸 영화 수:", len(box))
    feat = ["스크린수", "상영횟수", "순위"]
    yb = np.log1p(box["최종관객"])                                                        # 관객 수는 로그로
    Xtr, Xte, ytr, yte = train_test_split(box[feat], yb, test_size=0.2, random_state=42)  # 결과가 매번 같게
    for 이름, m in {"선형회귀": LinearRegression(), "랜덤포레스트": RandomForestRegressor(random_state=42),
                   "부스팅": GradientBoostingRegressor(random_state=42)}.items():
        m.fit(Xtr, ytr); st.write(이름, "R²", round(r2_score(yte, m.predict(Xte)), 2))
    feat2 = feat + ["열기"]
    Xtr, Xte, ytr, yte = train_test_split(box[feat2], yb, test_size=0.2, random_state=42)
    rf = RandomForestRegressor(random_state=42).fit(Xtr, ytr)
    st.write("열기를 더한 랜덤포레스트 R²", round(r2_score(yte, rf.predict(Xte)), 2))
    test = box.loc[Xte.index].assign(예측=np.expm1(rf.predict(Xte)).astype(int))
    st.plotly_chart(px.scatter(test, x="예측", y="최종관객", hover_name="영화명", hover_data=["개봉일", "스크린수"],
                               log_x=True, log_y=True))
    st.plotly_chart(px.bar(x=rf.feature_importances_, y=feat2, orientation="h", labels={"x": "특성 중요도", "y": ""}))
    # 흥행 계산기
    st.subheader("흥행 계산기")
    s, sh, r, a = (st.number_input("개봉일 스크린 수", 1, 3000, 800), st.number_input("개봉일 상영 횟수", 1, 20000, 3000),
                   st.number_input("개봉일 순위", 1, 10, 1), st.number_input("개봉일 관객 수", 1, 2000000, 100000))
    guess = np.expm1(rf.predict(pd.DataFrame([[s, sh, r, a / sh]], columns=feat2)))[0]
    st.metric("예상 최종 관객", f"{guess:,.0f}명")

# ── 탭 ③ 군집: 닮은 동네끼리 (정답이 없는 비지도학습) ─────────
@st.cache_data
def load_pop():
    pop = pd.read_csv(RAW + "population_latest.csv", encoding="cp949", thousands=",")
    이름칸 = pop.columns[0]
    동만 = pop[이름칸].str.split("(").str[0].str.strip().str.endswith(("동", "읍", "면"))
    pop = pop[동만].copy()                                           # 시도, 시군구 합계 행 빼기
    연령 = [c for c in pop.columns if "계_" in c and "세" in c]
    pop = pop[pop[[c for c in pop.columns if "총인구수" in c][0]] > 0]
    비율 = pop[연령].div(pop[연령].sum(axis=1), axis=0)               # ① 비율로
    X2 = StandardScaler().fit_transform(비율)                        # ② 같은 저울로
    km = KMeans(n_clusters=5, n_init=10, random_state=42).fit(X2)    # k=5는 사람이 정한다, 번호는 고정
    pop["무리"] = km.labels_; pop["이름"] = pop[이름칸].str.split("(").str[0].str.strip()
    return pop, 비율, 연령
pop, 비율, 연령 = load_pop()
with tab3:
    st.write(pop["무리"].value_counts().sort_index())
    prof = 비율.groupby(pop["무리"]).mean()
    fig = go.Figure()
    for c in prof.index:
        fig.add_scatter(x=list(range(len(연령))), y=prof.loc[c].values * 100, mode="lines", name=f"무리 {c}")
    fig.update_layout(xaxis_title="나이", yaxis_title="비율(%)"); st.plotly_chart(fig)
    young = 비율.iloc[:, 20:40].sum(axis=1) * 100; old = 비율.iloc[:, 60:].sum(axis=1) * 100
    st.plotly_chart(px.scatter(x=young, y=old, color=pop["무리"].astype(str), hover_name=pop["이름"],
                               labels={"x": "20~30대 비율(%)", "y": "60세 이상 비율(%)", "color": "무리"}))
    name = st.text_input("동네 이름", "대치1동")
    hit = pop[pop["이름"].str.contains(name)]
    if len(hit):
        c = int(hit.iloc[0]["무리"])
        st.write(f"{hit.iloc[0]['이름']}은(는) 무리 {c}입니다. 같은 무리:", ", ".join(pop[pop["무리"] == c]["이름"].head(5)))
