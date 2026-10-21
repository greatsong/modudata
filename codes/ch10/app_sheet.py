# 10장 3~5절 '모두의 점심' 구글 시트판 - 투표와 식사 기록을 구글 시트에 저장하고 읽는다.
# 실행 조건: 시트에 연결 프로그램(votes_sheet.gs)을 웹 앱으로 배포하고,
#           스트림릿 클라우드 [Settings] - [Secrets]에 SHEET_URL = "https://script.google.com/macros/s/배포_ID/exec" 등록
# - 저장: POST 요청의 data로 member, menu, type을 보낸다. 투표는 type='희망메뉴', 식사 기록은 member='전체'·type='식사완료'
# - 읽기: GET 요청으로 머리글(시각, 팀원, 메뉴, 구분)을 포함한 시트 목록을 받는다. 시각은 연결 프로그램이 한국 시간으로 적는다
# - 오늘의 투표: 한국 날짜 기준 오늘의 '희망메뉴'에서 같은 닉네임의 마지막 한 표만 센다(시각이 같으면 시트에서 뒤의 행)
# - 결과 영역만 10초마다 다시 읽는다. 지난 7일의 식사는 오늘을 빼고, 같은 날짜와 메뉴는 한 번으로 센다
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    SHEET_URL = st.secrets["SHEET_URL"]
except Exception:   # 비밀 정보가 없을 때. 주소 값은 화면에 보여 주지 않는다
    st.error("연결 주소(SHEET_URL)가 없습니다. 스트림릿 클라우드 [Settings] - [Secrets]에 "
             'SHEET_URL = "https://script.google.com/macros/s/배포_ID/exec" 형태로 등록하세요.')
    st.stop()
MENUS = ["제육볶음", "스시", "수제버거", "파스타", "타코", "샐러드"]
COLUMNS = ["시각", "팀원", "메뉴", "구분"]
KST = timezone(timedelta(hours=9))
TIMEOUT = 10


def save_row(member, menu, type_):
    res = requests.post(SHEET_URL, json={"data": {"member": member, "menu": menu, "type": type_}},
                        timeout=TIMEOUT)
    res.raise_for_status()
    body = res.json()
    if not body.get("ok"):
        raise RuntimeError(body.get("error") or "저장에 실패했습니다")
    return True


def load_rows():
    res = requests.get(SHEET_URL, timeout=TIMEOUT)
    res.raise_for_status()
    rows = res.json()
    if not rows:
        return pd.DataFrame(columns=COLUMNS + ["행번호", "날짜"])
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["행번호"] = range(len(df))
    df["시각"] = pd.to_datetime(df["시각"], errors="coerce")
    df["날짜"] = df["시각"].dt.date
    return df


def today_counts(df):
    today = datetime.now(KST).date()
    want = df[(df["구분"] == "희망메뉴") & (df["날짜"] == today)]
    want = want.sort_values(["시각", "행번호"], kind="stable")
    last = want.drop_duplicates(subset=["팀원"], keep="last")
    counts = last["메뉴"].value_counts()
    table = pd.DataFrame({"메뉴": MENUS, "득표 수": [int(counts.get(m, 0)) for m in MENUS]})
    return last, table


def meals(df):
    """‘식사완료’ 기록을 날짜와 메뉴 기준으로 한 번씩만 남긴다."""
    ate = df[df["구분"] == "식사완료"].copy()
    if ate.empty:
        return ate
    return ate.drop_duplicates(subset=["날짜", "메뉴"], keep="first")


st.set_page_config(page_title="모두의 점심", page_icon="🍚", layout="wide")
st.title("모두의 점심")
st.caption("닉네임과 메뉴만 받습니다. 실명이나 연락처는 적지 마세요.")

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
        try:
            save_row(nickname, menu, "희망메뉴")
        except Exception:  # noqa: BLE001
            st.error("투표를 저장하지 못했습니다. 연결 설정을 확인한 뒤 다시 시도해 주세요.")
        else:
            st.success(f"{nickname}님의 한 표를 저장했습니다.")


