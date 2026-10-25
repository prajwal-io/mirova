-- Transactional fixture: no accounts or research survive this test.
begin;
do $$
declare owner_id uuid:=gen_random_uuid(); editor_id uuid:=gen_random_uuid(); outsider_id uuid:=gen_random_uuid();
begin
 perform set_config('mirova.test_owner',owner_id::text,true);
 perform set_config('mirova.test_editor',editor_id::text,true);
 perform set_config('mirova.test_outsider',outsider_id::text,true);
 insert into auth.users(id,aud,role,email) values
 (owner_id,'authenticated','authenticated','policy-owner@tests.invalid'),
 (editor_id,'authenticated','authenticated','policy-editor@tests.invalid'),
 (outsider_id,'authenticated','authenticated','policy-outsider@tests.invalid');
 insert into public.workspaces(user_id,data) values(owner_id,'{"sources":[],"plans":[],"activity":[]}');
 insert into public.workspace_invites(workspace_id,code_hash) values(owner_id,repeat('a',64));
end;
$$;
set local role authenticated;
do $$
declare owner_id uuid:=current_setting('mirova.test_owner')::uuid;
 editor_id uuid:=current_setting('mirova.test_editor')::uuid;
 outsider_id uuid:=current_setting('mirova.test_outsider')::uuid;
 visible_count int; returned_id uuid; revision_value bigint; denied boolean:=false;
begin
 perform set_config('request.jwt.claims',jsonb_build_object('sub',outsider_id,'role','authenticated')::text,true);
 select count(*) into visible_count from public.workspaces;
 if visible_count<>0 then raise exception 'Unrelated user can read a workspace'; end if;
 begin perform public.accept_workspace_invite(repeat('z',64)); exception when others then denied:=true; end;
 if not denied then raise exception 'Invalid invite accepted'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',editor_id,'role','authenticated')::text,true);
 select public.accept_workspace_invite(repeat('a',64)) into returned_id;
 if returned_id<>owner_id then raise exception 'Invite did not join intended workspace'; end if;
 select count(*) into visible_count from public.workspaces where user_id=owner_id;
 if visible_count<>1 then raise exception 'Invited editor cannot read shared workspace'; end if;
 select public.save_workspace_sources(owner_id,0,'{"sources":[],"plans":[],"activity":[]}',jsonb_build_array(jsonb_build_object('sourceId','policy-test-source','chunks',jsonb_build_array(jsonb_build_object('id','policy-test-chunk','content','Shared source evidence','embedding',array_fill(0.1::real,ARRAY[768])))))) into revision_value;
 if revision_value<>1 then raise exception 'Atomic source save revision failed'; end if;
 select count(*) into visible_count from public.match_team_chunks(owner_id,array_fill(0.1::real,ARRAY[768])::extensions.vector,6,'{}');
 if visible_count<>1 then raise exception 'Team semantic retrieval failed'; end if;
 denied:=false;
 begin perform public.save_workspace_sources(owner_id,0,'{}','[]'); exception when others then denied:=true; end;
 if not denied then raise exception 'Stale revision overwrote current data'; end if;
 delete from public.workspaces where user_id=owner_id;
 select count(*) into visible_count from public.workspaces where user_id=owner_id;
 if visible_count<>1 then raise exception 'Editor deleted owner workspace'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',outsider_id,'role','authenticated')::text,true);
 select count(*) into visible_count from public.chunks;
 if visible_count<>0 then raise exception 'Unrelated user can retrieve private chunks'; end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',owner_id,'role','authenticated')::text,true);
 delete from public.team_members where workspace_id=owner_id and user_id=editor_id;
 delete from public.workspace_invites where workspace_id=owner_id;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',editor_id,'role','authenticated')::text,true);
 select count(*) into visible_count from public.workspaces;
 if visible_count<>0 then raise exception 'Removed member retained workspace access'; end if;
 denied:=false;
 begin perform public.accept_workspace_invite(repeat('a',64)); exception when others then denied:=true; end;
 if not denied then raise exception 'Revoked invite accepted'; end if;
end;
$$;
rollback;
