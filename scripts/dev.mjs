import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import path from 'node:path';
const root=process.cwd(),demo=process.argv.includes('--demo'),production=process.argv.includes('--production');
const apiPort=demo?'8001':'8000',frontPort=demo?'3001':'3000';
const python=process.env.PYTHON_EXECUTABLE||(process.platform==='win32'?path.join(root,'backend/.venv/Scripts/python.exe'):path.join(root,'backend/.venv/bin/python'));
if(!existsSync(python)){console.error('Create backend/.venv and install backend/requirements-lock.txt first.');process.exit(1);}
// Never pass provider credentials inherited from a shell into the frontend process.
const frontendEnv=Object.fromEntries(Object.entries(process.env).filter(([key])=>!/(GEMINI|MIRO|SUPABASE|SECRET|TOKEN|API_KEY)/i.test(key)));
Object.assign(frontendEnv,{BACKEND_URL:`http://127.0.0.1:${apiPort}`,...(demo?{NEXT_DIST_DIR:'.next-test'}:{})});
const backendEnv={...process.env,...(demo?{APP_MODE:'demo',DEMO_DATA_DIR:'.data/preview',MIRO_ACCESS_TOKEN:''}:{}),...(production?{APP_ENV:'production'}:{})};
const backend=spawn(python,['-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',apiPort,'--workers','1','--no-access-log'],{cwd:root,env:backendEnv,stdio:'inherit',windowsHide:true});
const frontend=spawn(process.execPath,['node_modules/next/dist/bin/next',production?'start':'dev','--hostname','127.0.0.1','--port',frontPort],{cwd:root,env:frontendEnv,stdio:'inherit',windowsHide:true});
let stopping=false;
function stop(code=0){if(stopping)return;stopping=true;for(const child of [backend,frontend]){if(process.platform==='win32'&&child.pid){spawn('taskkill',['/PID',String(child.pid),'/T','/F'],{stdio:'ignore',windowsHide:true});}else child.kill();}setTimeout(()=>process.exit(code),1000).unref();}
for(const child of [backend,frontend]){child.on('error',e=>{console.error('Server failed to start:',e.message);stop(1);});child.on('exit',code=>stop(code||0));}
process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());
console.log(`Mirova ${demo?'isolated preview':'workspace'}: http://localhost:${frontPort} — FastAPI on private loopback ${apiPort}`);
