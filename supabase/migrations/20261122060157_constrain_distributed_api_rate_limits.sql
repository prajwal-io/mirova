create policy api_rate_limits_no_direct_access on public.api_rate_limits
  for all to authenticated using (false) with check (false);

create or replace function public.consume_api_rate_limit(p_bucket text, p_limit integer, p_window_seconds integer)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_uid uuid := auth.uid();
  current_count integer;
begin
  if current_uid is null then
    raise exception 'Authentication required';
  end if;
  if p_bucket <> 'api' or p_limit <> 120 or p_window_seconds <> 60 then
    raise exception 'Invalid rate-limit parameters';
  end if;

  insert into public.api_rate_limits as limits (user_id, bucket, window_started_at, request_count)
  values (current_uid, p_bucket, now(), 1)
  on conflict (user_id, bucket) do update
  set window_started_at = case
        when limits.window_started_at <= now() - make_interval(secs => p_window_seconds) then now()
        else limits.window_started_at
      end,
      request_count = case
        when limits.window_started_at <= now() - make_interval(secs => p_window_seconds) then 1
        else limits.request_count + 1
      end
  returning request_count into current_count;

  return current_count <= p_limit;
end;
$$;

revoke all on table public.api_rate_limits from anon, authenticated;
revoke all on function public.consume_api_rate_limit(text, integer, integer) from public, anon;
grant execute on function public.consume_api_rate_limit(text, integer, integer) to authenticated;
