# 9장 기본판 - 민주적 점심 (구글 시트 저장)
# 실행 조건: 스트림릿 클라우드 [Settings] → [Secrets]에 SHEET_URL(.../exec) 등록
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd
import streamlit as st

SHEET_URL = st.secrets["SHEET_URL"]          # 시트에 딸린 접수창구 주소
KST = timezone(timedelta(hours=9))           # 시각은 한국 시간 기준으로 읽고 쓴다
MENUS = ["김치찌개", "된장찌개", "돈까스", "비빔밥", "냉면", "샐러드"]

st.title("민주적 점심")
st.caption("오늘 점심은 투표로 정합니다")


def save(member, menu, type_):
    """접수창구에 값을 보내 시트에 한 줄을 쌓는다. 한글이 깨지지 않게 params로 넘긴다."""
    requests.get(SHEET_URL, params={"member": member, "menu": menu, "type": type_}, timeout=10)


@st.cache_data(ttl=10)                       # 방금 넣은 표가 곧 보이도록 아주 짧게만 기억
def load():
    """접수창구를 값 없이 열면 전체 기록이 표로 온다. 첫 줄은 머리글이다."""
    rows = requests.get(SHEET_URL, timeout=10).json()
    if len(rows) <= 1:                       # 머리글만 있으면 빈 표
        return pd.DataFrame(columns=["시각", "팀원", "메뉴", "구분"])
    df = pd.DataFrame(rows[1:], columns=["시각", "팀원", "메뉴", "구분"])
    df["시각"] = df["시각"].astype(str).str.lstrip("'")     # 앞에 붙인 작은따옴표를 떼고
    df["날짜"] = df["시각"].str[:10]
    return df


# ── 투표하기 ───────────────────────────────────────────
member = st.text_input("이름")
menu = st.selectbox("메뉴", MENUS)
if st.button("이 메뉴에 한 표"):
    if member.strip():
        save(member.strip(), menu, "먹고싶다")
        load.clear()                          # 방금 넣은 표를 바로 반영
        st.success(f"{member}님의 한 표, 잘 받았습니다")
    else:
        st.warning("이름을 먼저 적어 주세요")

df = load()
if df.empty:
    st.info("아직 표가 하나도 없습니다. 첫 표를 던져 주세요.")
    st.stop()

today = datetime.now(KST).strftime("%Y-%m-%d")
votes = df[(df["날짜"] == today) & (df["구분"] == "먹고싶다")]
votes = votes.sort_values("시각").drop_duplicates("팀원", keep="last")   # 같은 사람은 마지막 표만

if votes.empty:
    st.info("오늘은 아직 표가 없습니다. 첫 표를 던져 주세요.")
    st.stop()

# ── 오늘의 당선 메뉴 ───────────────────────────────────
count = votes["메뉴"].value_counts()
winner = count.index[0]
st.header(f"오늘의 메뉴는 {winner}")
st.write(f"{len(votes)}명이 투표했습니다.")

# 최근 7일 안에 그 메뉴를 먹었다면 한마디
ate = df[df["구분"] == "먹었다"]
ate = ate[ate["메뉴"] == winner]
if not ate.empty:
    last = pd.to_datetime(ate["날짜"]).max()
    days = (pd.Timestamp(today) - last).days
    if days <= 7:
        st.warning(f"그 메뉴, {days}일 전에도 드셨는데 괜찮으시겠어요?")

if st.button("오늘 이거 먹었다"):
    save("모두", winner, "먹었다")
    load.clear()
    st.success(f"{winner}, 먹은 기록으로 남겼습니다")

# ── 오늘의 득표와 이번 주 기록 ─────────────────────────
st.subheader("오늘의 득표")
st.dataframe(count.rename_axis("메뉴").reset_index(name="표"), hide_index=True)

st.subheader("최근 7일 동안 먹은 기록")
week = df[(df["구분"] == "먹었다") & (df["날짜"] >= (pd.Timestamp(today) - pd.Timedelta(days=7)).strftime("%Y-%m-%d"))]
if week.empty:
    st.write("최근 7일 동안 먹은 기록이 없습니다.")
else:
    st.dataframe(week[["날짜", "메뉴"]].sort_values("날짜", ascending=False), hide_index=True)
