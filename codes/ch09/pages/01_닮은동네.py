# 9장 5절 "닮은 동네끼리 묶어보기" - 책의 프롬프트 4개 순서대로 만든 앱 (인증키 불필요)
# 프롬프트 1: population_2026_05.csv 읽고 연령 비율 만들기
# 프롬프트 2: 표준화 + KMeans 5군집 + 평균 연령 곡선
# 프롬프트 3: 군집 수 슬라이더 2~10
# 프롬프트 4: 동네 검색 + 네 동네 표
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_2026_05.csv"

st.set_page_config(page_title="닮은 동네끼리 묶어보기", layout="wide")


# ---------------- 프롬프트 1 ----------------
@st.cache_data
def load():
    raw = pd.read_csv(URL, encoding="cp949", dtype=str)
    df = raw.copy()

    # 첫 열: "서울특별시 강남구 대치1동 (1168060000)" -> 이름 / 코드(문자열)
    first = df.columns[0]
    ext = df[first].str.extract(r"^(?P<동네이름>.*?)\s*\((?P<코드>[0-9]+)\)\s*$")
    df.insert(0, "코드", ext["코드"])
    df.insert(0, "동네이름", ext["동네이름"].str.strip())

    dup_code = int(df["코드"].duplicated().sum())
    dup_name = int(df["동네이름"].duplicated().sum())

    # 천 단위 쉼표 제거 후 숫자로
    num_cols = [c for c in df.columns if c not in ("동네이름", "코드", first)]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce")

    # 읍·면·동만 남기기 (이름이 읍/면/동으로 끝나는 행)
    n_all = len(df)
    dong = df[df["동네이름"].str.endswith(("읍", "면", "동"))].copy()
    n_dong = len(dong)

    # 남녀 합계(계)의 0세~100세 이상 연령 열 101개
    age_cols = [c for c in dong.columns if "_계_" in c and c.endswith("세") and "총인구수" not in c]
    age_cols += [c for c in dong.columns if "_계_" in c and c.endswith("100세 이상")]
    age_cols = list(dict.fromkeys(age_cols))
    # 0세 ... 100세 이상 순서 보장
    def age_key(c):
        tail = c.split("_계_")[-1]
        return 101 if "이상" in tail else int(tail.replace("세", ""))
    age_cols = sorted(age_cols, key=age_key)

    ages = dong[age_cols].astype(float)
    total = ages.sum(axis=1)

    zero_mask = total == 0
    n_zero = int(zero_mask.sum())

    keep = dong[~zero_mask].copy()
    ratio = ages[~zero_mask].div(total[~zero_mask], axis=0)
    ratio.columns = [age_key(c) for c in age_cols]  # 0..101(=100세 이상)
    ratio.index = keep.index

    keep = keep[["동네이름", "코드"]].reset_index(drop=True)
    ratio = ratio.reset_index(drop=True)
    return raw, keep, ratio, dict(n_all=n_all, n_dong=n_dong, n_zero=n_zero,
                                  dup_code=dup_code, dup_name=dup_name,
                                  n_final=len(keep), age_cols=age_cols)


raw, meta_df, ratio, info = load()

st.title("닮은 동네끼리 묶어보기")

st.header("1. 데이터 읽고 연령 비율 만들기")
c1, c2 = st.columns(2)
with c1:
    st.write(f"원본 크기: {raw.shape[0]:,}행 × {raw.shape[1]:,}열")
    st.write(f"코드 중복: {info['dup_code']}건 / 동네 이름 중복: {info['dup_name']}건")
    st.write(f"읍·면·동만 남긴 행: {info['n_dong']:,}곳")
    st.write(f"연령 인구 합이 0이라 제외한 동네: {info['n_zero']}곳")
    st.write(f"**최종 {info['n_final']:,}곳**")
with c2:
    st.write("열 이름 앞부분")
    st.write(list(raw.columns[:6]))
st.write("동네 이름과 코드로 나눈 결과 + 연령 비율(%) 앞부분")
preview = meta_df.head(5).copy()
for _a in [0, 1, 2, 3, 4]:
    preview[f"{_a}세 비율(%)"] = (ratio[_a].head(5) * 100).round(2).values
