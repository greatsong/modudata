# 6장 전체 코드 - API 병아리반(유튜브) (2026-09-04, 저자 윤문본 _02 기준)
# 실행 조건: 스트림릿 클라우드 [Settings] → [Secrets]에 YOUTUBE_API_KEY 등록, 저장소에 fonts/NanumGothic.ttf
# requirements.txt: google-api-python-client, plotly, kiwipiepy, wordcloud
import re
from collections import Counter
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from kiwipiepy import Kiwi                     # 자바가 필요 없는 한글 형태소 분석기
from wordcloud import WordCloud

st.set_page_config(page_title="유튜브 API 대시보드", layout="wide")
youtube = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])   # 키는 비밀 금고에서


# ── 공통 도구 ──────────────────────────────────────────
def channel_query(link):
    """채널 링크를 API 요청 변수로 바꾼다. youtube.com/@핸들 → forHandle, youtube.com/channel/UC… → id"""
    link = link.strip()
    m = re.search(r"channel/(UC[\w-]+)", link)
    if m:
        return {"id": m.group(1)}
    m = re.search(r"@([\w.-]+)", link)
    if m:
        return {"forHandle": m.group(1)}
    return {"id": link} if link.startswith("UC") else {"forHandle": link}


def seconds(duration):
    """ISO 8601 길이(PT1M4S)를 초로. 3분(180초) 이하이면 쇼츠로 본다(유튜브 현행 기준)."""
    h, m, s = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration).groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)


@st.cache_data(ttl=3600)                       # 같은 요청을 되풀이하지 않도록 한 시간 보관(무료 한도 절약)
def get_channel(link):
    return youtube.channels().list(part="snippet,statistics,contentDetails", **channel_query(link)).execute()


@st.cache_data(ttl=3600)
def get_recent_videos(uploads):
    """업로드 재생목록 → 최근 영상 50편의 ID → 영상 50편의 통계를 한 번에 신청 (요청 두 번)"""
    pl = youtube.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()
    ids = [p["contentDetails"]["videoId"] for p in pl["items"]]
    vs = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()["items"]
    df = pd.DataFrame([{"제목": v["snippet"]["title"], "공개일": v["snippet"]["publishedAt"][:10],
                        "조회수": int(v["statistics"].get("viewCount", 0)),
                        "좋아요": int(v["statistics"].get("likeCount", 0)),
                        "길이(초)": seconds(v["contentDetails"]["duration"])} for v in vs])
    df["형식"] = (df["길이(초)"] <= 180).map({True: "쇼츠(3분 이하)", False: "긴 영상"})
    return df.sort_values("공개일").reset_index(drop=True)


@st.cache_data(ttl=3600)
def get_music_chart():
    r = youtube.videos().list(part="snippet,statistics", chart="mostPopular",
                              regionCode="KR", videoCategoryId="10", maxResults=10).execute()
    rows = []
    for i, v in enumerate(r["items"], 1):
        pub = date.fromisoformat(v["snippet"]["publishedAt"][:10])
        rows.append({"순위": i, "제목": v["snippet"]["title"], "채널": v["snippet"]["channelTitle"],
                     "조회수": int(v["statistics"].get("viewCount", 0)),
                     "좋아요": int(v["statistics"].get("likeCount", 0)),
                     "공개일": pub, "공개 며칠째": (date.today() - pub).days})
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_comments(video_id, pages=10):
    """댓글은 한 번에 100개씩 오므로 nextPageToken을 따라 pages번 이어 받는다 (최대 1,000개)."""
    rows, token = [], None
    for _ in range(pages):
        r = youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=100, pageToken=token,
                                          order="relevance", textFormat="plainText").execute()
        for c in r["items"]:
            s = c["snippet"]["topLevelComment"]["snippet"]
            rows.append({"댓글": s["textDisplay"], "좋아요": s["likeCount"], "작성일": s["publishedAt"][:10]})
        token = r.get("nextPageToken")
        if not token:
            break
    return pd.DataFrame(rows)


EN_STOP = set("the a an and or but if of to in on at for with from by as is are was were be been it its this that "
              "these those i you he she we they me him her us them my your his our their what which who how when "
              "where why not no so than too very can could would should will just do does did have has had about "
              "into over after before up down out off more most some any all both each other only own same".split())
KO_STOP = set("진짜 너무 정말 그냥 이거 이건 그거 근데 이제 우리 사람 생각 영상 댓글 사람들".split())   # 결과를 보며 추가


def count_words(comments):
    """한글이 많은 댓글이면 형태소 분석기로 명사만, 아니면 영어 단어를 소문자로 세 글자 이상만 센다."""
    text = " ".join(comments)
    korean = len(re.findall(r"[가-힣]", text)) > len(re.findall(r"[A-Za-z]", text)) * 0.3
    if korean:
        kiwi = Kiwi()
        words = [t.form for c in comments for t in kiwi.tokenize(c)
                 if t.tag in ("NNG", "NNP") and len(t.form) >= 2 and t.form not in KO_STOP]
    else:
        words = [w for c in comments for w in re.findall(r"[a-z']+", c.lower())
                 if len(w) >= 3 and w not in EN_STOP]
    return Counter(words), korean


# ── 화면: 탭 세 개 ─────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["채널 분석", "음악 차트", "댓글 분석"])

