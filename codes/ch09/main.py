"""
9장 2·3절 - 2050년 서울 평균 기온 예측 (인증키 불필요)

책의 프롬프트 순서대로 만든 스트림릿 앱이다.
  1. seoul_daily.csv 읽기 → 열 이름, 기간, 결측, 중복, 350일 기준, 제외한 연도
  2. 연도별 평균 기온 산점도(가장 더운 다섯 해와 가장 추운 다섯 해 색 구분)
  3. 선형회귀와 2050년 예측, 점선 연장, y = ax + b
  4. 학습 데이터의 R²
  5. 다항회귀 1·2·3·9차(2004년까지 학습, 2005년부터 평가)와 20차 추가
  6. 학습 기간 네 가지(전체, 최근 50년, 30년, 20년) 선형회귀 비교

서울 기온 파일은 날마다 갱신되므로 수치는 책과 조금 다를 수 있다.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures

st.set_page_config(page_title="서울 기온 예측", layout="wide")

CSV_URL = "https://raw.githubusercontent.com/greatsong/modudata/refs/heads/main/data/seoul_daily.csv"
MIN_DAYS = 350


# ---------------------------------------------------------------- P1
@st.cache_data
def load_data():
    return pd.read_csv(CSV_URL, parse_dates=["날짜"])


st.title("2050년 서울 평균기온 예측")

df = load_data()

st.header("1. 데이터 확인")
st.write("열 이름:", list(df.columns))
st.write(
    f"기록 기간: {df['날짜'].min().date()} ~ {df['날짜'].max().date()} "
    f"(전체 {len(df):,}행)"
)
st.write(f"평균기온 결측 수: {int(df['평균기온'].isna().sum())}개")

dup = int(df["날짜"].duplicated().sum())
st.write(f"중복된 날짜 수: {dup}개" + ("" if dup else " (중복 없음)"))

df["연도"] = df["날짜"].dt.year
# "평균기온이 있는 날짜" 수는 파일에 등장하는 모든 연도에 대해 센다.
# (평균기온이 한 건도 없는 1951·1952도 '0일'로 함께 보이게 하기 위해서다.)
by_year = (
    df.groupby("연도")
    .agg(연평균기온=("평균기온", "mean"), 유효날짜수=("평균기온", "count"))
    .reset_index()
)

kept = by_year[by_year["유효날짜수"] >= MIN_DAYS].reset_index(drop=True)
dropped = by_year[by_year["유효날짜수"] < MIN_DAYS].reset_index(drop=True)

st.subheader(f"분석에서 제외한 연도 ({len(dropped)}개)")
st.dataframe(
    dropped[["연도", "유효날짜수"]].astype({"연도": str}),
    hide_index=True,
    use_container_width=False,
)
st.success(
    f"유효 날짜 {MIN_DAYS}일 이상인 연도 {len(kept)}개 "
    f"({int(kept['연도'].min())}~{int(kept['연도'].max())})"
)


# ---------------------------------------------------------------- P2
st.header("2. 연도별 평균기온 산점도")

kept = kept.sort_values("연도").reset_index(drop=True)
hot5 = kept.nlargest(5, "연평균기온")
cold5 = kept.nsmallest(5, "연평균기온")
rest = kept[~kept["연도"].isin(pd.concat([hot5, cold5])["연도"])]

HOVER = "연도 %{x}<br>평균기온 %{y:.2f}℃<br>날짜 수 %{customdata}일<extra></extra>"


def scatter(part, name, color, size=7):
    return go.Scatter(
        x=part["연도"],
        y=part["연평균기온"],
        customdata=part["유효날짜수"],
        mode="markers",
        name=name,
        marker=dict(color=color, size=size),
        hovertemplate=HOVER,
    )


def labels(part, color, dy):
    return go.Scatter(
        x=part["연도"],
        y=part["연평균기온"],
        mode="text",
        text=part["연도"].astype(str),
        textposition="top center" if dy > 0 else "bottom center",
        textfont=dict(color=color, size=11),
        showlegend=False,
        hoverinfo="skip",
    )


fig2 = go.Figure(
    [
        scatter(rest, "그 외 연도", "#9aa4b2"),
        scatter(hot5, "가장 더운 5해", "#d62728", 11),
        scatter(cold5, "가장 추운 5해", "#1f77b4", 11),
        labels(hot5, "#d62728", 1),
        labels(cold5, "#1f77b4", -1),
    ]
)
fig2.update_layout(
    xaxis_title="연도",
    yaxis_title="연평균기온(℃)",
    height=480,
    hovermode="closest",
)
st.plotly_chart(fig2, use_container_width=True)

c1, c2 = st.columns(2)
c1.write("가장 더운 다섯 해")
c1.dataframe(
    hot5.sort_values("연평균기온", ascending=False).astype({"연도": str}),
    hide_index=True,
)
c2.write("가장 추운 다섯 해")
c2.dataframe(
    cold5.sort_values("연평균기온").astype({"연도": str}), hide_index=True
)


# ---------------------------------------------------------------- P3
st.header("3. 선형회귀로 2050년 예측하기")

X = kept[["연도"]].values
y = kept["연평균기온"].values

lin = LinearRegression().fit(X, y)
a = float(lin.coef_[0])
b = float(lin.intercept_)
last_year = int(kept["연도"].max())
pred_2050 = float(lin.predict([[2050]])[0])

past_years = np.arange(int(kept["연도"].min()), last_year + 1)
future_years = np.arange(last_year, 2051)

fig3 = go.Figure(
    [
        scatter(kept, "연평균기온", "#9aa4b2"),
        go.Scatter(
            x=past_years,
            y=lin.predict(past_years.reshape(-1, 1)),
            mode="lines",
            name="선형회귀 직선",
            line=dict(color="#d62728", width=3),
        ),
        go.Scatter(
            x=future_years,
            y=lin.predict(future_years.reshape(-1, 1)),
            mode="lines",
            name="과거 추세를 연장한 값",
            line=dict(color="#d62728", width=3, dash="dash"),
        ),
        go.Scatter(
            x=[2050],
            y=[pred_2050],
            mode="markers+text",
            name="2050년 예측",
            marker=dict(color="#ff7f0e", size=14, symbol="star"),
            text=[f"2050년 {pred_2050:.2f}℃"],
            textposition="top center",
        ),
    ]
)
fig3.add_vline(x=last_year, line_dash="dot", line_color="#888")
fig3.add_annotation(
    x=(last_year + 2050) / 2,
    y=min(y),
    text="과거 추세를 연장한 값",
    showarrow=False,
    font=dict(color="#888"),
)
fig3.update_layout(xaxis_title="연도", yaxis_title="연평균기온(℃)", height=480)
st.plotly_chart(fig3, use_container_width=True)

st.latex(rf"y = {a:.6f}x {'+' if b >= 0 else '-'} {abs(b):.2f}")
m1, m2, m3 = st.columns(3)
m1.metric("기울기 a", f"{a:.6f}")
m2.metric("y절편 b", f"{b:.2f}")
m3.metric("2050년 예측", f"{pred_2050:.2f} ℃")


# ---------------------------------------------------------------- P4
st.header("4. 학습 데이터에 대한 R²")
r2_train_all = r2_score(y, lin.predict(X))
st.metric("학습 데이터 R²", f"{r2_train_all:.4f}")


# ---------------------------------------------------------------- P5 / P6
st.header("5. 다항회귀 1·2·3·9·20차 비교")

train = kept[kept["연도"] <= 2004]
test = kept[kept["연도"] >= 2005]

# "연도는 학습용 데이터만 이용해 계산하기 편한 값으로 바꾼 뒤" →
# 학습 구간의 첫 연도를 0으로 놓는 이동(shift). 평가용에도 같은 기준을 적용한다.
base_year = int(train["연도"].min())


def shift(years):
    return np.asarray(years, dtype=float) - base_year


Xtr = shift(train["연도"]).reshape(-1, 1)
ytr = train["연평균기온"].values
Xte = shift(test["연도"]).reshape(-1, 1)
yte = test["연평균기온"].values

DEGREES = [1, 2, 3, 9, 20]
rows = []
curves = {}
grid = np.arange(int(kept["연도"].min()), 2051)

for d in DEGREES:
    model = make_pipeline(PolynomialFeatures(d), LinearRegression()).fit(Xtr, ytr)
    rows.append(
        {
            "차수": f"{d}차",
            "학습 R²": round(float(r2_score(ytr, model.predict(Xtr))), 4),
            "평가 R²": round(float(r2_score(yte, model.predict(Xte))), 4),
            "2050년 예측": round(float(model.predict(shift([2050]).reshape(-1, 1))[0]), 2),
        }
    )
    curves[d] = model.predict(shift(grid).reshape(-1, 1))

st.dataframe(pd.DataFrame(rows), hide_index=True)

show20 = st.checkbox("20차 곡선도 그래프에 표시", value=True)

fig5 = go.Figure(
    [
        scatter(train, "학습용(~2004)", "#1f77b4"),
        scatter(test, "평가용(2005~)", "#2ca02c"),
    ]
)
palette = {1: "#d62728", 2: "#ff7f0e", 3: "#9467bd", 9: "#8c564b", 20: "#e377c2"}
for d in DEGREES:
    if d == 20 and not show20:
        continue
    fig5.add_trace(
        go.Scatter(x=grid, y=curves[d], mode="lines", name=f"{d}차", line=dict(color=palette[d]))
    )
fig5.add_vline(x=2004.5, line_dash="dot", line_color="#888")
fig5.update_xaxes(range=[int(kept["연도"].min()) - 2, last_year + 2])      # 학습·평가 구간에 맞춰 보기
fig5.update_yaxes(range=[float(y.min()) - 1, float(y.max()) + 1])
fig5.update_layout(xaxis_title="연도", yaxis_title="연평균기온(℃)", height=520)
st.plotly_chart(fig5, use_container_width=True)

# 20차 곡선을 2050년까지 연장한 그래프는 따로 그린다.
st.subheader("20차 곡선을 2050년까지 연장한 그래프")
fig6 = go.Figure(
    [
        scatter(train, "학습용(~2004)", "#1f77b4"),
        scatter(test, "평가용(2005~)", "#2ca02c"),
        go.Scatter(x=grid, y=curves[20], mode="lines", name="20차", line=dict(color=palette[20])),
    ]
)
fig6.add_vline(x=2004.5, line_dash="dot", line_color="#888")
fig6.update_layout(xaxis_title="연도", yaxis_title="연평균기온(℃)", height=520)
st.plotly_chart(fig6, use_container_width=True)


# ---------------------------------------------------------------- P7
st.header("6. 학습 기간을 바꿔 가며 선형회귀")

with st.container(key="period_section"):
    END_YEAR = last_year            # 네 기간 모두 데이터의 마지막 해를 끝 연도로 맞춘다
    periods = [
        ("전체 기간", None),
        ("최근 50년", 50),
        ("최근 30년", 30),
        ("최근 20년", 20),
    ]
    prows = []
    plines = {}
    for name, n in periods:
        part = kept if n is None else kept[
            (kept["연도"] >= END_YEAR - n + 1) & (kept["연도"] <= END_YEAR)
        ]
        Xp = part[["연도"]].values
        yp = part["연평균기온"].values
        m = LinearRegression().fit(Xp, yp)
        prows.append(
            {
                "학습 기간": name,
                "연도 수": len(part),
                "시작 연도": int(part["연도"].min()),
                "끝 연도": int(part["연도"].max()),
                "100년당 기울기(℃)": round(float(m.coef_[0]) * 100, 2),
                "2050년 예측(℃)": round(float(m.predict([[2050]])[0]), 2),
            }
        )
        xs = np.arange(int(part["연도"].min()), 2051)
        plines[name] = (xs, m.predict(xs.reshape(-1, 1)))

    ptable = pd.DataFrame(prows)
    st.dataframe(
        ptable.assign(**{
            "100년당 기울기(℃)": ptable["100년당 기울기(℃)"].map("{:.2f}".format),
            "2050년 예측(℃)": ptable["2050년 예측(℃)"].map("{:.2f}".format),
        }),
        hide_index=True,
        use_container_width=True,
    )

    fig7 = go.Figure([scatter(kept, "연평균기온", "#b7bec9")])
    pcolor = {
        "전체 기간": "#1f77b4",
        "최근 50년": "#2ca02c",
        "최근 30년": "#ff7f0e",
        "최근 20년": "#d62728",
    }
    for name, _ in periods:
        xs, ys = plines[name]
        fig7.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=name,
                line=dict(color=pcolor[name], width=3),
            )
        )
    fig7.add_vline(x=END_YEAR, line_dash="dot", line_color="#888")
    fig7.update_layout(
        title="학습 기간을 달리한 네 직선",
        xaxis_title="연도",
        yaxis_title="연평균기온(℃)",
        height=520,
        legend=dict(orientation="h", y=1.02, yanchor="bottom"),
    )
    st.plotly_chart(fig7, use_container_width=True)
