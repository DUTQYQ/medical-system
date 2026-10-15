// Exercise the real Vue handlers with delayed responses and profile switches.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'../../04.编码/前端');
const parse=createRequire(path.join(root,'package.json'))('@babel/parser').parse;
function handlers(file,state,names){
  const source=fs.readFileSync(path.join(root,'src/components/common',file),'utf8').split('<script setup>')[1].split('</script>')[0];
  const functions=parse(source,{sourceType:'module'}).program.body.filter(n=>n.type==='FunctionDeclaration').map(n=>source.slice(n.start,n.end)).join('\n');
  return new Function('state','with(state){'+functions+';return {'+names.join(',')+'};}')(state);
}
function refs(state,values){for(const [key,value] of Object.entries(values))state[key]={value};}
function pending(){let resolve;return {promise:new Promise(r=>resolve=r),resolve};}
function service(){
  const s={viewVersion:0,requestsVersion:0,loansVersion:0,detailVersion:0,registrationsVersion:0,staff:false,userId:3,
    submitted:[],warnings:[],asList:d=>Array.isArray(d)?d:d.list,route:{query:{}},
    listServiceRequests:async()=>({list:[],total:0}),listServiceLoans:async()=>[],
    listServiceNotifications:async()=>({list:[],unread_count:0}),getServiceRequest:async()=>({id:1}),
    createServiceRequest:async body=>s.submitted.push(body),createServiceCall:async body=>s.submitted.push(body),
    requestServiceEquipment:async(id,body)=>s.submitted.push(body),
    ElMessage:{warning:m=>s.warnings.push(m),error:()=>{},success:()=>{}},ElMessageBox:{confirm:async()=>{}}};
  refs(s,{profileId:11,profiles:[{profile_id:11,location:'A'},{profile_id:22,location:'B'}],normalCategories:[{category:'OTHER'}],
    requests:[],total:0,page:1,filter:{},loans:[],detail:null,error:'',acting:false,requestDialog:false,borrowDialog:false,
    detailDialog:false,returnDialog:false,registrationsDialog:false,requestProfileId:null,requestForm:{},callMode:false,
    borrowProfileId:null,borrowForm:{},selectedEquipment:null,transitionResult:'',notifications:[],unread:0});
  const f=handlers('ServiceCenter.vue',s,['loadRequests','loadLoans','profileChanged','openRequest','submitRequest','openEquipment','submitBorrow','openDetail','transition']);
  return {s,f};
}
test('service lists discard an older profile response',async()=>{
  const {s,f}=service(),a=pending();s.listServiceRequests=async({profile_id})=>profile_id===11?a.promise:{list:[{profile_id}],total:1};
  const old=f.loadRequests();s.profileId.value=22;f.profileChanged();await f.loadRequests();a.resolve({list:[{profile_id:11}],total:1});await old;
  assert.equal(s.requests.value[0].profile_id,22);assert.equal(s.page.value,1);
});
test('newer service filter results win within the same profile',async()=>{
  const {s,f}=service(),a=pending();s.listServiceRequests=async({page})=>page===1?a.promise:{list:[{page}],total:2};
  const old=f.loadRequests();s.page.value=2;await f.loadRequests();a.resolve({list:[{page:1}],total:2});await old;assert.equal(s.requests.value[0].page,2);
});
test('service and equipment forms cannot submit for a newly selected elder',async()=>{
  const {s,f}=service();f.openRequest({title:'A 需求',description:'A 内容'});f.openEquipment({id:5});s.profileId.value=22;
  await f.submitRequest();await f.submitBorrow();assert.equal(s.submitted.length,0);assert.equal(s.warnings.length,2);
});
test('late submitted service cannot close or clear a new elder form',async()=>{
  const {s,f}=service(),a=pending();s.createServiceRequest=async body=>{s.submitted.push(body);return a.promise;};
  f.openRequest({title:'A 需求',description:'A 内容'});const old=f.submitRequest();s.profileId.value=22;f.profileChanged();f.openRequest({title:'B 需求',description:'B 内容'});
  a.resolve();await old;assert.equal(s.submitted[0].profile_id,11);assert.equal(s.requestDialog.value,true);assert.equal(s.requestForm.value.title,'B 需求');
});
test('late service detail does not reopen a previous elder dialog',async()=>{
  const {s,f}=service(),a=pending();s.getServiceRequest=()=>a.promise;const old=f.openDetail({id:1});s.profileId.value=22;f.profileChanged();a.resolve({id:1,profile_id:11});await old;
  assert.equal(s.detailDialog.value,false);assert.equal(s.detail.value,null);
});
test('switching during cancellation confirmation prevents cancelling another task',async()=>{
  const {s,f}=service(),a=pending();let calls=0;s.ElMessageBox.confirm=()=>a.promise;s.transitionServiceRequest=async()=>calls++;
  s.detail.value={id:1,status:'SUBMITTED'};const old=f.transition('CANCELLED');s.profileId.value=22;f.profileChanged();a.resolve();await old;assert.equal(calls,0);
});
test('loan lists are scoped to the selected elder and reject late responses',async()=>{
  const {s,f}=service(),a=pending();s.listServiceLoans=async({profile_id})=>profile_id===11?a.promise:[{profile_id}];
  const old=f.loadLoans();s.profileId.value=22;f.profileChanged();await f.loadLoans();a.resolve([{profile_id:11}]);await old;assert.equal(s.loans.value[0].profile_id,22);
});
function health(){
  const s={viewVersion:0,thresholdVersion:0,values:{value:75},emitted:[],warnings:[],
    measuredNow:()=>new Date().toISOString().slice(0,19),getPersonalThresholds:async()=>({rules:[]}),
    ElMessage:{warning:m=>s.warnings.push(m),success:()=>{},error:()=>{}},ElMessageBox:{alert:async()=>{}},emit:(...args)=>s.emitted.push(args)};
  refs(s,{profileId:11,type:'HEART_RATE',current:{fields:[{key:'value',label:'心率'}],integer:true},measuredAt:'2026-01-01 12:00:00',
    remark:'A 测量',saving:false,thresholds:[],error:''});
  return {s,f:handlers('HealthInput.vue',s,['validateInput','loadThresholds','profileChanged','save'])};
}
test('health validation enforces numbers, configured ranges and measurement time',()=>{
  const {s,f}=health();assert.equal(f.validateInput(),'');s.values.value=75.5;assert.match(f.validateInput(),/整数/);
  s.values.value=NaN;assert.match(f.validateInput(),/有限数字/);s.values.value=75;s.current.value.ranges={value:[80,100]};assert.match(f.validateInput(),/80/);
  s.current.value.ranges={};s.measuredAt.value='2999-01-01 00:00:00';assert.match(f.validateInput(),/未来/);
});
test('health validation covers pressure ordering, sleep quality and decimal precision',()=>{
  const {s,f}=health();s.type.value='BLOOD_PRESSURE';s.current.value={fields:[{key:'systolic'},{key:'diastolic'}],integer:true};s.values={systolic:80,diastolic:100};assert.match(f.validateInput(),/收缩压/);
  s.type.value='SLEEP';s.current.value={fields:[{key:'hours'},{key:'quality'}]};s.values={hours:25,quality:3};assert.match(f.validateInput(),/24/);
  s.values={hours:8,quality:1.5};assert.match(f.validateInput(),/质量/);s.type.value='BLOOD_SUGAR';s.current.value={fields:[{key:'value'}]};s.values={value:6.111};assert.match(f.validateInput(),/两位小数/);
});
test('late health threshold hints cannot replace another elder rules',async()=>{
  const {s,f}=health(),a=pending();s.getPersonalThresholds=async id=>id===11?a.promise:{rules:['B']};
  const old=f.loadThresholds();s.profileId.value=22;f.profileChanged();await f.loadThresholds();a.resolve({rules:['A']});await old;assert.deepEqual(s.thresholds.value,['B']);
});
test('late saved measurement does not reset another elder inputs',async()=>{
  const {s,f}=health(),a=pending();let body;s.addRecord=async b=>{body=b;return a.promise;};const old=f.save();s.profileId.value=22;f.profileChanged();s.values.value=88;s.remark.value='B 测量';a.resolve({is_abnormal:false});await old;
  assert.equal(body.profile_id,11);assert.equal(s.values.value,88);assert.equal(s.remark.value,'B 测量');assert.equal(s.emitted.length,0);
});
function thresholds(){
  const s={viewVersion:0,loadVersion:0,warnings:[],submitted:[],getPersonalThresholds:async id=>({profile_id:id,rules:[]}),
    proposePersonalThreshold:async(id,body)=>s.submitted.push({id,body}),ElMessage:{warning:m=>s.warnings.push(m),success:()=>{},error:()=>{}}};
  refs(s,{profileId:11,data:{profile_id:11,rules:[]},formProfileId:null,form:{},restore:false,dialog:false,loading:false,error:'',saving:false});
  return {s,f:handlers('PersonalThresholds.vue',s,['loadRules','profileChanged','open','submit'])};
}
test('late personal threshold rules cannot overwrite the current elder',async()=>{
  const {s,f}=thresholds(),a=pending();s.getPersonalThresholds=async id=>id===11?a.promise:{profile_id:id,rules:['B']};const old=f.loadRules();s.profileId.value=22;f.profileChanged();await f.loadRules();a.resolve({profile_id:11,rules:['A']});await old;assert.equal(s.data.value.profile_id,22);
});
test('threshold proposals keep their target and reject stale forms',async()=>{
  const {s,f}=thresholds();f.open({indicator:'HEART_RATE'},true);s.form.value.reason='A 依据';s.profileId.value=22;await f.submit();assert.equal(s.submitted.length,0);
  s.data.value={profile_id:22};f.open({indicator:'HEART_RATE'},true);s.form.value.reason='B 依据';await f.submit();assert.equal(s.submitted[0].id,22);
});
function account(){
  const s={user:{name:'旧姓名',phone:'13000000002'},form:{name:'新姓名',phone:'13000000002',current_password:'',new_password:''},
    warnings:[],updates:[],cleared:false,redirects:[],setUser:()=>{},clearAuth:()=>s.cleared=true,
    window:{location:{assign:url=>s.redirects.push(url)}},TextEncoder,
    updateMe:async body=>{s.updates.push(body);return {name:body.name,phone:body.phone,reauth_required:true};},
    ElMessage:{warning:m=>s.warnings.push(m),success:()=>{},error:()=>{}}};
  refs(s,{saving:false});return {s,f:handlers('ProfileCenter.vue',s,['save'])};
}
test('phone changes require password before sending and clear old login on success',async()=>{
  const {s,f}=account();s.form.phone='13800000008';await f.save();assert.equal(s.updates.length,0);
  s.form.current_password='Abc123456';await f.save();assert.equal(s.updates[0].current_password,'Abc123456');assert.equal(s.cleared,true);assert.deepEqual(s.redirects,['/login']);
});
test('combined phone and password changes send one atomic account update',async()=>{
  const {s,f}=account();s.form.phone='13800000008';s.form.current_password='Abc123456';s.form.new_password='Newpass1234';await f.save();
  assert.equal(s.updates.length,1);assert.equal(s.updates[0].new_password,'Newpass1234');
});
test('weak and oversized UTF-8 passwords are rejected locally',async()=>{
  const {s,f}=account();s.form.current_password='Abc123456';for(const value of ['abc','汉'.repeat(25)]){s.form.new_password=value;await f.save();}assert.equal(s.updates.length,0);assert.equal(s.warnings.length,2);
});
