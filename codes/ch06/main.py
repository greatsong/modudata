# 6장 전체 코드 - API 병아리반(유튜브) (2026-09-04)
# 실행 조건: 스트림릿 클라우드 [Settings] → [Secrets]에 YOUTUBE_API_KEY 등록, 저장소에 fonts/NanumGothic.ttf
import time
from datetime import date, timedelta

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build

# ── 유튜브 채널 대시보드 ───────────────────────────────
youtube = build("youtube", "v3", developerKey=st.secrets["YOUTUBE_API_KEY"])
channel_id = st.text_input("채널 ID", value="UCX6OQ3DkcsbYNE6H8uQQuVA")   # 기본값: MrBeast
if channel_id:
    r = youtube.channels().list(part="snippet,statistics,contentDetails", id=channel_id).execute()
    if r.get("items"):
        item = r["items"][0]
        stats = item["statistics"]
        subs   = int(stats.get("subscriberCount", 0))
        views  = int(stats.get("viewCount", 0))
        videos = int(stats.get("videoCount", 0))
        avg    = views // videos if videos else 0
        st.subheader(item["snippet"]["title"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("구독자 수", f"{subs:,}")
        c2.metric("총 조회수", f"{views:,}")
        c3.metric("영상 수", f"{videos:,}")
        c4.metric("영상당 평균 조회수", f"{avg:,}")

        # 최근 영상 50편: 업로드 재생목록 → 영상 ID 50개 → 영상별 통계
        uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = youtube.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()
        ids = [p["contentDetails"]["videoId"] for p in pl["items"]]
        vs = youtube.videos().list(part="snippet,statistics", id=",".join(ids)).execute()["items"]
        recent = pd.DataFrame([{"제목": v["snippet"]["title"], "공개일": v["snippet"]["publishedAt"][:10],
                                "조회수": int(v["statistics"].get("viewCount", 0)),
                                "좋아요": int(v["statistics"].get("likeCount", 0))} for v in vs]).sort_values("공개일")
        days = (pd.to_datetime(recent["공개일"].max()) - pd.to_datetime(recent["공개일"].min())).days
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("최근 50편 총 좋아요", f"{recent['좋아요'].sum():,}")
        c6.metric("최근 50편 평균 조회수", f"{int(recent['조회수'].mean()):,}")
        c7.metric("좋아요율(좋아요÷조회수)", f"{recent['좋아요'].sum() / recent['조회수'].sum() * 100:.2f}%")
        c8.metric("업로드 간격", f"{days / (len(recent) - 1):.1f}일에 한 편")
        recent["형식"] = recent["제목"].str.contains("#shorts", case=False).map({True: "쇼츠", False: "긴 영상"})   # 제목 표시 기준(간단판)
        st.plotly_chart(px.bar(recent, x="공개일", y="조회수", color="형식", hover_name="제목"))
        st.plotly_chart(px.scatter(recent, x="조회수", y="좋아요", color="형식", hover_name="제목", hover_data=["공개일"]))
        best = recent.sort_values("조회수").iloc[-1]
        st.write(f"최근 50편 중 최고 인기: {best['제목']} ({best['조회수']:,}회)")
    else:
        st.error("채널을 찾을 수 없어요. ID를 확인해 주세요.")

# ── 음악 인기 차트 ─────────────────────────────────────
chart = youtube.videos().list(part="snippet,statistics", chart="mostPopular",
                              regionCode="KR", videoCategoryId="10", maxResults=10).execute()
rows = []
for i, v in enumerate(chart["items"], 1):
    pub = date.fromisoformat(v["snippet"]["publishedAt"][:10])
    rows.append({"순위": i, "제목": v["snippet"]["title"], "채널": v["snippet"]["channelTitle"],
                 "조회수": int(v["statistics"].get("viewCount", 0)),
                 "좋아요": int(v["statistics"].get("likeCount", 0)),
                 "공개일": pub, "공개 며칠째": (date.today() - pub).days})
chart_df = pd.DataFrame(rows)
st.subheader("한국 음악 인기 차트 Top 10")
st.dataframe(chart_df)
st.plotly_chart(px.bar(chart_df.iloc[::-1], y="제목", x="조회수", orientation="h",
                       color="공개 며칠째", labels={"제목": ""}))


# ── 댓글 분석 ──────────────────────────────────────────
import re
from collections import Counter
from kiwipiepy import Kiwi                     # 자바가 필요 없는 한글 형태소 분석기
from wordcloud import WordCloud

@st.cache_data(ttl=3600)
def load_comments(vid, pages=10):
    """댓글은 한 번에 100개씩 오므로 nextPageToken을 따라 pages번 이어 받는다 (최대 1,000개)."""
    rows, token = [], None
    for _ in range(pages):
        r = youtube.commentThreads().list(part="snippet", videoId=vid, maxResults=100, pageToken=token,
                                          order="relevance", textFormat="plainText").execute()
        for c in r["items"]:
            s = c["snippet"]["topLevelComment"]["snippet"]
            rows.append({"댓글": s["textDisplay"], "좋아요": s["likeCount"], "작성일": s["publishedAt"][:10]})
        token = r.get("nextPageToken")
        if not token:
            break
    return rows

EN_STOP = set("the a an and or but if of to in on at for with from by as is are was were be been it its this that "
              "these those i you he she we they me him her us them my your his our their what which who how when "
              "where why not no so than too very can could would should will just do does did have has had about "
              "into over after before up down out off more most some any all both each other only own same".split())
KO_STOP = set("진짜 너무 정말 그냥 이거 이건 그거 근데 이제 우리 사람 생각 영상 댓글 사람들".split())     # 불용어(결과 보며 추가)

def count_words(comments, korean):
    if korean:                                 # 한국어: 형태소 분석기로 명사만
        kiwi = Kiwi()
        words = [tok.form for text in comments for tok in kiwi.tokenize(text)
                 if tok.tag in ("NNG", "NNP") and len(tok.form) >= 2 and tok.form not in KO_STOP]
    else:                                      # 영어: 소문자로 바꿔 띄어쓰기로 자르기
        words = [w for text in comments for w in re.findall(r"[a-z']+", text.lower())
                 if len(w) >= 3 and w not in EN_STOP]
    return Counter(words)

for title, vid, korean in [("알파고 다큐멘터리", "WXuK6gekU1Y", False), ("2002 월드컵 메모리즈", "I9vK5EVTt0U", True)]:
    comments = pd.DataFrame(load_comments(vid))
    st.subheader(f"{title} - 댓글 {len(comments):,}개")
    for _, row in comments.sort_values("좋아요", ascending=False).head(3).iterrows():
        st.info(f"👍 {row['좋아요']:,}  {row['댓글'][:120]}")
    freq = count_words(comments["댓글"], korean)
    top_words = pd.DataFrame(freq.most_common(15), columns=["단어", "횟수"])
    st.plotly_chart(px.bar(top_words.iloc[::-1], y="단어", x="횟수", orientation="h", labels={"단어": ""}))
    wc = WordCloud(font_path="fonts/NanumGothic.ttf", width=1200, height=600,   # 한글 폰트 파일은 저장소에 함께 올린다
                   background_color="white").generate_from_frequencies(dict(freq.most_common(300)))
    st.image(wc.to_array())

