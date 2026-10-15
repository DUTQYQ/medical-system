<template>
  <div class="ky-page ai-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">{{ pageTitle }}</h2>
      <div style="display: flex; align-items: center; gap: 12px">
        <span class="ky-sub">{{ profileLabel }}：</span>
        <el-select v-model="selectedProfileId" style="width: 180px" @change="onSwitchProfile">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
      </div>
    </div>

    <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-bottom:16px" />
    <el-empty v-if="!profiles.length && !error" :description="scope==='family'?'暂无已授权绑定档案，请先完成绑定':'暂无可咨询的健康档案，请先建立档案'" />
    <section v-if="canIntake && selectedProfileId" class="ky-card intake-card" v-loading="intakeLoading">
      <div class="ky-card__title">{{ isFamily ? '协助长者补充日常信息' : '先了解您的日常生活' }}</div>
      <p class="ky-sub">{{ isFamily ? '请依据您了解的实际情况代长者回答；不确定的内容可跳过。答案确认前不会作为事实用于建议。' : '首次打开会自动询问。答案先暂存，可跳过；只有您确认后才保存为个人词条，离开后可继续。' }}</p>
      <el-alert v-if="intakeError" type="error" :closable="false" :title="intakeError"><el-button @click="loadPersonal">重新加载问卷</el-button></el-alert>
      <template v-if="intake?.next_question">
        <h3>{{ intake.next_question.label }}</h3>
        <div class="intake-options"><el-button v-for="o in intake.next_question.options || []" :key="o.value || o" @click="intakeAnswer=String(o.value || o)" :type="intakeAnswer===String(o.value || o)?'primary':''">{{ o.label || o }}</el-button></div>
        <el-input v-model="intakeAnswer" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="选择上方提示或写下您的实际情况，也可以暂时跳过" />
        <el-space wrap style="margin-top:16px"><el-button type="primary" :disabled="!intakeAnswer.trim()" :loading="personalSaving" @click="answer(false)">保存答案并继续</el-button><el-button :disabled="personalSaving" @click="answer(true)">暂时跳过此题</el-button></el-space>
        <p class="ky-sub">已回答 {{ intake.answers?.length || 0 }} 项。信息仅用于授权档案的康养服务。</p>
      </template>
      <template v-else-if="intake?.status==='READY_TO_CONFIRM'">
        <h3>请确认要保存的个人词条</h3><p class="ky-sub">可在保存前修改，跳过的题目不会作为事实保存。</p>
        <el-form label-position="top"><el-form-item v-for="a in confirmationEntries" :key="a.key" :label="a.label || a.key"><el-input v-model="a.value" type="textarea" :rows="2" maxlength="500" /></el-form-item></el-form>
        <el-empty v-if="!confirmationEntries.length" description="全部题目已跳过，本次不会保存个人词条" /><el-button type="primary" :disabled="!canConfirmIntake" :loading="personalSaving" @click="confirmAnswers">确认并保存词条</el-button>
      </template>
      <el-alert v-else-if="intake?.status==='CONFIRMED'" type="success" :closable="false" title="本次问答已完成。您可以修改个人词条，或根据已确认信息生成新的建议。" />
    </section>
    <section v-if="selectedProfileId" class="ky-card">
      <div class="ky-page-header"><h3 class="ky-card__title">{{ isCare ? '长者康养信息词条' : isFamily ? '长者生活信息与来源' : '个人生活信息与来源' }}</h3><el-space><el-button v-if="canEditFacts" type="primary" @click="openNewFact()">{{ isFamily ? '补充家属观察' : '添加个人词条' }}</el-button><el-button @click="loadFacts">刷新词条</el-button></el-space></div>
      <p v-if="isCare" class="ky-sub">仅查看本人负责档案中经用户确认的生活信息；护工账号不能代替老人或家属修改自述。</p><p v-if="isFamily" class="ky-sub">家属可在已绑定档案范围内协助维护生活信息；新增或修改内容会记录报告人与版本，建议与长者或负责护工核实。</p>
      <el-table :data="facts"><el-table-column prop="label" label="词条" min-width="150" /><el-table-column label="已确认信息" min-width="220"><template #default="{row}">{{ factValue(row.value) }}</template></el-table-column><el-table-column label="状态与版本" min-width="130"><template #default="{row}"><el-tag :type="row.is_current===false?'warning':'success'">{{ row.status==='EXPIRED'?'已过期':'已确认' }}</el-tag><div class="ky-sub">版本 {{ row.version || 1 }}</div></template></el-table-column><el-table-column label="确认时间与来源" min-width="200"><template #default="{row}">{{ fmtDate(row.confirmed_at) }}<p class="ky-sub">{{ row.source || '由用户确认' }}</p><p v-if="row.status==='EXPIRED'" class="ky-sub">近期信息已过期，不再用于当前建议；请核对后更新。</p></template></el-table-column><el-table-column v-if="canEditFacts" label="操作" width="150"><template #default="{row}"><el-button v-if="canEditFact(row)" link type="primary" @click="editingFact=row;factDraft=factValue(row.value);sourceMessageId=null;factDialog=true">修改</el-button><el-button v-if="canEditFact(row)" link type="danger" @click="revokeFact(row)">撤销</el-button></template></el-table-column></el-table><el-empty v-if="!facts.length" :description="isCare?'暂无已确认词条':'尚无已确认词条，完成上方问答并确认后保存'" />
    </section>
    <section v-if="selectedProfileId" class="ky-card">
      <div class="ky-page-header"><h3 class="ky-card__title">{{ isCare ? '护理工作建议' : isFamily ? '家属照护建议' : '您的康养建议' }}</h3><el-button type="primary" :loading="adviceLoading" @click="makeAdvice">{{ isCare ? '生成照护建议' : '根据已确认信息生成建议' }}</el-button></div>
      <p class="ky-sub">{{ isCare ? '建议供负责护工沟通和协同参考，需按院内流程核实；模型不会创建或完成护理任务。' : isFamily ? '建议围绕如何支持长者与联系工作人员；家属观察应与长者或护工核实。' : '建议按生成时的信息留存。词条修改或撤销后，请重新生成建议以使用最新信息。' }}</p><el-empty v-if="!advices.length" description="尚未生成建议，请先确认生活信息" />
      <el-select v-if="advices.length>1" v-model="adviceId" placeholder="选择建议版本" style="width:100%;margin-bottom:16px"><el-option v-for="a in advices" :key="a.advice_id || a.id" :label="a.title+' · '+fmtDate(a.created_at)+' · '+(a.mode==='MODEL'?'模型辅助':'规则建议')" :value="a.advice_id || a.id" /></el-select><article v-for="a in visibleAdvices" :key="a.advice_id || a.id" class="advice-card"><h3>{{ a.title }}</h3><el-tag :type="a.mode==='MODEL'?'success':'info'">{{ a.mode==='MODEL'?'模型辅助建议':'规则生成建议' }}</el-tag><p v-if="a.generation_note" class="ky-sub">{{ a.generation_note }}</p><div class="advice-sections"><section v-for="s in a.sections || []" :key="s.title"><h4>{{ s.title }}</h4><ul><li v-for="(item,index) in s.items || []" :key="index">{{ item }}</li></ul></section></div><p v-if="a.sources?.length" class="ky-sub">参考信息：{{ a.sources.map(s=>typeof s==='string'?s:s.title || s.label || s.source || ((factLabels[s.key] || '个人词条')+'，版本 '+s.version)).join('、') }}</p><el-space v-if="!isCare" wrap><el-button v-for="(action,index) in a.actions || []" :key="index" @click="useSuggestion(action,a)">{{ action.title }} · 查看申请</el-button></el-space><p v-if="!isCare && a.actions?.length" class="ky-sub">点击后进入服务申请，核对地点与需求后再确认提交。</p></article>
    </section>
    <el-dialog v-if="canEditFacts" v-model="factDialog" :title="editingFact?'修改个人词条 · '+editingFact.label:(isFamily?'确认添加家属观察':'确认添加个人词条')" width="min(620px,95vw)"><el-form-item v-if="!editingFact" label="词条类型"><el-select v-model="factKey" placeholder="请选择这条信息所属类型"><el-option v-for="(label,key) in factLabels" :key="key" :label="label" :value="key" /></el-select></el-form-item><el-alert type="info" :closable="false" :title="isFamily?'请填写您观察到的实际情况，提交后会标记为家属报告；聊天消息与模型回答不会自动保存。':'请确认以下内容是老人当前的实际情况；聊天消息与模型回答不会自动保存。'" style="margin-bottom:14px" /><el-input v-model="factDraft" type="textarea" :rows="3" maxlength="500" show-word-limit /><template #footer><el-button @click="factDialog=false">取消</el-button><el-button type="primary" :loading="personalSaving" @click="saveFact">{{ editingFact?'确认修改':'确认保存' }}</el-button></template></el-dialog>
    <el-collapse :model-value="['chat']" style="margin-top:20px"><el-collapse-item :title="chatSectionTitle" name="chat">
    <el-alert v-if="retrievalInfo?.semantic_embedding === false" type="info" :closable="false" title="当前知识来源匹配能力有限，请结合已确认信息与人工照护意见。" style="margin-bottom:16px" /><el-alert v-if="modelStatus==='BYPASSED_FOR_SAFETY'" type="warning" :closable="false" title="紧急求助提示由安全规则生成，已触发预警；请立即寻求人工医疗帮助。" style="margin-bottom:16px" /><div class="ai-layout">
      <!-- 左侧会话列表 -->
      <aside class="ai-sessions ky-card">
        <el-button v-if="canChat" type="primary" style="width: 100%" @click="newSession">＋ 新建咨询</el-button><h3 v-else>我的护理咨询记录</h3>
        <div class="ai-sessions__list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="ai-session-item" tabindex="0" role="button"
            :class="{ 'ai-session-item--active': s.session_id === currentSessionId }"
            @click="openSession(s)" @keydown.enter="openSession(s)"
          >
            <div class="ai-session-item__title">{{ s.title }}</div>
            <div class="ai-session-item__time">{{ fmtDate(s.created_at) }}</div>
            <el-button v-if="s.can_delete !== false" link type="danger" size="small" @click.stop="removeSession(s)">删除</el-button>
          </div>
          <div v-if="!sessions.length" class="ky-empty">暂无历史会话</div>
        </div>
      </aside>

      <!-- 右侧聊天窗 -->
      <section class="ai-chat ky-card">
        <div v-if="!profiles.length" class="ky-empty">
          {{ isFamily ? '尚未绑定老人，请先前往「绑定老人」完成绑定后再咨询' : isCare ? '暂无负责老人档案，请先建立照护关系' : '暂无可咨询的健康档案' }}
        </div>

        <template v-else>
          <div ref="chatBody" class="ai-chat__body">
            <div v-if="!messages.length" class="ai-chat__hint">
              <p v-if="isElder">您好，我是您的健康与生活助手。可以咨询健康记录、睡眠、活动和院内服务。</p><p v-else-if="isFamily">这里为已绑定长者提供家属照护咨询，可了解健康记录并讨论如何沟通、联系护工和申请院内服务。</p><p v-else>这里为您负责的老人提供护理工作参考，可咨询沟通、观察和院内服务协同；不能代替医护判断。</p>
              <div v-if="canChat" class="ai-presets">
                <el-tag v-for="q in presets" :key="q" class="ai-preset" tabindex="0" role="button" @click="sendPreset(q)" @keydown.enter="sendPreset(q)">{{ q }}</el-tag>
              </div>
            </div>

            <div v-for="m in messages" :key="m.message_id" class="ai-msg">
              <div class="ai-msg__bubble" :class="m.role === 'user' ? 'ky-bubble--user' : 'ky-bubble--ai'">
                <div v-if="m.role === 'assistant'" class="ai-msg__meta">
                  <el-tag size="small" :type="safetyType(m.safety_level)">{{ safetyText(m.safety_level) }}</el-tag>
                  <el-tag size="small" type="info" v-if="m.intent">{{ intentText(m.intent) }}</el-tag>
                </div>
                <div style="white-space: pre-wrap">{{ m.content }}</div><el-button v-if="canEditFacts && m.role==='user' && !String(m.message_id).startsWith('pending-')" link @click="openNewFact(m)">将此信息保存为词条</el-button>
                <div v-if="m.sources && m.sources.length" class="ai-msg__sources">
                  参考来源：{{ m.sources.map(x => typeof x === 'string' ? x : x.title || x.source || '知识条目').join('、') }}
                </div>
              </div>
            </div>

            <div v-if="loading" class="ai-msg">
              <div class="ky-bubble ky-bubble--ai">正在思考…</div>
            </div>
          </div>

          <div v-if="canChat" class="ai-chat__input">
            <el-input
              v-model="input"
              type="textarea"
              :rows="2"
              maxlength="500"
              show-word-limit
              :placeholder="chatPlaceholder"
              @keydown.enter.exact.prevent="send"
            />
            <el-button type="primary" :disabled="!input.trim() || loading" @click="send">发送</el-button>
          </div>
        </template>
      </section>
    </div>
    </el-collapse-item></el-collapse>


  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fmtDate } from '@/utils/format'
