# 10장 점심 메뉴 투표 앱 '모두의 점심'

책의 흐름을 따라 세 가지 판을 두었습니다. 스트림릿 클라우드에서 실행할 파일을 하나 골라 지정합니다.

| 파일 | 책의 위치 | 저장 위치 | 비밀 정보(Secrets) |
|---|---|---|---|
| `app_basic.py` | 1절 | `st.session_state`(새로고침하면 사라짐) | 없음 |
| `app_sheet.py` | 3~5절 | 구글 시트 | `SHEET_URL` |
| `main.py` | 6~7절(최종판, 화면 꾸미기 포함) | 수파베이스 `votes` 테이블 | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` |

- `votes_sheet.gs` : 구글 시트의 [확장 프로그램] - [Apps Script]에 붙여 넣는 연결 프로그램입니다. 첫 부분의 `SPREADSHEET_ID`만 자신의 시트 ID로 바꾼 뒤 웹 앱으로 배포합니다. GET 요청에는 시트 목록을 돌려주고, POST 요청의 `data`로 `member`, `menu`, `type`을 받아 한 줄을 씁니다.
- `votes_setup.sql` : 수파베이스 [SQL Editor]에서 한 번 실행하는 준비용 SQL입니다. `votes` 테이블(id, name, menu, kind, created_at)과 저장 규칙(빈 닉네임 거절, 여섯 메뉴만 허용, 구분은 '희망메뉴'와 '식사완료', 식사 기록은 한국 날짜와 메뉴가 같으면 한 번만, 로그인하지 않은 요청은 읽기와 추가만)을 만듭니다.
- `requirements.txt` : 세 판에 필요한 도구를 모두 적었습니다.

이 앱은 로그인 기능이 없는 공개 실습용입니다. 실명이나 연락처 대신 실습용 닉네임만 사용합니다.
