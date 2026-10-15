// Runs actual Vue handler functions with controlled delays, without browser/data writes.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontend = path.resolve(__dirname, '../../04.编码/前端');
const parse = createRequire(path.join(frontend, 'package.json'))('@babel/parser').parse;
const source = fs.readFileSync(path.join(frontend, 'src/components/common/AIConsult.vue'), 'utf8').split('<script setup>')[1].split('</script>')[0];
const definitions = parse(source, {sourceType:'module'}).program.body.filter(node=>node.type==='FunctionDeclaration').map(node=>source.slice(node.start,node.end)).join('\n');
function deferred() { let resolve; const promise = new Promise(r=>resolve=r); return {promise,resolve}; }
function fixture() {
  const state = {viewVersion:0, canIntake:true, canChat:true, scope:'family', nextTick:async()=>{}, pushed:[], warnings:[],
    listSessions:async()=>[], listPersonalFacts:async()=>[], listPersonalAdvice:async()=>[], startIntake:async()=>null,
    listMessages:async()=>[], generatePersonalAdvice:async id=>({profile_id:id,advice_id:1}),
    sendMessage:async()=>{}, ElMessage:{warning:()=>state.warnings.push(true),success:()=>{},error:()=>{}},
    router:{push:value=>state.pushed.push(value)}};
  for (const [key,value] of Object.entries({selectedProfileId:11,currentSessionId:null,messages:[],input:'询问近况',loading:false,error:'',chatBody:null,
    sessions:[],intake:null,intakeAnswer:'',intakeLoading:false,intakeError:'',personalSaving:false,confirmationEntries:[],facts:[],advices:[],
    adviceLoading:false,factDialog:false,editingFact:null,adviceId:null,sourceMessageId:null,retrievalInfo:null,modelStatus:''})) state[key]={value};
  const handlers=new Function('state', 'with(state){'+definitions+';return {makeAdvice,useSuggestion,send,onSwitchProfile,newSession,loadSessions,openSession};}')(state);
  return {state,handlers};
}

test('late advice is discarded after profile switch; actions require the card profile',async()=>{
  const {state,handlers:f}=fixture(),pending=deferred();
  state.generatePersonalAdvice=()=>pending.promise;
  const work=f.makeAdvice(); state.selectedProfileId.value=22; f.onSwitchProfile();
  const old={profile_id:11,advice_id:1,actions:[{category:'DAILY_LIVING',title:'申请陪同'}]};
  pending.resolve(old); await work;
  assert.deepEqual(state.advices.value,[]);
  f.useSuggestion(old.actions[0],old); assert.equal(state.pushed.length,0);
  const current={...old,profile_id:22,advice_id:2};
  state.generatePersonalAdvice=async()=>current;await f.makeAdvice();f.useSuggestion(current.actions[0],current);
  assert.equal(state.pushed[0].query.profile_id,22);
});

test('late chat response cannot install an old session in a new profile',async()=>{
  const {state,handlers:f}=fixture(),pending=deferred();let messageReads=0;
  state.sendMessage=()=>pending.promise;state.listMessages=async()=>{messageReads++;return [{content:'A'}];};
  const work=f.send();await Promise.resolve();state.selectedProfileId.value=22;f.onSwitchProfile();
  pending.resolve({profile_id:11,session_id:1});await work;
  assert.equal(messageReads,0);assert.equal(state.currentSessionId.value,null);assert.deepEqual(state.messages.value,[]);
});

test('profile switching while history loads cannot install old messages',async()=>{
  const {state,handlers:f}=fixture(),history=deferred(),started=deferred();
  state.sendMessage=async()=>({profile_id:11,session_id:1});
  state.listMessages=()=>{started.resolve();return history.promise;};
  const work=f.send();await started.promise;state.selectedProfileId.value=22;f.onSwitchProfile();
  history.resolve([{content:'old profile'}]);await work;
  assert.equal(state.currentSessionId.value,null);assert.deepEqual(state.messages.value,[]);
});

test('late session list cannot overwrite the selected profile sessions',async()=>{
  const {state,handlers:f}=fixture(),pending=deferred();
  state.listSessions=async({profile_id})=>profile_id===11?pending.promise:[{session_id:2,profile_id:22}];
  const work=f.loadSessions();state.selectedProfileId.value=22;f.onSwitchProfile();await Promise.resolve();
  pending.resolve([{session_id:1,profile_id:11}]);await work;
  assert.equal(state.sessions.value[0].profile_id,22);
});

test('rapid session switching ignores the older history response',async()=>{
  const {state,handlers:f}=fixture(),pending=deferred();
  state.listMessages=async id=>id===1?pending.promise:[{content:'new session'}];
  const old=f.openSession({session_id:1,profile_id:11});await f.openSession({session_id:2,profile_id:11});
  pending.resolve([{content:'old session'}]);await old;
  assert.equal(state.currentSessionId.value,2);assert.equal(state.messages.value[0].content,'new session');
});

test('new session clears previous emergency and retrieval badges',()=>{
  const {state,handlers:f}=fixture();state.modelStatus.value='BYPASSED_FOR_SAFETY';state.retrievalInfo.value={semantic_embedding:false};
  f.newSession();assert.equal(state.modelStatus.value,'');assert.equal(state.retrievalInfo.value,null);
});
