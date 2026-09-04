# 9장 개선판 - 민주적 점심 개표 방송 (구글 시트 저장)
# 실행 조건: 스트림릿 클라우드 [Settings] → [Secrets]에 SHEET_URL(.../exec) 등록
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd
import plotly.express as px
import streamlit as st

SHEET_URL = st.secrets["SHEET_URL"]
KST = timezone(timedelta(hours=9))
MENUS = ["김치찌개", "된장찌개", "돈까스", "비빔밥", "냉면", "샐러드"]
CREAM, ORANGE, DEEP = "#FFF7EC", "#F08A24", "#C25A0E"

st.set_page_config(page_title="민주적 점심 개표 방송", page_icon="🍚")
st.markdown(f"""<style>
    .stApp {{ background: {CREAM}; }}
    .headline {{ text-align:center; color:{DEEP}; font-size:0.95rem; letter-spacing:0.12em; margin-bottom:0.2rem; }}
    .winner {{ text-align:center; color:{ORANGE}; font-size:4.2rem; font-weight:800; line-height:1.15; margin:0.1rem 0 0.6rem; }}
    .bubble {{ background:#fff; border:2px solid {ORANGE}; border-radius:18px; padding:0.9rem 1.2rem;
               color:{DEEP}; font-size:1.05rem; text-align:center; margin:0.4rem 0 1rem; }}
    .counting {{ text-align:center; color:{DEEP}; font-size:1.6rem; font-weight:700; margin:1rem 0; }}
</style>""", unsafe_allow_html=True)

st.title("민주적 점심")
st.caption("오늘 점심, 개표 방송으로 정합니다")


def save(member, menu, type_):
    """접수창구에 값을 보내 시트에 한 줄을 쌓는다. 한글이 깨지지 않게 params로 넘긴다."""
    requests.get(SHEET_URL, params={"member": member, "menu": menu, "type": type_}, timeout=10)


@st.cache_data(ttl=10)
def load():
    """접수창구를 값 없이 열면 전체 기록이 표로 온다. 첫 줄은 머리글이다."""
    rows = requests.get(SHEET_URL, timeout=10).json()
    if len(rows) <= 1:
        return pd.DataFrame(columns=["시각", "팀원", "메뉴", "구분"])
    df = pd.DataFrame(rows[1:], columns=["시각", "팀원", "메뉴", "구분"])
    df["시각"] = df["시각"].astype(str).str.lstrip("'")
    df["날짜"] = df["시각"].str[:10]
    return df


# ── 투표소 ─────────────────────────────────────────────
c1, c2 = st.columns([1, 1])
member = c1.text_input("이름")
menu = c2.selectbox("메뉴", MENUS)
if st.button("이 메뉴에 한 표", width="stretch"):
    if member.strip():
        save(member.strip(), menu, "먹고싶다")
        load.clear()
        st.balloons()                                  # 접수 축하 연출
        st.success(f"{member}님의 한 표, 접수되었습니다")
    else:
        st.warning("이름을 먼저 적어 주세요")

df = load()
today = datetime.now(KST).strftime("%Y-%m-%d")
votes = df[(df["날짜"] == today) & (df["구분"] == "먹고싶다")] if not df.empty else df
if not votes.empty:
    votes = votes.sort_values("시각").drop_duplicates("팀원", keep="last")   # 같은 사람은 마지막 표만

if votes.empty:
    st.markdown('<div class="counting">아직 들어온 표가 없습니다</div>', unsafe_allow_html=True)
    st.stop()

count = votes["메뉴"].value_counts()
voters = votes.groupby("메뉴")["팀원"].apply(lambda s: ", ".join(s))        # 막대에 올릴 이름표

# ── 개표 ───────────────────────────────────────────────
if len(votes) < 3:                                     # 세 명 미만이면 발표하지 않는다
    st.markdown(f'<div class="counting">개표가 진행 중입니다 · 현재 {len(votes)}명 투표</div>', unsafe_allow_html=True)
elif len(count) > 1 and count.iloc[0] == count.iloc[1]:
    tie = ", ".join(count[count == count.iloc[0]].index)
    st.markdown('<div class="counting">동점입니다</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="bubble">{tie}이(가) 같은 표를 받았습니다. 결선 투표를 한 번 더 돌려 주세요.</div>', unsafe_allow_html=True)
else:
    winner = count.index[0]
    st.markdown('<div class="headline">개표 결과를 발표합니다</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="winner">{winner}</div>', unsafe_allow_html=True)

    ate = df[(df["구분"] == "먹었다") & (df["메뉴"] == winner)]
    if not ate.empty:
        days = (pd.Timestamp(today) - pd.to_datetime(ate["날짜"]).max()).days
        if days <= 7:
            st.markdown(f'<div class="bubble">그 메뉴, {days}일 전에도 드셨는데 괜찮으시겠어요?</div>', unsafe_allow_html=True)

    if st.button("오늘 이거 먹었다", width="stretch"):
        save("모두", winner, "먹었다")
        load.clear()
        st.success(f"{winner}, 먹은 기록으로 남겼습니다")

# ── 득표 현황 ──────────────────────────────────────────
st.subheader("득표 현황")
board = count.rename_axis("메뉴").reset_index(name="표")
board["투표한 사람"] = board["메뉴"].map(voters)
fig = px.bar(board.iloc[::-1], x="표", y="메뉴", orientation="h", text="표",
             custom_data=["투표한 사람"], color_discrete_sequence=[ORANGE], labels={"메뉴": ""})
fig.update_traces(hovertemplate="<b>%{y}</b> %{x}표<br>%{customdata[0]}<extra></extra>", textposition="outside", cliponaxis=False)
fig.update_layout(plot_bgcolor=CREAM, paper_bgcolor=CREAM, height=300, margin=dict(l=10, r=40, t=10, b=30),
                  xaxis=dict(dtick=1, title=None))
st.plotly_chart(fig, width="stretch")

# ── 이번 주에 먹은 기록 ────────────────────────────────
st.subheader("이번 주에 뭘 먹었나")
since = (pd.Timestamp(today) - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
week = df[(df["구분"] == "먹었다") & (df["날짜"] >= since)].copy()
if week.empty:
    st.write("최근 7일 동안 먹은 기록이 없습니다.")
else:
    week["며칠 전"] = (pd.Timestamp(today) - pd.to_datetime(week["날짜"])).dt.days
    bar = px.bar(week["메뉴"].value_counts().rename_axis("메뉴").reset_index(name="횟수"),
                 x="메뉴", y="횟수", text="횟수", color_discrete_sequence=[DEEP])
    bar.update_layout(plot_bgcolor=CREAM, paper_bgcolor=CREAM, height=260, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis=dict(dtick=1))
    st.plotly_chart(bar, width="stretch")
    dots = px.scatter(week, x="날짜", y="메뉴", custom_data=["며칠 전"], color_discrete_sequence=[ORANGE])
    dots.update_traces(marker_size=16, hovertemplate="<b>%{y}</b><br>%{x} · %{customdata[0]}일 전<extra></extra>")
    dots.update_layout(plot_bgcolor=CREAM, paper_bgcolor=CREAM, height=260, margin=dict(l=10, r=10, t=10, b=10),
                       yaxis=dict(title=None))
    st.plotly_chart(dots, width="stretch")