with tab1:
    link = st.text_input("유튜브 채널 링크", value="https://www.youtube.com/@MrBeast")
    if link:
        r = get_channel(link)
        if not r.get("items"):
            st.error("채널을 찾을 수 없어요. 링크를 확인해 주세요.")
        else:
            item = r["items"][0]
            stats = item["statistics"]
            subs, views, videos = int(stats.get("subscriberCount", 0)), int(stats.get("viewCount", 0)), int(stats.get("videoCount", 0))
            st.subheader(item["snippet"]["title"])
            c1, c2, c3 = st.columns(3)                   # 채널 통계 카드 세 장
            c1.metric("구독자 수", f"{subs:,}")
            c2.metric("총 조회수", f"{views:,}")
            c3.metric("영상 수", f"{videos:,}")
            with st.expander("API 응답 그대로 보기"):      # 첫 호출 때 화면에 그대로 보여 준 응답
                st.json(r)

            # 최근 영상 50편
            recent = get_recent_videos(item["contentDetails"]["relatedPlaylists"]["uploads"])
            shorts = recent[recent["형식"] == "쇼츠(3분 이하)"]
            best = recent.sort_values("조회수").iloc[-1]
            c4, c5, c6 = st.columns(3)                   # 아래 줄 카드 세 장 (API가 준 값을 그대로 보여 준다)
            c4.metric("최근 50편 총 좋아요", f"{recent['좋아요'].sum():,}")
            c5.metric("최근 50편 중 쇼츠(3분 이하)", f"{len(shorts)}편")
            c6.metric("최근 50편 최고 조회수", f"{best['조회수']:,}")

            recent["순서"] = range(1, len(recent) + 1)
            fig = px.bar(recent, x="순서", y="조회수", color="형식", custom_data=["제목", "공개일", "좋아요"],
                         color_discrete_map={"쇼츠(3분 이하)": "#BBD3F2", "긴 영상": "#2A78D6"},
                         labels={"순서": "최근 50편(오래된 순 → 최신)", "조회수": "조회수(회)"})
            fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>공개 %{customdata[1]}<br>조회수 %{y:,}회 · 좋아요 %{customdata[2]:,}<extra></extra>")
            st.plotly_chart(fig, width="stretch")
            st.write(f"최근 50편 중 최고 인기: **{best['제목']}** ({best['조회수']:,}회, {best['공개일']} 공개)")

            fig2 = px.scatter(recent, x="조회수", y="좋아요", color="형식", custom_data=["제목", "공개일"],
                              color_discrete_map={"쇼츠(3분 이하)": "#BBD3F2", "긴 영상": "#2A78D6"},
                              labels={"조회수": "조회수(회)", "좋아요": "좋아요(개)"})
            fig2.update_traces(marker_size=11, hovertemplate="<b>%{customdata[0]}</b><br>공개 %{customdata[1]}<br>조회수 %{x:,} · 좋아요 %{y:,}<extra></extra>")
            st.plotly_chart(fig2, width="stretch")

with tab2:
    st.subheader("한국 음악 인기 차트 Top 10")
    chart_df = get_music_chart()
    st.dataframe(chart_df, hide_index=True, width="stretch")
    fig3 = px.bar(chart_df.iloc[::-1], y="제목", x="조회수", orientation="h", color="공개 며칠째",
                  custom_data=["채널", "공개일", "좋아요", "공개 며칠째"],
                  color_continuous_scale=["#0F4C9A", "#BBD3F2"], labels={"제목": "", "조회수": "조회수(회)"})
    fig3.update_traces(hovertemplate="<b>%{y}</b><br>%{customdata[0]} · 공개 %{customdata[1]}(%{customdata[3]}일째)<br>조회수 %{x:,} · 좋아요 %{customdata[2]:,}<extra></extra>")
    st.plotly_chart(fig3, width="stretch")

with tab3:
    video_id = st.text_input("영상 ID (주소의 v= 뒤 열한 글자)", value="WXuK6gekU1Y")   # 알파고 다큐멘터리, 한국어 예: I9vK5EVTt0U
    if video_id:
        comments = get_comments(video_id.strip())
        st.subheader(f"댓글 {len(comments):,}개")
        for _, row in comments.sort_values("좋아요", ascending=False).head(3).iterrows():   # 좋아요 Top 3
            st.info(f"👍 {row['좋아요']:,}  {row['댓글'][:200]}")
        st.dataframe(comments, hide_index=True, width="stretch")

        freq, korean = count_words(comments["댓글"].tolist())
        st.caption("한국어 댓글: 형태소 분석기(kiwipiepy)로 명사만 셈" if korean else "영어 댓글: 소문자로 바꿔 세 글자 이상 단어만 셈")
        top_words = pd.DataFrame(freq.most_common(15), columns=["단어", "횟수"])
        fig4 = px.bar(top_words.iloc[::-1], y="단어", x="횟수", orientation="h", text="횟수", labels={"단어": ""})
        fig4.update_traces(marker_color="#EB6834", textposition="outside", cliponaxis=False)
        st.plotly_chart(fig4, width="stretch")
        wc = WordCloud(font_path="fonts/NanumGothic.ttf", width=1200, height=600,   # 한글 폰트 파일은 저장소에 함께 올린다
                       background_color="white").generate_from_frequencies(dict(freq.most_common(150)))
        st.image(wc.to_array(), width="stretch")
