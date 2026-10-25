const key=process.env.GEMINI_API_KEY;
const base='https://generativelanguage.googleapis.com/v1beta/models/';
const checks=[
 [process.env.GEMINI_MODEL+':generateContent',{contents:[{parts:[{text:'Reply with exactly: Connection verified'}]}],generationConfig:{maxOutputTokens:64,thinkingConfig:{thinkingBudget:0}}}],
 [process.env.GEMINI_EMBEDDING_MODEL+':embedContent',{model:'models/'+process.env.GEMINI_EMBEDDING_MODEL,content:{parts:[{text:'Workspace connection check'}]},taskType:'RETRIEVAL_DOCUMENT',outputDimensionality:768}]
];
for(const [model,body] of checks){
 const r=await fetch(base+model,{method:'POST',headers:{'Content-Type':'application/json','x-goog-api-key':key},body:JSON.stringify(body),signal:AbortSignal.timeout(45000)});
 const d=await r.json();
 console.log(model,r.status,r.ok?(d.embedding?'dimensions '+d.embedding.values.length:d.candidates?.[0]?.content?.parts?.map(p=>p.text||'').join('')):(d.error?.status||'Failed'));
 if(!r.ok)process.exitCode=1;
}
const supabase=await fetch(process.env.SUPABASE_URL+'/auth/v1/settings',{headers:{apikey:process.env.SUPABASE_PUBLISHABLE_KEY},signal:AbortSignal.timeout(20000)});
console.log('Supabase authentication:',supabase.status);
if(!supabase.ok)process.exitCode=1;
