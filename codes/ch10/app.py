"""10장 '모두의 점심' 최종판 - 수파베이스에 저장하고 화면을 꾸민 앱(그림 10-1과 같은 화면).

실행 조건
  - 수파베이스 SQL Editor에서 votes_setup.sql을 한 번 실행해 votes 테이블과 저장 규칙을 만든다.
  - 스트림릿 클라우드 [Settings] - [Secrets]에 다음 두 줄을 등록한다.
        SUPABASE_URL = "https://xxxx.supabase.co"
        SUPABASE_PUBLISHABLE_KEY = "sb_publishable_xxxxxxxxxx"

구글 시트판(app_sheet.py)과 화면 흐름과 집계 규칙은 같고, 저장과 조회만 수파베이스로 바꿨다.
  - public.votes 테이블에 닉네임은 name, 메뉴는 menu, 구분은 kind('희망메뉴' 또는 '식사완료')로 저장한다.
  - id와 created_at은 보내지 않는다(데이터베이스가 채운다).
  - 날짜는 한국 시간으로 판단한다. 같은 닉네임의 마지막 투표는 created_at이 가장 늦은 기록,
    시각까지 같으면 id가 큰 기록이다.
  - 한 번에 돌려받는 행 수(1000행)를 넘으면 이어서 읽는다.
  - 식사 기록이 중복 규칙(23505)에 걸리면 '이미 기록한 식사입니다'라고 안내하고, 다른 오류는 이유를 보여 준다.
  - 투표와 식사 기록을 저장한 뒤에 결과 영역을 그려서, 저장이 성공하면 바로 다시 읽은 결과가 보인다.
화면은 흰 바탕에 포인트 색 하나만 쓰는 카드형이고, 지난 7일의 식사는 달력 모양으로 보여 준다.
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from postgrest.exceptions import APIError
from supabase import create_client

MENUS = ["제육볶음", "스시", "수제버거", "파스타", "타코", "샐러드"]
EMOJI = {"제육볶음": "🍖", "스시": "🍣", "수제버거": "🍔", "파스타": "🍝", "타코": "🌮", "샐러드": "🥗"}
KST = timezone(timedelta(hours=9), "KST")
WANT, ATE = "희망메뉴", "식사완료"
PAGE = 1000          # 한 번의 조회로 돌려받는 행 수 한도
POINT = "#F4511E"    # 포인트 색


# ---------------------------------------------------------------- 저장과 조회
@st.cache_resource
def connect():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_PUBLISHABLE_KEY"])


def read_recent(days=7):
    """오늘 0시를 기준으로 days일 전부터의 기록만 읽는다. 한도를 넘으면 이어 읽는다."""
    today = datetime.now(KST).date()
    since = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=KST)
    sb, rows, start = connect(), [], 0
    while True:
        got = (sb.table("votes")
                 .select("id, name, menu, kind, created_at")
                 .gte("created_at", since.isoformat())
                 .order("created_at").order("id")
                 .range(start, start + PAGE - 1)
                 .execute().data) or []
        rows += got
        if len(got) < PAGE:
            break
        start += PAGE
    df = pd.DataFrame(rows, columns=["id", "name", "menu", "kind", "created_at"])
    if df.empty:
        df["날짜"] = pd.Series(dtype="object")
        return df, today
    # created_at은 시간대를 포함한 값이다. 한국 시간으로 바꾼 뒤 날짜를 본다.
    df["날짜"] = pd.to_datetime(df["created_at"], utc=True, format="ISO8601").dt.tz_convert(KST).dt.date
    return df, today


def save(name, menu, kind):
    """데이터베이스가 돌려준 응답을 확인한 뒤에만 성공으로 본다."""
    rows = connect().table("votes").insert({"name": name, "menu": menu, "kind": kind}).execute().data
    if not rows:
        raise RuntimeError("저장 결과를 확인하지 못했습니다.")


# ---------------------------------------------------------------- 화면 꾸미기
CSS = """
<style>
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1120px;}
  #MainMenu, footer, header {visibility: hidden;}

  .ml-head {display: flex; align-items: baseline; gap: .6rem; margin-bottom: .2rem;}
  .ml-head h1 {font-size: 2rem; font-weight: 800; letter-spacing: -.02em; margin: 0;}
  .ml-head .sub {color: #6B7280; font-size: .95rem;}

  .ml-card {
    border: 1px solid #ECEDEF; border-radius: 16px; padding: 22px 24px;
    background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.04);
  }
  .ml-card h3 {margin: 0 0 2px; font-size: 1.05rem; font-weight: 700; letter-spacing: -.01em;}
  .ml-card .note {color: #8A9099; font-size: .82rem; margin-bottom: 16px;}

  .ml-winners {display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px;}
  .ml-win {
    flex: 1 1 140px; border-radius: 14px; padding: 14px 16px;
    background: #FFF3EE; border: 1px solid #FBD9CB;
  }
  .ml-win .tag {font-size: .72rem; font-weight: 700; color: POINT; letter-spacing: .02em; margin-bottom: 6px;}
  .ml-win .nm {font-size: 1.35rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.25;}
  .ml-win .vt {color: #6B7280; font-size: .88rem; margin-top: 2px;}

  .ml-row {display: flex; align-items: center; gap: 10px; margin: 9px 0;}
  .ml-row .nm {width: 96px; flex: none; font-size: .9rem; color: #3A4049;}
  .ml-row .tr {flex: 1; height: 10px; border-radius: 999px; background: #F1F2F4; overflow: hidden;}
  .ml-row .fill {display: block; height: 100%; border-radius: 999px; background: POINT;}
  .ml-row .vl {
    width: 40px; flex: none; text-align: right; font-size: .85rem;
    color: #6B7280; font-variant-numeric: tabular-nums;
  }
  .ml-row.zero .vl {color: #C3C7CC;}

  .ml-list {
    margin-top: 16px; padding-top: 14px; border-top: 1px solid #F1F2F4;
    font-size: .86rem; color: #5B6270; line-height: 2;
  }

  .ml-cal {display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-top: 4px;}
  .ml-cal .day {
    border: 1px solid #F0F1F3; border-radius: 10px; padding: 9px 4px 11px;
    text-align: center; min-height: 78px;
  }
  .ml-cal .day.has {background: #FFF7F3; border-color: #FBD9CB;}
  .ml-cal .dow {font-size: .68rem; color: #A8ADB5; letter-spacing: .02em;}
  .ml-cal .dnum {font-size: .82rem; font-weight: 700; color: #3A4049; margin-top: 1px;}
  .ml-cal .emj {font-size: 1.25rem; line-height: 1.5; margin-top: 3px;}
  .ml-cal .mn {font-size: .7rem; color: #5B6270; line-height: 1.2;}
  .ml-cal .day.none .emj {color: #E4E6E9;}
  .ml-cal .day.none .mn {color: #C3C7CC;}

  .ml-empty {padding: 26px 0; text-align: center; color: #9AA0A8; font-size: .9rem;}
  .ml-read {color: #9AA0A8; font-size: .8rem; margin-top: 10px;}

  @media (max-width: 640px) {
    .ml-head h1 {font-size: 1.6rem;}
    .ml-card {padding: 18px 16px;}
    .ml-row .nm {width: 80px; font-size: .85rem;}
    .ml-cal {grid-template-columns: repeat(4, 1fr);}
  }
</style>
""".replace("POINT", POINT)


def bars(pairs, unit):
    """pairs: [(메뉴, 값)]. 값이 큰 순서로 그리고, 0인 메뉴도 함께 보여 준다."""
    top = max((v for _, v in pairs), default=0) or 1
    out = []
    for name, value in pairs:
        zero = " zero" if value == 0 else ""
        out.append(
            f'<div class="ml-row{zero}"><span class="nm">{EMOJI.get(name, "")} {name}</span>'
            f'<span class="tr"><span class="fill" style="width:{value / top * 100:.1f}%"></span></span>'
            f'<span class="vl">{value}{unit}</span></div>'
        )
    return "".join(out)


def vote_card(joined, counts, read_at):
    """오늘의 투표. counts: {메뉴: 득표 수}, joined: 참여 인원."""
    pairs = sorted(((m, int(counts.get(m, 0))) for m in MENUS), key=lambda x: -x[1])
    body = ['<div class="ml-card"><h3>오늘의 투표</h3>']
    if joined == 0:
        body.append('<div class="note">&nbsp;</div><div class="ml-empty">아직 투표가 없습니다.</div>'
                    f'<div class="ml-read">마지막으로 읽은 시각: {read_at} (한국 시간)</div></div>')
        st.markdown("".join(body), unsafe_allow_html=True)
        return
    top = pairs[0][1]
    winners = [m for m, v in pairs if v == top]
    label = "공동 1위" if len(winners) > 1 else "1위"
    body.append(f'<div class="note">참여 {joined}명 · 한 사람의 마지막 한 표만 집계합니다</div>')
    body.append('<div class="ml-winners">')
    for name in winners:
        body.append(f'<div class="ml-win"><div class="tag">{label}</div>'
                    f'<div class="nm">{EMOJI.get(name, "")} {name}</div><div class="vt">{top}표</div></div>')
    body.append("</div>")
    body.append(bars(pairs, "표"))
    body.append(f'<div class="ml-read">마지막으로 읽은 시각: {read_at} (한국 시간)</div></div>')
    st.markdown("".join(body), unsafe_allow_html=True)


def meal_card(days, counts):
    """지난 7일의 식사를 달력으로 보여 준다. days: [(날짜, [메뉴, ...])] 오래된 날부터."""
    dow = ["월", "화", "수", "목", "금", "토", "일"]
    body = ['<div class="ml-card"><h3>지난 7일의 식사</h3>'
            f'<div class="note">{days[0][0]:%m월 %d일}~{days[-1][0]:%m월 %d일}'
            ' · 오늘 제외 · 같은 날짜의 같은 메뉴는 한 번</div>']
    if not any(m for _, m in days):
        body.append('<div class="ml-empty">지난 7일에 기록된 식사가 없습니다.</div></div>')
        st.markdown("".join(body), unsafe_allow_html=True)
        return
    body.append('<div class="ml-cal">')
    for d, menus in days:
        cell = [f'<div class="{"day has" if menus else "day none"}"><div class="dow">{dow[d.weekday()]}</div>'
                f'<div class="dnum">{d.day}</div>']
        if menus:
            cell += [f'<div class="emj">{EMOJI.get(m, "")}</div><div class="mn">{m}</div>' for m in menus]
        else:
            cell.append('<div class="emj">·</div><div class="mn">기록 없음</div>')
        cell.append("</div>")
        body.append("".join(cell))
    body.append("</div>")
    pairs = sorted(((m, int(counts.get(m, 0))) for m in MENUS), key=lambda x: -x[1])
    if any(v for _, v in pairs):
        body.append('<div class="ml-list">' + bars(pairs, "회") + "</div>")
    body.append("</div>")
    st.markdown("".join(body), unsafe_allow_html=True)


# ---------------------------------------------------------------- 화면
st.set_page_config(page_title="모두의 점심", page_icon="🍚", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown('<div class="ml-head"><h1>🍚 모두의 점심</h1>'
            '<span class="sub">오늘 함께 먹을 메뉴를 정해요</span></div>', unsafe_allow_html=True)

try:
    connect()
except Exception:   # 비밀 정보가 없거나 값이 잘못되었을 때. 키 값은 화면에 보여 주지 않는다
    st.error("수파베이스 연결 정보를 읽지 못했습니다. 스트림릿 클라우드 [Settings] - [Secrets]에 "
             "SUPABASE_URL과 SUPABASE_PUBLISHABLE_KEY를 등록했는지 확인하세요.")
    st.stop()

with st.container(border=True):
    c1, c2 = st.columns(2)
    nickname = c1.text_input("닉네임", placeholder="실습용 닉네임").strip()
    menu = c2.selectbox("먹고 싶은 메뉴", MENUS, format_func=lambda m: f"{EMOJI[m]} {m}")
    if st.button("이 메뉴에 한 표", type="primary"):
        if not nickname:
            st.warning("닉네임을 먼저 적어 주세요.")
        elif len(nickname) > 30:
            st.warning("닉네임은 30자까지만 사용할 수 있습니다.")
        elif nickname == "전체":
            st.warning("‘전체’는 식사 기록에 사용하므로 닉네임으로 쓸 수 없습니다.")
        else:
            try:
                save(nickname, menu, WANT)
            except Exception as err:  # noqa: BLE001
                st.error(f"투표를 저장하지 못했습니다. ({err})")
            else:
                st.success(f"{nickname}님의 한 표를 저장했습니다.")


@st.fragment(run_every=10)
def results():
    """결과 영역만 10초마다 다시 읽는다. 입력 중인 닉네임과 메뉴는 그대로 남는다."""
    st.button("결과 새로 읽기")
    try:
        df, today = read_recent()
    except Exception as err:  # noqa: BLE001
        st.error(f"기록을 읽지 못했습니다. ({err})")
        return
    left, right = st.columns(2)   # 투표 결과와 식사 기록은 섞지 않고 나란히
    with left:
        today_want = df[(df["kind"] == WANT) & (df["날짜"] == today)]
        last = today_want.drop_duplicates(subset=["name"], keep="last")   # created_at, id 순으로 정렬되어 있다
        vote_card(len(last), last["menu"].value_counts().to_dict(), f"{datetime.now(KST):%Y-%m-%d %H:%M:%S}")
    with right:
        start, end = today - timedelta(days=7), today - timedelta(days=1)
        ate = df[(df["kind"] == ATE) & (df["날짜"] >= start) & (df["날짜"] <= end)]
        ate = ate.drop_duplicates(subset=["날짜", "menu"])          # 같은 날짜와 메뉴는 한 번으로
        by_date = {} if ate.empty else ate.groupby("날짜")["menu"].apply(list).to_dict()
        days = [(start + timedelta(days=i), by_date.get(start + timedelta(days=i), [])) for i in range(7)]
        meal_card(days, {} if ate.empty else ate["menu"].value_counts().to_dict())


results_box = st.container()   # 결과 영역의 자리. 식사 기록 저장까지 처리한 뒤 맨 아래에서 채운다

st.write("")
with st.container(border=True):
    st.markdown("**오늘 먹은 메뉴 기록**")
    c1, _ = st.columns(2)
    ate_menu = c1.selectbox("오늘 실제로 먹은 메뉴", MENUS, key="ate", format_func=lambda m: f"{EMOJI[m]} {m}")
    if st.button("이 메뉴로 기록"):
        try:
            save("전체", ate_menu, ATE)
        except APIError as err:
            # 23505는 같은 한국 날짜와 메뉴를 두 번 저장하지 못하게 한 규칙에 걸렸다는 뜻이다.
            if err.code == "23505":
                st.warning("이미 기록한 식사입니다.")
            else:
                st.error(f"식사 기록을 저장하지 못했습니다. ({err.message})")
        except Exception as err:  # noqa: BLE001
            st.error(f"식사 기록을 저장하지 못했습니다. ({err})")
        else:
            st.success(f"오늘 먹은 메뉴로 {ate_menu}을(를) 기록했습니다.")

    # 선택한 메뉴를 최근 7일 안에 먹었다면 마지막으로 먹은 날짜를 알려 준다.
    try:
        recent, today = read_recent()
        past = recent[(recent["kind"] == ATE) & (recent["menu"] == ate_menu) & (recent["날짜"] < today)]
        if past.empty:
            st.caption(f"최근 7일 동안 {ate_menu}을(를) 먹은 기록이 없습니다.")
        else:
            st.caption(f"{ate_menu}을(를) 최근에 먹은 날: {past['날짜'].max():%Y-%m-%d}")
    except Exception:  # noqa: BLE001
        st.caption("최근 식사 기록을 읽지 못했습니다.")

with results_box:   # 저장을 모두 처리한 뒤에 결과를 읽으므로 방금 저장한 기록도 바로 보인다
    results()
