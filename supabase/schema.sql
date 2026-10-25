-- Run once in the SQL editor of your own Supabase project.
create extension if not exists vector with schema extensions;
create table if not exists public.workspaces (
 user_id uuid primary key references auth.users(id) on delete cascade,
 data jsonb not null default '{"sources":[],"plans":[],"activity":[]}',
 updated_at timestamptz not null default now()
);
create table if not exists public.chunks (
 id text not null,
 user_id uuid not null references auth.users(id) on delete cascade,
 source_id text not null,
 content text not null,
 embedding extensions.vector(768) not null,
 primary key(user_id,id)
);
create index if not exists chunks_user_source_idx on public.chunks(user_id,source_id);
create index if not exists chunks_embedding_idx on public.chunks using hnsw (embedding extensions.vector_cosine_ops);
alter table public.workspaces enable row level security;
alter table public.chunks enable row level security;
drop policy if exists workspace_owner on public.workspaces;
create policy workspace_owner on public.workspaces for all to authenticated
 using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
drop policy if exists chunks_owner on public.chunks;
create policy chunks_owner on public.chunks for all to authenticated
 using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
grant select,insert,update,delete on public.workspaces,public.chunks to authenticated;
revoke all on public.workspaces,public.chunks from anon;
create or replace function public.match_chunks(query_embedding extensions.vector(768),match_count int default 6,source_filter text[] default '{}')
returns table(id text,source_id text,content text,similarity float)
language sql stable security invoker set search_path = '' as $$
 select c.id,c.source_id,c.content,1-(c.embedding operator(extensions.<=>) query_embedding) as similarity
 from public.chunks c
 where c.user_id=(select auth.uid()) and (cardinality(source_filter)=0 or c.source_id=any(source_filter))
 and 1-(c.embedding operator(extensions.<=>) query_embedding) > 0.25
 order by c.embedding operator(extensions.<=>) query_embedding
 limit least(greatest(match_count,1),12);
$$;
-- Atomic chunk replacement: old embeddings survive any failed replacement.
create or replace function public.replace_source_chunks(p_source_id text,p_chunks jsonb)
returns void language plpgsql security invoker set search_path = '' as $$
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 delete from public.chunks where user_id=auth.uid() and source_id=p_source_id;
 insert into public.chunks(id,user_id,source_id,content,embedding)
 select c->>'id',auth.uid(),p_source_id,c->>'content',(c->>'embedding')::extensions.vector(768)
 from jsonb_array_elements(p_chunks) c;
end;
$$;
revoke all on function public.match_chunks(extensions.vector,int,text[]) from public,anon;
revoke all on function public.replace_source_chunks(text,jsonb) from public,anon;
grant execute on function public.match_chunks(extensions.vector,int,text[]) to authenticated;
grant execute on function public.replace_source_chunks(text,jsonb) to authenticated;
-- Supabase may provision an automatic RLS event trigger. It is not a client RPC.
do $$
begin
 if to_regprocedure('public.rls_auto_enable()') is not null then
  revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
 end if;
end;
$$;
