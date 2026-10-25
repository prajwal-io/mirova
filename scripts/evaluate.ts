import assert from 'node:assert/strict';
import {seed} from '../lib/seed';
import {chunkSource,retrieve} from '../lib/rag';
const w=seed();const chunks=w.sources.flatMap(chunkSource);
const cases=[{q:'invitation permissions risks roadmap',expected:'board-roadmap'},{q:'five customer interviews trust',expected:'doc-interviews'},{q:'data retention missing ideas',expected:'doc-workshop'},{q:'enterprise provisioning billing out of scope',expected:'doc-brief'}];
let hits=0;for(const c of cases){const results=retrieve(c.q,chunks,3);if(results.some(r=>r.sourceId===c.expected))hits++;console.log(`${results.some(r=>r.sourceId===c.expected)?'PASS':'FAIL'} ${c.q}`);}
assert.equal(hits,cases.length,'Retrieval must include the expected source in the top 3.');
assert.equal(retrieve('xyzzyqwerty',chunks).length,0,'Unrelated questions must abstain.');
const text=Array.from({length:450},(_,i)=>`word${i}`).join(' ');const long=chunkSource({...w.sources[0],text});assert.equal(long.length,3);assert.ok(long[0].content.includes('word199'));assert.ok(long[1].content.startsWith('word160'));
console.log(`Recall@3: ${hits/cases.length}; abstention and chunk overlap checks passed. Local keyword benchmark only.`);
