-- 모두의 점심 - 수파베이스 준비용 SQL
-- 비어 있는 새 프로젝트의 [SQL Editor]에 붙여 넣고 [Run]을 한 번만 실행합니다.
-- 표의 열과 저장 규칙을 한꺼번에 만듭니다.

create table public.votes (
  id         bigint generated always as identity primary key,  -- 데이터베이스가 붙이는 고유 번호
  name       text        not null,                             -- 투표한 별명. 식사 기록은 '전체'
  menu       text        not null,                             -- 앞에서 정한 여섯 메뉴 중 하나
  kind       text        not null,                             -- '희망메뉴' 또는 '식사완료'
  created_at timestamptz not null default now(),               -- 데이터베이스가 적는 저장 시각

  -- 빈 별명은 받지 않는다(공백만 넣은 것도 빈 별명으로 본다).
  constraint votes_name_not_blank check (btrim(name) <> ''),

  -- 약속하지 않은 메뉴는 받지 않는다.
  constraint votes_menu_allowed check (
    menu in ('제육볶음', '스시', '수제버거', '파스타', '타코', '샐러드')
  ),

  -- 구분은 두 가지뿐이다.
  constraint votes_kind_allowed check (kind in ('희망메뉴', '식사완료'))
);

-- 식사 기록은 '한국 날짜와 메뉴가 같으면 한 번만 저장'한다.
-- 개인의 투표('희망메뉴')는 마음을 바꿀 수 있으므로 이 규칙에서 뺀다(부분 유일 인덱스).
--
-- 주의: created_at::date, date(created_at), to_char(created_at, 'YYYY-MM-DD')처럼
--       저장 시각에서 날짜를 바로 뽑으면 "functions in index expression must be marked
--       IMMUTABLE" 오류가 납니다. created_at은 시간대를 포함한 값이라 어느 날짜가 되는지가
--       접속의 시간대 설정에 따라 달라지고, 그런 식은 인덱스에 쓸 수 없기 때문입니다.
--       아래처럼 at time zone 'Asia/Seoul'로 한국 시간을 먼저 정한 뒤 날짜를 뽑으면
--       값이 접속 설정과 무관하게 고정되어 인덱스에 쓸 수 있습니다.
create unique index votes_meal_once_per_day
  on public.votes (((created_at at time zone 'Asia/Seoul')::date), menu)
  where kind = '식사완료';

-- 접근 권한: 로그인하지 않은 요청(anon)에 읽기와 추가만 허용한다.
-- 수정과 삭제는 정책을 만들지 않았으므로 자동으로 막힌다.
alter table public.votes enable row level security;

create policy votes_select_anon on public.votes
  for select to anon using (true);

create policy votes_insert_anon on public.votes
  for insert to anon with check (true);

revoke all on public.votes from anon;
grant select, insert on public.votes to anon;
