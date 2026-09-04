# 9장 6절 - Supabase에 점심 투표를 저장하는 앱
# 실행 조건: [Settings] → [Secrets]에 SUPABASE_URL, SUPABASE_KEY(공개용 anon 키) 등록
import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client

MENUS = ["김치찌개", "된장찌개", "돈까스", "비빔밥", "냉면", "샐러드"]

@st.cache_resource                      # 연결은 한 번만 만들어 두고 계속 재사용한다
def connect():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = connect()
st.title("민주적 점심 - Supabase 판")
st.caption("별명과 메뉴만 받습니다. 실명이나 연락처는 묻지 않습니다.")

name = st.text_input("별명")
menu = st.selectbox("메뉴", MENUS)
if st.button("이 메뉴에 한 표"):
    if name.strip():
        sb.table("votes").insert({"name": name.strip(), "menu": menu}).execute()   # 이 한 줄이 저장이다
        st.success("한 표, 잘 받았습니다")
    else:
        st.warning("별명을 먼저 적어 주세요")

rows = sb.table("votes").select("name, menu").execute().data
if not rows:
    st.info("아직 표가 없습니다. 첫 표를 던져 주세요.")
    st.stop()

df = pd.DataFrame(rows)
count = df["menu"].value_counts().rename_axis("메뉴").reset_index(name="표")
top = count.iloc[0]["메뉴"]                                                    # 가장 많은 메뉴를 강조
count["강조"] = count["메뉴"].eq(top).map({True: "1위", False: "그 밖"})
st.subheader(f"지금 1위는 {top}")
fig = px.bar(count.iloc[::-1], x="표", y="메뉴", orientation="h", text="표", color="강조",
             color_discrete_map={"1위": "#F08A24", "그 밖": "#D8DEE6"}, labels={"메뉴": ""})
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(showlegend=False, height=320, xaxis=dict(dtick=1, title=None))
st.plotly_chart(fig, width="stretch")