st.dataframe(preview, hide_index=True, width="stretch", key="tbl_head")


# ---------------- 프롬프트 2 / 3 ----------------
X = ratio.values
scaled = StandardScaler().fit_transform(X)


@st.cache_data
def run_kmeans(k):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    return km.fit_predict(scaled)


def band(df_ratio, lo, hi):
    cols = [c for c in df_ratio.columns if lo <= c <= hi]
    return df_ratio[cols].sum(axis=1)


band_0_19 = band(ratio, 0, 19)
band_20_39 = band(ratio, 20, 39)
band_60up = band(ratio, 60, 101)

age_axis = [c if c <= 100 else 100 for c in ratio.columns]
age_label = [f"{c}세" if c <= 100 else "100세 이상" for c in ratio.columns]


def draw(labels, k):
    fig = go.Figure()
    rows = []
    for g in range(k):
        m = labels == g
        n = int(m.sum())
        mean_ratio = ratio[m].mean(axis=0) * 100
        fig.add_trace(go.Scatter(x=age_label, y=mean_ratio.values, mode="lines",
                                 name=f"군집 {g} ({n:,}곳)"))
        rows.append({
            "군집": g,
            "동네 수": n,
            "0~19세": round(band_0_19[m].mean() * 100, 1),
            "20~30대": round(band_20_39[m].mean() * 100, 1),
            "60세 이상": round(band_60up[m].mean() * 100, 1),
        })
    tickvals = [lab for lab in age_label if lab == "100세 이상" or int(lab.replace("세", "")) % 10 == 0]
    fig.update_layout(xaxis_title="연령", yaxis_title="평균 비율(%)",
                      legend_title="군집", height=520,
                      margin=dict(l=60, r=20, t=20, b=50))
    fig.update_xaxes(tickmode="array", tickvals=tickvals, ticktext=tickvals, tickangle=0)
    return fig, pd.DataFrame(rows)


st.header("2. 표준화 후 KMeans 5개 군집")
labels5 = run_kmeans(5)
fig5, table5 = draw(labels5, 5)
st.plotly_chart(fig5, width="stretch", key="chart5", config={"displayModeBar": False})
st.dataframe(table5, hide_index=True, width="stretch", key="tbl5")

st.header("3. 군집 수를 바꿔 보기")
k = st.slider("군집 수", min_value=2, max_value=10, value=5, step=1)
st.write(f"현재 선택한 군집 수: **{k}개**")
labels_k = run_kmeans(k)
figk, tablek = draw(labels_k, k)
st.plotly_chart(figk, width="stretch", key="chartk", config={"displayModeBar": False})
st.dataframe(tablek, hide_index=True, width="stretch", key="tblk", height=35 * len(tablek) + 40)


# ---------------- 프롬프트 4 ----------------
st.header("4. 동네 검색")
base = meta_df.copy()
base["군집"] = labels5
size5 = pd.Series(labels5).value_counts()

q = st.text_input("동네 이름으로 검색", value="대치1동")
if q:
    hit = base[base["동네이름"].str.contains(q, na=False)].copy()
    if len(hit) == 0:
        st.warning("검색 결과가 없습니다.")
    else:
        hit["같은 군집 동네 수"] = hit["군집"].map(size5)
        st.dataframe(hit[["동네이름", "코드", "군집", "같은 군집 동네 수"]],
                     hide_index=True, width="stretch")

st.subheader("대치1동 · 귀인동 · 중계1동 · 둔산1동")
four = []
for name in ["대치1동", "귀인동", "중계1동", "둔산1동"]:
    sub = base[base["동네이름"].str.contains(name, na=False)]
    for _, r in sub.iterrows():
        four.append({"찾은 이름": name, "행정구역": r["동네이름"], "코드": r["코드"],
                     "군집": int(r["군집"]), "같은 군집 동네 수": int(size5[r["군집"]])})
st.dataframe(pd.DataFrame(four), hide_index=True, width="stretch")
