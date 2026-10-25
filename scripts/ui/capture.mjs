import {chromium} from 'playwright';
import {mkdir} from 'node:fs/promises';
await mkdir('.impeccable/review',{recursive:true});
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
for(const [name,width,height] of [['desktop',1440,1000],['tablet',768,1024],['mobile',390,844]]){
 const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});
 await page.goto('http://localhost:3000');await page.getByText('Product discovery',{exact:true}).first().waitFor();await page.evaluate(()=>document.fonts.ready);await page.addStyleTag({content:'nextjs-portal{display:none!important} *{transition:none!important;animation:none!important}'});await page.screenshot({path:`.impeccable/review/${name}.png`,fullPage:true});await page.close();
}
await browser.close();