import { getUser } from '@/utils/auth'
import { listProfiles, listSessions, listMessages, sendMessage, deleteSession, startIntake,answerIntake,confirmIntake,listPersonalFacts,createPersonalFact,updatePersonalFact,revokePersonalFact,generatePersonalAdvice,listPersonalAdvice } from '@/api'
const route=useRoute(),router=useRouter(),scope=route.meta.scope||'elder',user=getUser(),role=user?.role
const isElder=role==='ELDER',isFamily=role==='FAMILY',isCare=role==='CARE'
const canChat=['ELDER','FAMILY','CARE'].includes(role),canIntake=['ELDER','FAMILY'].includes(role),canEditFacts=['ELDER','FAMILY'].includes(role)
const pageTitle=isElder?'健康与生活助手':isFamily?'家属照护助手':'护理工作助手'
const profileLabel=isElder?'本人档案':isFamily?'已绑定老人': '负责老人'
const chatSectionTitle=isElder?'健康咨询与历史记录':isFamily?'家属照护咨询与记录':'护理工作咨询与记录'
const chatPlaceholder=isElder?'请输入您想咨询的健康或生活问题…':isFamily?'请输入您对长者照护、健康记录或院内服务的疑问…':'请输入护理沟通、观察或院内服务协同问题…'
const canConfirmIntake=computed(()=>isElder || isFamily)
const profiles=ref([]),selectedProfileId=ref(null),sessions=ref([]),currentSessionId=ref(null),messages=ref([]),input=ref(''),loading=ref(false),chatBody=ref(null),error=ref('')
const retrievalInfo=ref(null), modelStatus=ref('')
let viewVersion=0
function sameView(id,version){return id===selectedProfileId.value && version===viewVersion}
const intake=ref(null),intakeAnswer=ref(''),intakeLoading=ref(false),intakeError=ref(''),personalSaving=ref(false),confirmationEntries=ref([]),facts=ref([]),advices=ref([]),adviceLoading=ref(false),factDialog=ref(false),editingFact=ref(null),adviceId=ref(null),factDraft=ref(''),factKey=ref(''),sourceMessageId=ref(null)
const presets=isElder?['我最近睡眠不好，可以怎么调整？','我想参加打牌或锻炼活动，怎样申请？','我对近期健康记录有疑问。']:
  isFamily?['家属能怎样帮助老人改善睡眠？','老人想参加打牌或锻炼活动，家属如何申请？','我应该怎样和负责护工沟通老人的近况？']:
  ['老人睡眠情况需要怎样观察和记录？','安排活动前如何确认老人需要陪同？','家属提出日常协助需求后，院内怎样跟进？']
