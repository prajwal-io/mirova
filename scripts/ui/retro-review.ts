import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { seed } from '../../lib/seed';
const out='.impeccable/retro-review';await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const errors:string[]=[];
for(const [name,width,height] of [['desktop',1440,1000],['tablet',768,1024],['mobile',390,844]] as const){
 const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:3000');await page.getByRole('button',{name:'Sign in',exact:true}).waitFor();
 await page.evaluate(()=>document.fonts.ready);await page.addStyleTag({content:'nextjs-portal{display:none!important}'});
 await page.getByLabel('Password',{exact:true}).fill('visibility-check');await page.getByRole('button',{name:'Show password',exact:true}).click();assert.equal(await page.getByLabel('Password',{exact:true}).getAttribute('type'),'text');await page.getByRole('button',{name:'Hide password',exact:true}).click();await page.getByLabel('Password',{exact:true}).fill('');
 await page.getByRole('button',{name:'Create an account',exact:true}).click();await page.getByRole('button',{name:'Create account',exact:true}).waitFor();assert.equal(await page.getByLabel('Password',{exact:true}).getAttribute('minlength'),'8');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false,`${name} auth overflow`);
 await page.screenshot({path:`${out}/auth-${name}.png`,fullPage:true});await page.close();
}
const fixture=seed();fixture.plans=[{id:'preview-plan',title:'From discovery to delivery',status:'draft',sourceIds:fixture.sources.map(s=>s.id),createdAt:new Date().toISOString(),steps:[{phase:'Discover',title:'Connect the evidence',description:'Review research and agree on the onboarding problem.'},{phase:'Design',title:'Test the first step',description:'Prototype the guided board flow and validate it with five teams.'},{phase:'Build',title:'Build with intention',description:'Implement the validated flow and track activation.'},{phase:'Launch',title:'Learn from a pilot',description:'Check accessibility, agree a rollback plan, then launch a pilot.'}]}];
for(const [name,width,height] of [['desktop',1440,1000],['tablet',768,1024],['mobile',390,844]] as const){
 const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/config',r=>r.fulfill({json:{mode:'demo',url:'',key:'',integrations:{Miro:true,Gemini:true,Supabase:true}}}));
 await page.route('**/api/workspace',r=>r.fulfill({json:{...fixture,mode:'demo'}}));
 await page.route('**/api/chat',r=>r.fulfill({json:{answer:'Prioritize a guided first board, contextual templates, and a simpler invite flow. Validate the flow with five new teams. [1]',citations:[{id:1,sourceId:fixture.sources[0].id,title:fixture.sources[0].title,excerpt:fixture.sources[0].text}],mode:'local'}}));
 await page.goto('http://localhost:3000');await page.getByText('Product discovery',{exact:true}).first().waitFor();await page.evaluate(()=>document.fonts.ready);await page.addStyleTag({content:'nextjs-portal{display:none!important}'});
 assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false,`${name} dashboard overflow`);
 await page.screenshot({path:`${out}/dashboard-${name}.png`,fullPage:true});
 const navigate=async(name:string)=>{if(width<=740)await page.getByRole('button',{name:'Open navigation',exact:true}).click();await page.locator(name==='Settings'?'.sidebar-bottom > button':'nav button').filter({hasText:name}).click();};
 if(name==='desktop'){
  await page.getByRole('button',{name:'Help & getting started'}).click();await page.locator('.modal .primary').focus();await page.keyboard.press('Tab');assert.equal(await page.getByRole('button',{name:'Close dialog',exact:true}).evaluate(el=>el===document.activeElement),true);await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Search anything'}).click();await page.getByRole('textbox',{name:'Search workspace'}).fill('Product discovery');assert.equal(await page.locator('.search-results>button').count(),1);await page.keyboard.press('Escape');
 }
 for(const view of ['AI copilot','Knowledge map','Roadmaps','Settings','Knowledge library','Miro boards']){
  await navigate(view);assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth),false,`${name} ${view} overflow`);
  if(view==='AI copilot'){await page.getByRole('textbox',{name:'Ask your workspace'}).fill('What should our onboarding prioritize?');await page.getByRole('button',{name:'Send question'}).click();await page.locator('.citation').waitFor();await page.locator('.citation').click();await page.getByText('Referenced excerpt',{exact:true}).waitFor();await page.getByRole('button',{name:'Close source'}).click();}
  if(view==='Roadmaps')assert.equal(await page.getByRole('button',{name:'Approve demo plan'}).isDisabled(),true);
  if(['AI copilot','Roadmaps','Settings'].includes(view))await page.screenshot({path:`${out}/${view.replaceAll(' ','-').toLowerCase()}-${name}.png`,fullPage:true});
 }
 await page.close();
}
assert.deepEqual(errors,[]);await browser.close();console.log('PASS responsive auth and all workspace screens, password visibility, signup toggle, citation inspection, search, modal keyboard trap, approval gate, and no browser exceptions. Workspace screenshots use test-only synthetic fixtures; live authentication is unchanged.');
