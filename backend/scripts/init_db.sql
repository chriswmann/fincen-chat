create extension if not exists "uuid-ossp";
create schema if not exists fincen;

create table if not exists fincen.chats (
  id uuid primary key default uuid_generate_v4(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists fincen.message_roles (
  role text primary key,
  description text
);

insert into fincen.message_roles (role) values ('user'), ('assistant'), ('tool_call'), ('tool_return'), ('system'), ('retry')
on conflict (role) do nothing;

create table if not exists fincen.messages (
  id uuid primary key default uuid_generate_v4(),
  chat_id uuid not null references fincen.chats(id) on delete restrict,
  role text not null references fincen.message_roles(role),
  content text not null,
  tool_name text,
  tool_call_id text,
  tool_args jsonb,
  position int not null, -- sequential position in the chat
  created_at timestamptz not null default now()
);

create index if not exists idx_messages_chat_id on fincen.messages(chat_id);
create index if not exists idx_messages_positioning on fincen.messages(chat_id, position);

create or replace function fincen.update_updated_at()
returns trigger as $$
  begin new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_updated_at on fincen.chats;
create trigger set_updated_at
  before update on fincen.chats
    for each row execute function fincen.update_updated_at();