const SAFETY={L1:{text:'L1 日常健康建议',type:'success'},L2:{text:'L2 数据建议',type:'info'},L3:{text:'L3 异常关注',type:'warning'},L4:{text:'L4 紧急求助',type:'danger'}}
const INTENT={NORMAL:'日常咨询',DATA:'健康数据',ABNORMAL:'异常关注',EMERGENCY:'紧急求助'}
function safetyType(v){return SAFETY[v]?.type||'info'}
function safetyText(v){return SAFETY[v]?.text||v||'健康建议'}
function intentText(v){return INTENT[v]||v}
async function loadSessions(){const id=selectedProfileId.value,version=viewVersion;if(!id)return;try{const rows=await listSessions({profile_id:id});if(sameView(id,version))sessions.value=rows}catch(e){if(sameView(id,version))error.value=e.message}}
async function openSession(s){const changed=s.profile_id!==selectedProfileId.value;newSession();selectedProfileId.value=s.profile_id;currentSessionId.value=s.session_id;const id=s.profile_id,version=viewVersion;if(changed){intake.value=null;facts.value=[];advices.value=[];loadPersonal();loadSessions()}try{const rows=await listMessages(s.session_id);if(sameView(id,version)&&currentSessionId.value===s.session_id){messages.value=rows;await scrollBottom()}}catch(e){if(sameView(id,version))error.value=e.message}}
function newSession(){viewVersion++;currentSessionId.value=null;messages.value=[];input.value='';error.value='';retrievalInfo.value=null;modelStatus.value=''}
async function removeSession(s){try{await ElMessageBox.confirm('确认删除会话 '+s.title+'？','删除会话',{type:'warning'});await deleteSession(s.session_id);sessions.value=sessions.value.filter(x=>x.session_id!==s.session_id);if(currentSessionId.value===s.session_id)newSession()}catch(e){if(!['cancel','close'].includes(e))ElMessage.error(e.message)}}
function onSwitchProfile(){newSession();sessions.value=[];intake.value=null;facts.value=[];advices.value=[];adviceId.value=null;factDialog.value=false;editingFact.value=null;sourceMessageId.value=null;loadSessions();loadPersonal()}
const visibleAdvices=computed(()=>advices.value.filter(a=>(a.advice_id || a.id)===adviceId.value).slice(0,1))
const factLabels={life_goal:'生活目标',entertainment_preferences:'娱乐偏好',movement_ability:'行动能力',assistance_needs:'协助需求',food_preferences:'饮食偏好',sleep_concerns:'近期睡眠'}
function openNewFact(message){editingFact.value=null;factKey.value='';factDraft.value=message?.content || '';sourceMessageId.value=Number.isInteger(Number(message?.message_id))&&Number(message?.message_id)>0?Number(message.message_id):null;factDialog.value=true}
function canEditFact(){return isElder || isFamily}
function factValue(value){return Array.isArray(value)?value.join('、'):String(value ?? '')}
function setIntake(data){intake.value=data;intakeAnswer.value='';confirmationEntries.value=(data.answers || []).filter(a=>!a.skipped).map(a=>({...a,value:factValue(a.value)}))}
async function loadPersonal(){if(!selectedProfileId.value)return;const id=selectedProfileId.value,version=viewVersion;intakeLoading.value=canIntake;intakeError.value='';try{const [i,f,a]=await Promise.all([canIntake?startIntake(id):Promise.resolve(null),listPersonalFacts(id),listPersonalAdvice(id)]);if(sameView(id,version)){if(i)setIntake(i);facts.value=f;advices.value=a.filter(card=>card.profile_id===id);adviceId.value=advices.value[0]?.advice_id || advices.value[0]?.id}}catch(e){if(sameView(id,version)){if(canIntake)intakeError.value=e.message;else error.value=e.message}}finally{if(sameView(id,version))intakeLoading.value=false}}
async function loadFacts(){const id=selectedProfileId.value,version=viewVersion;try{const rows=await listPersonalFacts(id);if(sameView(id,version))facts.value=rows}catch(e){if(sameView(id,version))error.value=e.message}}
async function answer(skip){if(personalSaving.value)return;const id=selectedProfileId.value,version=viewVersion;personalSaving.value=true;try{const result=await answerIntake(intake.value.intake_id,{key:intake.value.next_question.key,value:intakeAnswer.value,skip});if(sameView(id,version))setIntake(result)}catch(e){if(sameView(id,version))intakeError.value=e.message}finally{personalSaving.value=false}}
async function confirmAnswers(){if(personalSaving.value)return;if(confirmationEntries.value.some(a=>!a.value.trim()))return ElMessage.warning('请补全需要保存的词条内容');const id=selectedProfileId.value,version=viewVersion;personalSaving.value=true;try{await confirmIntake(intake.value.intake_id,confirmationEntries.value.map(({key,value})=>({key,value})));if(!sameView(id,version))return;const result=await startIntake(id);if(!sameView(id,version))return;setIntake(result);await loadFacts();ElMessage.success('个人词条已确认保存')}catch(e){if(sameView(id,version))intakeError.value=e.message}finally{personalSaving.value=false}}
async function saveFact(){if(personalSaving.value)return;if(!factDraft.value.trim())return ElMessage.warning('请填写实际信息');if(!editingFact.value && !factKey.value)return ElMessage.warning('请选择词条类型');const id=selectedProfileId.value,version=viewVersion;personalSaving.value=true;try{if(editingFact.value)await updatePersonalFact(editingFact.value.fact_id || editingFact.value.id,factDraft.value);else await createPersonalFact({profile_id:id,key:factKey.value,value:factDraft.value,...(sourceMessageId.value?{source_message_id:sourceMessageId.value}:{})});if(!sameView(id,version))return;factDialog.value=false;await loadFacts();ElMessage.success('词条已更新，重新生成建议可使用最新信息')}catch(e){if(sameView(id,version)){error.value=e.message;ElMessage.error(e.message)}}finally{personalSaving.value=false}}
async function revokeFact(f){const id=selectedProfileId.value,version=viewVersion;try{await ElMessageBox.confirm('撤销后，新建议将不再使用这条信息；审计记录仍保留。','撤销个人词条');if(!sameView(id,version))return;await revokePersonalFact(f.fact_id || f.id);if(!sameView(id,version))return;await loadFacts();ElMessage.success('词条已撤销')}catch(e){if(sameView(id,version)&&!['cancel','close'].includes(e)){error.value=e.message;ElMessage.error(e.message)}}}
async function makeAdvice(){if(adviceLoading.value||!selectedProfileId.value)return;const id=selectedProfileId.value,version=viewVersion;adviceLoading.value=true;error.value='';try{const a=await generatePersonalAdvice(id);if(!sameView(id,version))return;if(a.profile_id!==id)throw new Error('建议所属档案不一致，请刷新');adviceId.value=a.advice_id || a.id;advices.value=[a,...advices.value.filter(x=>(x.advice_id || x.id)!==(a.advice_id || a.id))]}catch(e){if(sameView(id,version))error.value=e.message}finally{adviceLoading.value=false}}
function useSuggestion(action,advice){if(!advice || advice.profile_id!==selectedProfileId.value)return ElMessage.warning('建议属于其他档案，请切回对应老人后核对');const category=action.category==='DAILY_CARE'?'DAILY_LIVING':action.category;const query={profile_id:advice.profile_id,category,description:action.description || ''};if(category==='EQUIPMENT')query.tab='equipment';else{query.title=action.title;query.tab='requests'}router.push({path:'/'+scope+'/services',query})}
async function send(){
 const content=input.value.trim();if(!canChat||!content||!selectedProfileId.value||loading.value)return
 const id=selectedProfileId.value,version=viewVersion,sessionId=currentSessionId.value
 loading.value=true;error.value='';input.value=''
 const tmp={message_id:'pending-'+Date.now(),role:'user',content};messages.value.push(tmp);await scrollBottom()
 try{const reply=await sendMessage({session_id:sessionId,profile_id:id,content});if(!sameView(id,version))return;if(reply.profile_id!==id)throw new Error('咨询所属档案不一致，请刷新');const rows=await listMessages(reply.session_id);if(!sameView(id,version))return;currentSessionId.value=reply.session_id;messages.value=rows;retrievalInfo.value=reply.retrieval||null;modelStatus.value=reply.model_status||'';await loadSessions()}
 catch(e){if(sameView(id,version)){error.value=e.message;input.value=content;messages.value=messages.value.filter(m=>m!==tmp);await loadSessions()}}
 finally{loading.value=false;await scrollBottom()}
}
function sendPreset(q){input.value=q;send()}
async function scrollBottom(){await nextTick();if(chatBody.value)chatBody.value.scrollTop=chatBody.value.scrollHeight}
onMounted(async()=>{try{profiles.value=await listProfiles();selectedProfileId.value=profiles.value.find(p=>p.profile_id===Number(route.query.profile_id))?.profile_id||profiles.value[0]?.profile_id;await Promise.all([loadSessions(),loadPersonal()])}catch(e){error.value=e.message}})
</script>


<style scoped>
.intake-options{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}.advice-card{border:1px solid #e4e7ed;border-radius:10px;padding:18px;margin-bottom:18px;line-height:1.8}.advice-card h3{margin-top:0}.advice-sections{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:18px}.advice-sections h4{margin-bottom:8px}.advice-sections ul{padding-left:24px;margin-top:0}.intake-card{margin-bottom:16px}
.ai-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
}
.ai-sessions__list {
  margin-top: 16px;
  max-height: 560px;
  overflow-y: auto;
}
.ai-session-item {
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}
.ai-session-item--active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}
.ai-session-item__title {
  font-weight: 600;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-session-item__time {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.ai-chat {
  display: flex;
  flex-direction: column;
  min-height: 560px;
}
.ai-chat__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  max-height: 480px;
}
.ai-chat__hint {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 40px 0;
}
.ai-presets {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
.ai-preset {
  cursor: pointer;
}
.ai-msg {
  margin-bottom: 16px;
  display: flex;
}
.ai-msg__bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
}
.ai-msg__meta {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.ai-msg__sources {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.ai-chat__input {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}
@media (max-width: 820px) {
  .ai-layout {
    grid-template-columns: 1fr;
  }
}
</style>
