-- Apply after schema.sql. Existing owners and research remain intact.
alter table public.workspaces add column if not exists revision bigint not null default 0;
create schema if not exists private;
create table if not exists public.team_members (
 workspace_id uuid not null references auth.users(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 label text not null,
 joined_at timestamptz not null default now(),
 primary key(workspace_id,user_id)
);
create index if not exists team_members_user_idx on public.team_members(user_id);
create table if not exists public.workspace_invites (
 id uuid primary key default gen_random_uuid(),
 workspace_id uuid not null references auth.users(id) on delete cascade,
 code_hash text not null unique check(length(code_hash)=64),
 expires_at timestamptz not null default now()+interval '7 days',
 created_at timestamptz not null default now()
);
alter table public.team_members enable row level security;
alter table public.workspace_invites enable row level security;
create or replace function private.workspace_access(owner_id uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select auth.uid() is not null and (owner_id=auth.uid() or exists(select 1 from public.team_members m where m.workspace_id=owner_id and m.user_id=auth.uid()));
$$;
revoke all on function private.workspace_access(uuid) from public,anon;
grant usage on schema private to authenticated;
grant execute on function private.workspace_access(uuid) to authenticated;
create policy member_read on public.team_members for select to authenticated using(private.workspace_access(workspace_id));
create policy member_remove on public.team_members for delete to authenticated using(workspace_id=(select auth.uid()) or user_id=(select auth.uid()));
create policy invite_owner on public.workspace_invites for all to authenticated using(workspace_id=(select auth.uid())) with check(workspace_id=(select auth.uid()));
grant select,delete on public.team_members to authenticated;
grant select,insert,delete on public.workspace_invites to authenticated;
revoke all on public.team_members,public.workspace_invites from anon;
drop policy if exists workspace_owner on public.workspaces;
create policy workspace_team_read on public.workspaces for select to authenticated using(private.workspace_access(user_id));
create policy workspace_team_insert on public.workspaces for insert to authenticated with check(user_id=(select auth.uid()));
create policy workspace_team_update on public.workspaces for update to authenticated using(private.workspace_access(user_id)) with check(private.workspace_access(user_id));
create policy workspace_owner_delete on public.workspaces for delete to authenticated using(user_id=(select auth.uid()));
drop policy if exists chunks_owner on public.chunks;
create policy chunks_team on public.chunks for all to authenticated using(private.workspace_access(user_id)) with check(private.workspace_access(user_id));

-- Privileged membership creation is scoped to a valid, unexpired invite and the caller.
create or replace function private.accept_workspace_invite(p_hash text) returns uuid
language plpgsql security definer set search_path='' as $$
declare owner_id uuid; caller uuid:=auth.uid(); caller_label text;
begin
 if caller is null or length(p_hash)<>64 then raise exception 'Authentication and a valid invite are required'; end if;
 select workspace_id into owner_id from public.workspace_invites where code_hash=p_hash and expires_at>now();
 if owner_id is null then raise exception 'Invite is invalid, expired, or revoked'; end if;
 select email into caller_label from auth.users where id=caller;
 if caller<>owner_id then
  insert into public.team_members(workspace_id,user_id,label) values(owner_id,caller,coalesce(caller_label,'Teammate')) on conflict do nothing;
 end if;
 return owner_id;
end;
$$;
revoke all on function private.accept_workspace_invite(text) from public,anon;
grant execute on function private.accept_workspace_invite(text) to authenticated;
create or replace function public.accept_workspace_invite(p_hash text) returns uuid
language sql security invoker set search_path='' as $$ select private.accept_workspace_invite(p_hash); $$;
revoke all on function public.accept_workspace_invite(text) from public,anon;
grant execute on function public.accept_workspace_invite(text) to authenticated;

create or replace function public.match_team_chunks(p_workspace_id uuid,query_embedding extensions.vector(768),match_count int default 6,source_filter text[] default '{}')
returns table(id text,source_id text,content text,similarity float)
language sql stable security invoker set search_path='' as $$
 select c.id,c.source_id,c.content,1-(c.embedding operator(extensions.<=>) query_embedding)
 from public.chunks c
 where c.user_id=p_workspace_id and private.workspace_access(p_workspace_id)
 and (cardinality(source_filter)=0 or c.source_id=any(source_filter))
 and 1-(c.embedding operator(extensions.<=>) query_embedding)>0.25
 order by c.embedding operator(extensions.<=>) query_embedding
 limit least(greatest(match_count,1),12);
$$;
create or replace function public.replace_team_chunks(p_workspace_id uuid,p_source_id text,p_chunks jsonb)
returns void language plpgsql security invoker set search_path='' as $$
begin
 if not private.workspace_access(p_workspace_id) then raise exception 'Workspace access denied'; end if;
 delete from public.chunks where user_id=p_workspace_id and source_id=p_source_id;
 insert into public.chunks(id,user_id,source_id,content,embedding)
 select c->>'id',p_workspace_id,p_source_id,c->>'content',(c->>'embedding')::extensions.vector(768) from jsonb_array_elements(p_chunks) c;
end;
$$;
revoke all on function public.match_team_chunks(uuid,extensions.vector,int,text[]) from public,anon;
revoke all on function public.replace_team_chunks(uuid,text,jsonb) from public,anon;
grant execute on function public.match_team_chunks(uuid,extensions.vector,int,text[]) to authenticated;
grant execute on function public.replace_team_chunks(uuid,text,jsonb) to authenticated;

-- Save metadata and new vectors in the same transaction, with optimistic locking.
create or replace function public.save_workspace_sources(p_workspace_id uuid,p_expected_revision bigint,p_data jsonb,p_sources jsonb)
returns bigint language plpgsql security invoker set search_path='' as $$
declare next_revision bigint; source jsonb;
begin
 if not private.workspace_access(p_workspace_id) then raise exception 'Workspace access denied'; end if;
 if p_expected_revision=-1 then
  insert into public.workspaces(user_id,data,revision) values(p_workspace_id,p_data,1) returning revision into next_revision;
 else
  update public.workspaces set data=p_data,revision=revision+1,updated_at=now() where user_id=p_workspace_id and revision=p_expected_revision returning revision into next_revision;
  if next_revision is null then raise exception 'Workspace changed while saving'; end if;
 end if;
 for source in select value from jsonb_array_elements(p_sources) loop
  perform public.replace_team_chunks(p_workspace_id,source->>'sourceId',source->'chunks');
 end loop;
 return next_revision;
end;
$$;
revoke all on function public.save_workspace_sources(uuid,bigint,jsonb,jsonb) from public,anon;
grant execute on function public.save_workspace_sources(uuid,bigint,jsonb,jsonb) to authenticated;
