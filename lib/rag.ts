import { createHash } from 'node:crypto';
import type {Chunk,Source} from './types';
export const fingerprint=(text:string)=>createHash('sha256').update(text).digest('hex');
export function chunkSource(s:Source):Chunk[]{
 const words=s.text.split(/\s+/); const chunks:Chunk[]=[];
 for(let start=0;start<words.length;start+=160){const content=words.slice(start,start+200).join(' '); if(content) chunks.push({id:`${s.id}-${start}`,sourceId:s.id,content});}
 return chunks;
}
const stop=new Set(['the','a','an','of','to','in','and','is','our','what','with','for','how','are','we','on','should','from','can','this','me']);
export function tokens(s:string){return s.toLowerCase().match(/[a-z0-9]+/g)?.filter(t=>!stop.has(t))??[];}
export function retrieve(query:string,chunks:Chunk[],count=5):Chunk[]{const q=tokens(query);return chunks.map(c=>{const ts=tokens(c.content);const score=q.reduce((n,t)=>n+ts.filter(w=>w===t||w.startsWith(t)).length,0);return {...c,similarity:score/Math.max(q.length,1)};}).filter(c=>(c.similarity??0)>0).sort((a,b)=>(b.similarity??0)-(a.similarity??0)).slice(0,count);}
