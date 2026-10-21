# 10장 1절 '모두의 점심' 첫 판 - 투표를 st.session_state(임시 저장 공간)에만 기억한다.
# 닉네임과 먹고 싶은 메뉴를 받아 투표 버튼을 누르면 화면 목록에 추가한다. 파일이나 외부 저장소는 사용하지 않는다.
# 닉네임은 앞뒤 공백을 지우고, 빈 닉네임과 30자 초과는 받지 않으며, '전체'는 식사 기록용이라 개인 닉네임으로 받지 않는다.
# 브라우저를 새로고침하면 목록이 사라진다. 다음 판(app_sheet.py)에서 구글 시트에 저장한다.
import streamlit as st

MENUS = ["제육볶음", "스시", "수제버거", "파스타", "타코", "샐러드"]

st.set_page_config(page_title="모두의 점심", page_icon="🍚")
st.title("모두의 점심")
st.caption("오늘 먹고 싶은 메뉴에 한 표를 넣어 주세요.")

if "votes" not in st.session_state:
    st.session_state["votes"] = []   # 현재 접속에서만 기억하는 임시 메모장

name = st.text_input("닉네임", key="name")
menu = st.selectbox("먹고 싶은 메뉴", MENUS, key="menu")

if st.button("이 메뉴에 한 표"):
    nickname = name.strip()
    if not nickname:
        st.warning("닉네임을 먼저 적어 주세요.")
    elif len(nickname) > 30:
        st.warning("닉네임은 30자까지만 사용할 수 있습니다.")
    elif nickname == "전체":
        st.warning("‘전체’는 개인 닉네임으로 사용할 수 없습니다.")
    else:
        st.session_state["votes"].append({"닉네임": nickname, "메뉴": menu})
        st.success(f"{nickname}님의 한 표를 받았습니다.")

st.subheader("지금까지의 투표")
votes = st.session_state["votes"]
if not votes:
    st.info("아직 투표가 없습니다.")
else:
    for i, v in enumerate(votes, start=1):
        st.write(f"{i}. {v['닉네임']} - {v['메뉴']}")
    st.caption(f"모두 {len(votes)}표")
