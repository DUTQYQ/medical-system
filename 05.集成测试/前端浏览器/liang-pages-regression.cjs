// Real contributed Vue handlers: profile isolation, stale errors and safe prefill.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'../../04.编码/前端');
const parse=createRequire(path.join(root,'package.json'))('@babel/parser').parse;
function handlers(file,state,names){
  const src=fs.readFileSync(path.join(root,'src',file),'utf8').split('<script setup>')[1].split('</script>')[0];
  const functions=parse(src,{sourceType:'module'}).program.body.filter(n=>n.type==='FunctionDeclaration').map(n=>src.slice(n.start,n.end)).join('\n');
  return new Function('state','with(state){'+functions+';return {'+names.join(',')+'};}')(state);
}
function pending(){let resolve;return {promise:new Promise(r=>resolve=r),resolve};}
function fixture(kind){
  const s={requestVersion:0,pushed:[],warnings:[],router:{push:v=>s.pushed.push(v)},ElMessage:{warning:m=>s.warnings.push(m)},
    getHealthStatus:async()=>[],getRecommendations:async()=>[]};
  for(const [key,value]of Object.entries({profileId:11,items:[],list:[],loading:false,error:''}))s[key]={value};
  const file=kind==='health'?'HealthStatus.vue':'ActivityRecommend.vue';
  const names=kind==='health'?['load']:['load','requestActivity'];
  return {s,f:handlers('views/elder/'+file,s,names)};
}
for(const kind of ['health','activities'])test(kind+' ignores a late previous-profile result',async()=>{
  const {s,f}=fixture(kind),a=pending(),api=kind==='health'?'getHealthStatus':'getRecommendations',field=kind==='health'?'items':'list';
  s[api]=async id=>id===11?a.promise:[{profile_id:id}];
  const old=f.load();s.profileId.value=22;await f.load();a.resolve([{profile_id:11}]);await old;
  assert.equal(s[field].value[0].profile_id,22);assert.equal(s.loading.value,false);
});
for(const kind of ['health','activities'])test(kind+' clears stale data and exposes load errors',async()=>{
  const {s,f}=fixture(kind),api=kind==='health'?'getHealthStatus':'getRecommendations',field=kind==='health'?'items':'list';
  s[field].value=[{profile_id:11}];s[api]=async()=>{throw new Error('网络测试故障');};await f.load();
  assert.deepEqual(s[field].value,[]);assert.equal(s.error.value,'网络测试故障');
});
test('newer refresh wins for the same profile',async()=>{
  const {s,f}=fixture('health'),a=pending();let calls=0;s.getHealthStatus=async()=>++calls===1?a.promise:[{record_id:2}];
  const old=f.load();await f.load();a.resolve([{record_id:1}]);await old;assert.equal(s.items.value[0].record_id,2);
});
test('recommendation action only prefills the current approved-to-request card',()=>{
  const {s,f}=fixture('activities');const base={profile_id:11,can_request:true,name:'棋牌活动',service_category:'ENTERTAINMENT'};
  f.requestActivity({...base,profile_id:22});f.requestActivity({...base,can_request:false});assert.equal(s.pushed.length,0);
  f.requestActivity(base);assert.equal(s.pushed[0].path,'/elder/services');assert.equal(s.pushed[0].query.profile_id,11);
  assert.equal(s.pushed[0].query.category,'ENTERTAINMENT');assert.match(s.pushed[0].query.description,/核验/);
});
test('friendly rule form preserves zero ages and removes empty controls',()=>{
  const s={form:{value:{suitable:{min_age:0,max_age:70,chronic_in:[],seasons_in:['autumn'],seasons_not_in:[]},avoid:{min_age:null,seasons_in:[]},cautionLevel:2}}};
  const f=handlers('views/admin/Activities.vue',s,['rulesFromForm']);
  assert.deepEqual(f.rulesFromForm(),{suitable:{min_age:0,max_age:70,seasons_in:['autumn']},caution:{max_risk_level:2}});
});
