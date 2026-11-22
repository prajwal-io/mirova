drop policy if exists api_rate_limits_self on public.api_rate_limits;
revoke all on table public.api_rate_limits from anon, authenticated;

alter function public.consume_api_rate_limit(text, integer, integer) security definer;
alter function public.consume_api_rate_limit(text, integer, integer) set search_path = '';
revoke all on function public.consume_api_rate_limit(text, integer, integer) from public, anon;
grant execute on function public.consume_api_rate_limit(text, integer, integer) to authenticated;
