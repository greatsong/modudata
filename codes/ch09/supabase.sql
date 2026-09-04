-- 9장 Supabase - [SQL Editor]에 붙여 넣고 [Run]
create table votes (
  id bigint generated always as identity primary key,
  name text not null,                 -- 별명만
  menu text not null,                 -- 투표한 메뉴 (예: 김치찌개)
  created_at timestamptz default now()
);
-- 출입 정책: 추가, 읽기만 허용. 수정, 삭제는 정책을 안 만들었으므로 자동으로 막힘
alter table votes enable row level security;
create policy p1 on votes for insert with check (true);
create policy p2 on votes for select using (true);
