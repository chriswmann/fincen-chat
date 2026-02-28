create table if not exists chats (
  id uuid primary key default generate_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists message_roles (
  role text primary key,
  description text,
);

insert into message_roles (role) values ('user'), ('assistant'), ('tool_call'), ('tool_return');

create table if not exists messages (
  id uuid primary key default generate_random_uuid(),
  chat_id uuid not null references chats(id) on delete restrict,
  role text not null references message_roles(role),
  content text not null,
  tool_name text,
  tool_call_id text,
  tool_args jsonb,
  position int not null, -- sequential position in the chat
  created_at timestamptz not null default now()
);

create index if not exists idx_messages_chat_id on messages(chat_id);
create index if not exists idx_messages_positioning on messages(chat_id, position);

create or replace function update_updated_at()
returns trigger as $$
  begin new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger set_updated_at
  before update on chats
    for each row execute function update_updated_at();