@st.fragment(run_every=10)
def result_area():
    if st.button("결과 새로 읽기"):
        pass
    try:
        df = load_rows()
    except Exception:  # noqa: BLE001
        st.error("기록을 읽지 못했습니다. 화면의 목록이 비어 있는 것과는 다른 상황입니다.")
        return
    read_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    left, right = st.columns(2)          # 투표 결과와 식사 기록을 섞지 않고 나란히

    with left:
        st.subheader("오늘의 투표")
        last, table = today_counts(df)
        if last.empty:
            st.info("아직 투표가 없습니다.")
        else:
            top = int(table["득표 수"].max())
            winners = table.loc[table["득표 수"] == top, "메뉴"].tolist()
            st.info(f"{len(last)}명 참여 · 공동 1위: {' · '.join(winners)} (각 {top}표)"
                    if len(winners) > 1 else f"{len(last)}명 참여 · 1위: {winners[0]} ({top}표)")
            fig = px.bar(table, x="득표 수", y="메뉴", orientation="h",
                         category_orders={"메뉴": MENUS[::-1]},
                         labels={"득표 수": "투표 수 (표)", "메뉴": ""})
            fig.update_layout(height=300, xaxis=dict(dtick=1), margin=dict(t=10, b=10))
            st.plotly_chart(fig, config={"displayModeBar": False})

    with right:
        st.subheader("지난 7일의 식사")
        today = datetime.now(KST).date()
        start, end = today - timedelta(days=7), today - timedelta(days=1)
        ate = meals(df)
        recent = ate[(ate["날짜"] >= start) & (ate["날짜"] <= end)] if not ate.empty else ate
        st.caption(f"{start:%m-%d}~{end:%m-%d} · 오늘 제외 · 날짜·메뉴 중복 제거")
        if recent.empty:
            st.info("지난 7일에 기록된 식사가 없습니다.")
        else:
            cnt = recent["메뉴"].value_counts()
            mtable = pd.DataFrame({"메뉴": MENUS, "횟수": [int(cnt.get(m, 0)) for m in MENUS]})
            fig2 = px.bar(mtable, x="횟수", y="메뉴", orientation="h",
                          category_orders={"메뉴": MENUS[::-1]},
                          labels={"횟수": "식사 횟수 (회)", "메뉴": ""})
            fig2.update_traces(marker_color="#F08A24")
            fig2.update_layout(height=300, xaxis=dict(dtick=1), margin=dict(t=10, b=10))
            st.plotly_chart(fig2, config={"displayModeBar": False})
            st.write(" / ".join(f"{d:%m-%d} {m}" for d, m in
                                recent.sort_values("날짜", ascending=False)[["날짜", "메뉴"]].values))
    st.caption(f"마지막으로 읽은 시각: {read_at} (한국 시간)")


result_area()

st.divider()
st.subheader("오늘 먹은 메뉴 기록")
ate_menu = st.selectbox("오늘 실제로 먹은 메뉴", MENUS, key="ate")
if st.button("이 메뉴로 기록"):
    try:
        df = load_rows()
    except Exception:  # noqa: BLE001
        st.error("기록을 읽지 못해 저장을 멈췄습니다.")
    else:
        today = datetime.now(KST).date()
        ate = meals(df)
        already = (not ate.empty) and ((ate["날짜"] == today) & (ate["메뉴"] == ate_menu)).any()
        if already:
            st.warning(f"오늘 {ate_menu}은(는) 이미 기록되어 있습니다.")
        else:
            try:
                save_row("전체", ate_menu, "식사완료")
            except Exception:  # noqa: BLE001
                st.error("식사 기록을 저장하지 못했습니다.")
            else:
                st.success(f"오늘 먹은 메뉴로 {ate_menu}을(를) 기록했습니다.")

try:
    _df = load_rows()
    _ate = meals(_df)
    _past = _ate[(_ate["메뉴"] == ate_menu) & (_ate["날짜"] < datetime.now(KST).date())] \
        if not _ate.empty else _ate
    if not _past.empty:
        st.caption(f"최근에 먹은 날: {max(_past['날짜'])}")
    else:
        st.caption(f"{ate_menu}을(를) 최근에 먹은 기록이 없습니다.")
except Exception:  # noqa: BLE001
    pass
