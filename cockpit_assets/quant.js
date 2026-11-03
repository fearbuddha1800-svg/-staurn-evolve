/* STAURN controller: one authenticated client, visible-only polling, no synthetic market graphics. */
(() => {
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
const titles={overview:['Overview','Account, protection and the latest activity. One clear view.'],chart:['Chart Lab','Real broker candles. Editable Pine research. No order execution.'],signals:['Signals','Follow incoming signals, recorded decisions and source channels.'],strategies:['Strategies','Inspect engine state, paper strategies and model readiness.'],intelligence:['Intelligence','Local integrations, source-backed research and sample-aware analytics.'],system:['System','Process health, safety flags and your local connection.'],luxalgo:['LuxAlgo','Technical analysis library with trend, momentum and volatility indicators']};
let active='overview',connected=false,coreBusy=false,viewBusy=false,chartBusy=false,pineBusy=false,timer,state=null,candles=[],plots={},chartContext='',traceTicket=null;
let velas=null; // { overview: STURN.VelaChart, chart: STURN.VelaChart }
const cache=new Map(),viewTimes=new Map();
const client=new window.HQClient();
let accountScope=null,lastObservation=0,lastChart=0,focusReturn=null,lastHealth=null;
let clockTimer;
let motionPaused=matchMedia('(prefers-reduced-motion: reduce)').matches,tapePaused=false;
function tickClock(){
 clearTimeout(clockTimer);const now=new Date();$('mt-clock').dateTime=now.toISOString();$('mt-clock').textContent=now.toISOString().slice(11,19)+' UTC';
 if(!document.hidden)clockTimer=setTimeout(tickClock,1000);
}
// Chart helpers consume only supplied, validated broker rows; never fabricate candles.
const chartViewport={size:0,offset:0},chartGeometry=new Map();let chartSelected=null;
function chartNumber(value){
 if(typeof value==='number')return Number.isFinite(value)?value:null;
 if(typeof value!=='string'||!/^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$/.test(value.trim()))return null;
 const number=Number(value);return Number.isFinite(number)?number:null;
}
function price(value){const n=chartNumber(value);return n===null?'Unavailable':n.toLocaleString(undefined,{maximumFractionDigits:6,minimumFractionDigits:2});}
function normaliseCandles(rows){
 const unique=new Map();if(!Array.isArray(rows))return [];
 for(const row of rows){
  if(!row||typeof row!=='object')continue;
  const values=Array.isArray(row)?row:[row.time??row.openTime,row.open,row.high,row.low,row.close,row.volume??row.tick_volume];
  const numbers=values.slice(0,5).map(chartNumber);if(numbers.length!==5||numbers.some(n=>n===null))continue;
  const [time,open,high,low,close]=numbers,ms=time<1e12?time*1000:time;
  if(ms<=0||ms>8.64e15||[open,high,low,close].some(n=>n<=0)||high<Math.max(open,close,low)||low>Math.min(open,close,high))continue;
  const volume=chartNumber(values[5]);unique.set(ms,[ms,open,high,low,close,volume!==null&&volume>=0?volume:null]);
 }
 return [...unique.values()].sort((a,b)=>a[0]-b[0]);
}
function resetChartViewport(){chartViewport.size=0;chartViewport.offset=0;chartSelected=null;chartGeometry.clear();}
function chartRange(target,width){
 const total=candles.length,automatic=Math.min(150,Math.max(30,Math.floor((width-88)/6)));
 const count=Math.min(total,target==='chart'?(chartViewport.size||automatic):automatic);
 const offset=target==='chart'?Math.min(Math.max(0,chartViewport.offset),Math.max(0,total-count)):0;
 return {start:Math.max(0,total-offset-count),end:total-offset,total,count};
}
function chartReadout(row){return new Date(row[0]).toISOString()+' · timestamp as supplied · O '+price(row[1])+' · H '+price(row[2])+' · L '+price(row[3])+' · C '+price(row[4])+' · V '+(row[5]===null?'unavailable':row[5].toLocaleString());}
function updateChartControls(){
 const range=chartRange('chart',$('chart').getBoundingClientRect().width),disabled=chartBusy||!connected||!range.total;
 for(const [id,unavailable]of [['older',!range.start],['newer',range.end===range.total],['zoom-in',range.count<=Math.min(10,range.total)],['zoom-out',range.count===range.total],['reset',false],['export',false]])$('chart-'+id).disabled=disabled||unavailable;
 $('chart-window').textContent=range.total?'Bars '+(range.start+1)+'–'+range.end+' of '+range.total+' · '+chartContext+' · loaded history only':'No broker candles loaded.';
 if(chartSelected!==null&&(chartSelected<range.start||chartSelected>=range.end))chartSelected=null;
 const selected=chartSelected??(range.end-1),row=candles[selected];
 $('chart-readout').textContent=row?(chartSelected===null?'Latest visible candle · ':'Selected candle '+(selected+1)+' · ')+chartReadout(row):'No broker candles. Select a candle or use Left/Right, Home/End when the chart has focus.';
}
function changeChartWindow(action){
 if(chartBusy||!connected||!candles.length)return;
 const range=chartRange('chart',$('chart').getBoundingClientRect().width),step=Math.max(1,Math.ceil(range.count/2));
 if(action==='older')chartViewport.offset=Math.min(range.total-range.count,chartViewport.offset+step);
 if(action==='newer')chartViewport.offset=Math.max(0,chartViewport.offset-step);
 if(action==='zoom-in')chartViewport.size=Math.min(range.total,Math.max(10,Math.floor(range.count/1.5)));
 if(action==='zoom-out')chartViewport.size=Math.min(range.total,Math.ceil(range.count*1.5));
 if(action==='reset')resetChartViewport();
 chartViewport.offset=Math.min(chartViewport.offset,Math.max(0,range.total-(chartViewport.size||range.count)));chartSelected=null;drawCharts();
}
function selectChartCandle(event){
 if(!velas||!velas.chart||chartBusy||!connected||!candles.length)return;
 drawCharts();
}
function stepChartCandle(event){
 if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)||chartBusy||!connected||!candles.length)return;
 event.preventDefault();const range=chartRange('chart',$('chart').getBoundingClientRect().width),current=chartSelected??(range.end-1);
 chartSelected=event.key==='Home'?range.start:event.key==='End'?range.end-1:Math.max(range.start,Math.min(range.end-1,current+(event.key==='ArrowLeft'?-1:1)));drawCharts();
}
function exportChartCandles(){
 if(chartBusy||!connected||!candles.length)return;
 const rows=['time_epoch_ms,time_iso_as_supplied,open,high,low,close,volume',...candles.map(row=>[row[0],new Date(row[0]).toISOString(),...row.slice(1,5),row[5]??''].join(','))];
 const blob=new Blob([rows.join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');
 link.href=url;link.download='STAURN-'+chartContext.replace(/[^a-zA-Z0-9._-]+/g,'-')+'-candles.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function loadPineRegistry(){
 if(cache.has('pine'))return;const scope=accountScope,generation=client.generation;
 try{const data=await api('pine');if(!connected||scope!==accountScope||generation!==client.generation)return;cache.set('pine',data);populatePine(data);}
 catch(e){if(connected)$('compile-message').textContent='Registry unavailable: '+e.message+'. Source editing remains local; simulation is unavailable.';}
}

function updateTelemetry(){
 const observed=state?.mt5?.account_available===true;
 $('fabric-status').textContent=!connected?'Session disconnected':observed?'Broker observed · other sources reported in their workspaces':'Broker unavailable · verify System health';
 $('mt-latency').textContent='HTTP RTT '+(Number.isFinite(client.lastRTT)?Math.round(client.lastRTT)+' ms':'unobserved');
 if(!connected)return;
 if(candles.length){const last=candles.at(-1),prior=candles.at(-2),close=Number(last[4]);
  const delta=prior&&Number(prior[4])!==0?(close/Number(prior[4])-1)*100:null;
  const stamp=Number(last[0]),iso=new Date(stamp<1e12?stamp*1000:stamp).toISOString();
  const item=el('span',chartContext+' · '+price(close)+(delta===null?'':' · Last-bar Δ '+delta.toFixed(3)+'%')+' · '+iso+' · Not a live quote','tape-item');
  $('vt-tape-top').replaceChildren(item);document.querySelector('.ribbon-scope').textContent=(chartContext.split(' · ')[1]||'Bar')+' Δ';
 }else $('vt-tape-top').replaceChildren(el('span','Broker candle prices unavailable. No simulated quotes.','tape-pending'));
 $('vt-tape-bottom').textContent=lastObservation?'Snapshot '+new Date(lastObservation).toISOString()+' · '+(accountScope||'Account unknown'):'Awaiting a broker observation';
}
function applyMotion(){document.body.classList.toggle('motion-paused',motionPaused);$('motion-toggle').setAttribute('aria-pressed',String(motionPaused));$('motion-toggle').setAttribute('aria-label',motionPaused?'Resume decorative motion':'Pause decorative motion');
 $('vt-tape-top').style.overflowX=tapePaused?'auto':'';$('tape-toggle').setAttribute('aria-pressed',String(tapePaused));$('tape-toggle').setAttribute('aria-label',tapePaused?'Resume scrolling prices':'Pause scrolling prices');}
$('motion-toggle').addEventListener('click',()=>{motionPaused=!motionPaused;applyMotion();});
$('tape-toggle').addEventListener('click',()=>{tapePaused=!tapePaused;$('vt-tape-top').style.setProperty('animation-play-state',tapePaused?'paused':'running');applyMotion();});
applyMotion();tickClock();
const moduleErrors=new Map();
const fmt=v=>v===null||v===undefined||v===''?'Unavailable':typeof v==='number'?v.toLocaleString(undefined,{maximumFractionDigits:2}):String(v);
const scalar=v=>v===null||v===undefined?'Not reported':typeof v==='boolean'?(v?'Yes':'No'):typeof v==='object'?JSON.stringify(v):String(v);
function auth(yes){
 const changed=connected!==yes;
 connected=yes;$('connect').hidden=yes;$('app').hidden=!yes;
 if(changed)window.dispatchEvent(new CustomEvent('hq:session',{detail:{authenticated:yes}}));
 if(!yes){clearTimeout(timer);client.clear();cache.clear();viewTimes.clear();state=null;lastObservation=0;moduleErrors.clear();
 document.querySelectorAll('[data-feature-host]').forEach(n=>n.replaceChildren());$('trace').hidden=true;}
 if(!yes){$('connection').textContent='Disconnected';$('view-status-chip').textContent='Disconnected';$('vt-tape-top').replaceChildren(el('span','Connect to view broker prices.','tape-pending'));$('vt-tape-bottom').textContent='Session disconnected · observations cleared';candles=[];plots={};chartContext='';resetChartViewport();drawCharts();lastChart=0;accountScope=null;}
}
async function api(path,options){try{return await client.request(path,options);}catch(e){if(e.status===401)auth(false);throw e;}}
function notice(message){$('view-status').hidden=!message;$('view-status').textContent=message||'';}
function success(){updateFreshness();}
function renderBrokerStatus(stale=false){
 const b=state?.broker,hold=b?.maintenance===true?'Maintenance':b?.halt===true?'Halted':b?.stop===true?'Stopped':b?.pause===true?'Paused':null;
 const label=!connected?'Session disconnected':stale?'Stale broker observation':hold|| (b?.connected===true?'Existing broker observed':'Broker offline / unverified');
 $('broker-condition').textContent=label;$('broker-condition').className='hq-pill '+(hold?'bad':'warn');
 $('broker-reason').textContent='Maintenance: '+flag(b?.maintenance)+' · HALT: '+flag(b?.halt)+' · '+(!connected?'Session disconnected':stale?'Observation stale':b?.blocked_reason||'Read-only observation')+'. HQ never starts or reconnects MT5; no reset or enable is performed.';
}
function updateFreshness(){
 if(!connected)return;
 const stale=lastObservation&&Date.now()-lastObservation>45000;
 const unavailable=state?.mt5?.account_available!==true||state?.mt5?.positions_available!==true;
 const halted=['halt','stop'].some(k=>state?.[k]===true),unknown=['halt','pause','stop'].some(k=>typeof state?.[k]!=='boolean');
 const processProblem=lastHealth?.processes?.some(p=>p.up!==true)||Object.values(lastHealth?.ports||{}).some(up=>up!==true);
 const status=stale?'Stale':state?.broker?.maintenance===true?'Maintenance':halted?'Halted':state?.pause===true?'Paused':state?.broker?.connected!==true?'Broker offline':unavailable||unknown||moduleErrors.size||processProblem?'Degraded':'Connected';
 renderBrokerStatus(stale);
 for(const id of ['connection','view-status-chip']){$(id).textContent=status;$(id).className='hq-pill '+(status==='Connected'?'ok':status==='Halted'?'bad':'warn');}
 $('last-sync').textContent=lastObservation?'Snapshot '+new Date(lastObservation).toLocaleTimeString()+' · MT5 / '+(accountScope||'unobserved'):'No broker observation';
}
function makeTable(headers,rows){
 const wrap=el('div',undefined,'table-wrap'),t=el('table',undefined,'data-table'),head=el('thead'),tr=el('tr'),body=el('tbody');let selected=-1,ascending=true;
 const paint=()=>{body.replaceChildren();for(const row of rows.slice(0,200)){const r=el('tr');for(const value of row){const td=el('td');value instanceof Node?td.append(value):td.textContent=scalar(value);r.append(td);}body.append(r);}};
 headers.forEach((label,index)=>{const th=el('th'),b=el('button',label);th.scope='col';b.setAttribute('aria-label','Sort by '+label);b.addEventListener('click',()=>{ascending=selected===index?!ascending:true;selected=index;head.querySelectorAll('th').forEach(n=>n.removeAttribute('aria-sort'));th.setAttribute('aria-sort',ascending?'ascending':'descending');const text=v=>v instanceof Node?v.textContent:v;rows.sort((a,b)=>String(text(a[index])??'').localeCompare(String(text(b[index])??''),undefined,{numeric:true})*(ascending?1:-1));paint();});th.append(b);tr.append(th);});
 head.append(tr);t.append(head,body);paint();wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Data table; scroll horizontally for more columns');wrap.append(t);return wrap;
}
function openEvidence(title,data){focusReturn=document.activeElement;traceTicket=null;$('trace-title').textContent=title;$('trace').hidden=false;renderData($('trace-body'),data);$('trace-close').focus();}
function closeEvidence(){$('trace').hidden=true;traceTicket=null;focusReturn?.focus();}

function empty(target,message){target.replaceChildren(el('p',message,'empty'));}
function details(data,label='Inspect raw record'){const d=el('details',undefined,'record-details');d.append(el('summary',label),el('pre',JSON.stringify(data,null,2)));return d;}
function dataList(data){const dl=el('dl',undefined,'data-list');for(const [key,value] of Object.entries(data||{})){const row=el('div');row.append(el('dt',key.replaceAll('_',' ')),el('dd',scalar(value)));dl.append(row);}return dl;}
function renderData(target,data,emptyText='No records reported for this source.'){target.replaceChildren();if(data===null||data===undefined||(Array.isArray(data)&&!data.length)||(typeof data==='object'&&!Object.keys(data).length)){empty(target,emptyText);return;}if(Array.isArray(data)){const rows=data.slice(0,100);if(rows.every(x=>x&&typeof x==='object'&&!Array.isArray(x))){const keys=[...new Set(rows.flatMap(x=>Object.keys(x)))].slice(0,10);const wrap=el('div',undefined,'table-wrap'),table=el('table',undefined,'data-table'),head=el('thead'),tr=el('tr');keys.forEach(k=>{const th=el('th',k.replaceAll('_',' '));th.scope='col';tr.append(th);});head.append(tr);table.append(head);const body=el('tbody');rows.forEach(row=>{const tr=el('tr');keys.forEach(k=>{const td=el('td');if(row[k]&&typeof row[k]==='object'){td.append(details(row[k],'Details'));}else td.textContent=scalar(row[k]);tr.append(td);});body.append(tr);});table.append(body);wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Data table · scroll horizontally for more columns');wrap.append(table);target.append(wrap);}else rows.forEach(x=>target.append(el('p',scalar(x),'panel-copy')));if(data.length>100)target.append(el('p',`Showing 100 of ${data.length} records.`,'panel-copy'));return;}if(typeof data==='object'){if(data.available===false)target.append(el('p',data.reason||'Unavailable: insufficient data or source disconnected.','empty'));const simple=Object.fromEntries(Object.entries(data).filter(([,v])=>v===null||typeof v!=='object'));if(Object.keys(simple).length)target.append(dataList(simple));for(const [key,value]of Object.entries(data)){if(value&&typeof value==='object'){const d=el('details',undefined,'record-details');d.append(el('summary',key.replaceAll('_',' ')));const child=el('div');renderData(child,value);d.append(child);target.append(d);}}}else target.append(el('p',scalar(data),'panel-copy'));}

function section(title){const p=el('section',undefined,'panel'),heading=el('div',undefined,'section-heading'),body=el('div');heading.append(el('h2',title));p.append(heading,body);return {p,body,heading};}

function renderIdentity(target,data){
 target.replaceChildren();
 if(data.available===false){empty(target,data.reason||'Strategy attribution unavailable.');target.append(details(data));return;}
 const positions=Array.isArray(data.open_positions)?data.open_positions:null;
 if(positions?.length){
  const rows=positions.map(p=>{const identity=(data.identities||[]).find(i=>String(i.magic)===String(p.magic));return {'Ticket':p.ticket,'Symbol':p.symbol,'Strategy owner':p.label??identity?.label??'Unavailable','Strategy ID':p.strategy_id??identity?.id??'Unavailable','Version':p.version??identity?.version??'Unavailable','Broker magic':p.magic};});
  renderData(target,rows);target.querySelector('table').setAttribute('aria-label','Open position strategy attribution');
 }else empty(target,positions&&state?.mt5?.positions_available!==false?'No open positions returned by attribution source.':'Open-position attribution unavailable.');
 if(data.note)target.append(el('p',data.note,'panel-copy attribution-note'));
 if(Array.isArray(data.identities)){const registry=el('details',undefined,'record-details');registry.append(el('summary',`Identity registry · ${data.identities.length} registered identities`));const body=el('div');renderData(body,data.identities);registry.append(body);target.append(registry);}
}
function renderNeural(target,data){
 target.replaceChildren();const summary=el('div',undefined,'neural-summary');
 const readiness=el('div',undefined,'readiness');readiness.append(el('h3','Model readiness'),el('p',data.ready===true?`Ready · ${fmt(data.count)} completed labels.`:data.ready===false?`Not ready · ${fmt(data.count)} of ${fmt(data.min_needed)} labels required.`:'Readiness unavailable.'));
 if(Number.isFinite(data.progress)){const progress=el('progress');progress.max=1;progress.value=Math.max(0,Math.min(1,data.progress));progress.setAttribute('aria-label','Completed label readiness');readiness.append(progress);}
 readiness.append(el('small','Readiness does not activate or promote a model.'));summary.append(readiness);
 const health=data.health,report=health?.report,healthBox=el('div',undefined,'pipeline-health');healthBox.append(el('h3','Label-pipeline health'));
 if(health?.available!==true||!report)healthBox.append(el('p',health?.reason||'Pipeline health unavailable.','warning'));
 else{
  const checks=el('dl',undefined,'health-checks');
  const add=(label,value,cls)=>{const row=el('div');row.append(el('dt',label),el('dd',value,cls));checks.append(row);};
  add('Status',report.status??'Unavailable');
  const counts=report.label_counts;add('Labels',counts?`${fmt(counts.total)} total · ${fmt(counts.complete)} complete · ${fmt(counts.pending)} pending`:'Unavailable');
  const consistent=report.map_consistency?.consistent;add('Map consistency',consistent===true?'Consistent':consistent===false?'Inconsistent':'Unavailable',consistent===true?'positive':consistent===false?'negative':'warning');
  const dims=report.feature_dims;add('Feature dimensions',dims&&Number.isFinite(dims.checked)&&Number.isFinite(dims.malformed_count)?`${dims.checked} checked · ${dims.malformed_count} malformed`:'Unavailable',dims?.malformed_count>0?'negative':dims?.checked>0&&dims?.malformed_count===0?'positive':'warning');
  if(report.timestamp)add('Observed',report.timestamp);
  healthBox.append(checks);
 }
 summary.append(healthBox);target.append(summary,details(data,'Inspect neural readiness & full health report'));
}
function renderEndpoint(target,path,data){if(path==='identity')renderIdentity(target,data);else if(path==='neural')renderNeural(target,data);else renderData(target,data);}
function renderQuant(data){
 $('quant-time').textContent=data.observed_at?'Observed '+data.observed_at:'Observation time unavailable';
 const risk=data.risk;
 if(risk?.available===true){
  const summary={'Open / protected positions':`${fmt(risk.open_positions)} / ${fmt(risk.protected_positions)}`,'Known current-stop risk':`${fmt(risk.known_stop_risk_money??risk.current_stop_risk_money)} ${risk.currency??''}`,'Account stop risk':risk.risk_complete===true&&Number.isFinite(risk.current_stop_risk_pct)?`${risk.current_stop_risk_pct.toFixed(4)}%`:'Incomplete / unavailable','Risk completeness':risk.risk_complete===true?'Complete for reported positions':'Incomplete · some positions could not be priced'};
  renderData($('risk-summary'),summary);
  $('risk-summary').append(el('p','Mark-to-stop estimate only. Before fees, gaps, slippage and stop execution uncertainty.','panel-copy'));
  if(risk.unprotected_tickets?.length)$('risk-summary').append(el('p','Unprotected tickets: '+risk.unprotected_tickets.join(', '),'panel-copy warning'));
 }else empty($('risk-summary'),risk?.reason||data.reason||'Broker risk diagnostics unavailable.');
 const {p,body}=section('Historical market diagnostics');
 if(Array.isArray(data.market)&&data.market.length)renderData(body,data.market);else empty(body,data.reason||'Historical market observations unavailable.');
 if(data.correlation)body.append(details(data.correlation,'Observed-interval correlation'));
 if(data.methodology)body.append(details(data.methodology,'Methodology & limitations'));
 $('quant-content').replaceChildren(p);
}
function flag(v){return v===true?'Active':v===false?'Clear':'Unknown';}
function renderState(s){
 state=s;lastObservation=Number.isFinite(Date.parse(s.observed_at))?Date.parse(s.observed_at):Date.now();auth(true);const a=s.account||{},scope=a.login===null||a.login===undefined?'unavailable':String(a.login)+'@'+String(a.server||'unknown');
 if(accountScope!==scope){accountScope=scope;client.clear(scope);cache.clear();viewTimes.clear();candles=[];plots={};chartContext='';resetChartViewport();drawCharts();lastChart=0;document.querySelectorAll('[data-feature-host]').forEach(n=>n.replaceChildren());$('trace').hidden=true;}
 updateTelemetry();
 const accountKnown=s.mt5?.account_available===true,positionsKnown=s.mt5?.positions_available===true;
 const mode=a.trade_mode===0?'DEMO':a.trade_mode===2?'LIVE':a.trade_mode===1?'CONTEST':'MODE UNKNOWN';
 $('account-id').textContent=accountKnown?'MT5 '+scalar(a.login):'Broker account unavailable';$('account-mode').textContent=mode+(a.server?' · '+a.server:'');
 document.querySelectorAll('.currency').forEach(n=>n.textContent=a.currency||'currency unknown');
 for(const [id,key]of [['balance','balance'],['equity','equity'],['unrealized','profit']])$(id).textContent=accountKnown?fmt(a[key]):'Unavailable';
 const dp=s.day_pl;$('day-pl-kpi').textContent=dp&&Number.isFinite(dp.total)?fmt(dp.total):'Unavailable';$('day-pl-kpi').className=dp&&Number.isFinite(dp.total)?dp.total<0?'negative':dp.total>0?'positive':'neutral':'muted';
 $('day-pl-detail').textContent=dp?`Realized since ${dp.since||'session start'} · ${a.currency||'currency unknown'} · signals ${fmt(dp.signals)} / algo ${fmt(dp.algo)}`:'Realized P/L unavailable; no zero is assumed.';
 $('day-pl').textContent=dp?'Realized today '+fmt(dp.total)+' '+(a.currency||'unknown currency'):'Realized P/L unavailable';
 const positions=positionsKnown&&Array.isArray(s.positions)?s.positions:[];$('position-count').textContent=positionsKnown?String(positions.length):'Unavailable';$('position-count-badge').textContent=positionsKnown?positions.length+' open':'Unknown';
 $('safety').replaceChildren();for(const key of ['maintenance','halt','pause','stop'])$('safety').append(el('span',key+': '+flag(s[key]),'badge '+(s[key]===true?'warn':s[key]===false?'ok':'warn')));
 const unprotected=positions.filter(p=>!Number.isFinite(Number(p.sl))||Number(p.sl)<=0);
 $('risk-status').textContent=!positionsKnown?'Protection unknown: broker positions unavailable.':unprotected.length?unprotected.length+' position(s) have no broker stop reported. Inspect immediately.':positions.length?'Broker stops reported for every open position. Stop fills are not guaranteed.':'No open positions reported by MT5.';
 $('risk-status').className='source-note '+(!positionsKnown||unprotected.length?'warn':'');
 if(!positionsKnown)empty($('positions'),'Position data unavailable. Check System health and broker terminal.');else if(!positions.length)empty($('positions'),'No open positions reported for this account.');else{
 const rows=positions.map(p=>{const b=el('button',scalar(p.ticket));b.addEventListener('click',()=>loadTrace(p.ticket));b.setAttribute('aria-label','Inspect ticket '+p.ticket);return[b,`${scalar(p.symbol)} · ${scalar(p.side)}`,p.lots,p.entry,p.now,p.pl,p.sl>0?p.sl:'No stop',p.tp>0?p.tp:'None'];});const table=makeTable(['Ticket','Symbol / side','Lots','Entry','Current','P/L '+(a.currency||'?'),'Broker stop','TP'],rows);table.classList.add('position-table');const cards=el('div',undefined,'position-cards');for(const p of positions){const card=el('article',undefined,'position-summary'),b=el('button',p.symbol+' · '+p.side+' · '+p.lots+' lots');b.setAttribute('aria-label','Inspect position '+p.ticket);b.addEventListener('click',()=>loadTrace(p.ticket));card.append(b,el('strong',fmt(p.pl)+' '+(a.currency||'unknown currency')),el('p','Broker stop: '+(p.sl>0?p.sl:'Not reported')+' · Ticket '+p.ticket));cards.append(card);}$('positions').replaceChildren(table,cards);}
 updateFreshness();
}

function eventTicket(e){const p=e.payload||{};return p.ticket??p.position_ticket??p.mt5_ticket;}
function renderEvents(data){const rows=Array.isArray(data)?data:[];if(!rows.length){empty($('activity'),'No recorded events in this window. New activity will appear here.');return;}$('activity').replaceChildren();rows.slice(0,30).forEach(e=>{const row=el('article',undefined,'event-row');row.append(el('small',`${scalar(e.ts)} · ${scalar(e.source)}`),el('strong',String(e.type||'Recorded event').replaceAll('_',' ')));if(e.trace_id)row.append(el('p','Trace '+e.trace_id));const ticket=eventTicket(e);if(ticket!==undefined&&/^\d+$/.test(String(ticket))){const b=el('button','Ticket '+ticket);b.addEventListener('click',()=>loadTrace(ticket));row.append(b);}row.append(details(e.payload||{},'Event payload'));$('activity').append(row);});}

function renderSignalsTable(targetId,data){
 const target=$(targetId),all=Array.isArray(data)?data:[];
 const rows=targetId==='signals-table'?all.filter(s=>!['executed','filled','closed','completed'].includes(String(s.status).toLowerCase())).slice(0,8):all.slice(0,50);
 if(targetId==='signals-table')$('signals-summary').textContent='Recorded inbox · '+rows.length+' shown · source classification, not new trade instructions';
 if(!rows.length){empty(target,'No recorded signals in this window. No synthetic activity is generated.');return;}
 target.replaceChildren(makeTable(['Observed','Source / setup','Symbol','Status','Evidence'],rows.map(s=>{const b=el('button','Inspect');b.addEventListener('click',()=>openEvidence('Signal evidence',s));return[s.time,s.source||s.setup||'Unknown source',s.symbol,s.status||'Unclassified',b];})));
}
function renderHealthTable(h){
 lastHealth=h;$('exceptions').replaceChildren();const notes=[...(h.processes||[]).filter(p=>p.up!==true).map(p=>p.name+': '+(p.up===false?'not running':'unverified')), ...Object.entries(h.ports||{}).filter(([,up])=>up!==true).map(([name])=>name+': unreachable'),...(h.missing||[]).map(x=>'Missing process: '+x),...(h.unknown||[]).map(x=>'Unverified process: '+x),...(h.errors||[]).map(String),...[...moduleErrors].map(([k,v])=>k+': '+v)];
 if(!notes.length)empty($('exceptions'),'No exceptions reported by this observation. This is not an execution-safety guarantee.');else for(const text of notes.slice(0,20))$('exceptions').append(el('p',text,'notice'));
}

async function loadTrace(ticket){if(!/^\d+$/.test(String(ticket)))return;focusReturn=document.activeElement;traceTicket=String(ticket);$('trace').hidden=false;$('trace-close').focus();$('trace-title').textContent='Ticket '+ticket+' · exact trace';empty($('trace-body'),'Loading recorded lifecycle…');try{const result=await api('trace/'+encodeURIComponent(ticket));if(traceTicket===String(ticket))renderData($('trace-body'),result,'No recorded trace for this exact ticket.');}catch(e){if(traceTicket===String(ticket))empty($('trace-body'),e.message);}}
async function refreshCore(){
 if(coreBusy||!connected||document.hidden)return;coreBusy=true;$('refresh').disabled=true;
 try{
  try{renderState(await api('state'));moduleErrors.delete('Account');}catch(e){if(!connected)return;moduleErrors.set('Account',e.message);}
  const scope=accountScope;
  const jobs=[['Activity','events?limit=30&exclude=pnl_update',renderEvents],['Signals','inbox',data=>{renderSignalsTable('signals-table',data);renderSignalsTable('inbox-table',data);}],['Risk','quant',renderQuant],['Health','health',renderHealthTable]];
  const results=await Promise.allSettled(jobs.map(([,path])=>api(path)));
  if(!connected||scope!==accountScope)return;
  results.forEach((r,i)=>{const [name,,render]=jobs[i];if(r.status==='fulfilled'){moduleErrors.delete(name);render(r.value);}else{moduleErrors.set(name,r.reason.message);if(name==='Activity')empty($('activity'),'Unavailable: '+r.reason.message);if(name==='Signals'){empty($('signals-table'),'Signal feed unavailable. '+r.reason.message);empty($('inbox-table'),'Signal feed unavailable. '+r.reason.message);}if(name==='Risk')empty($('risk-summary'),'Risk unavailable. '+r.reason.message);}});
  renderHealthTable(lastHealth||{});notice(moduleErrors.size?[...moduleErrors].map(([k,v])=>k+': '+v).join(' · ')+' · Previously received values may be stale.':'');
  if(active==='overview'&&Date.now()-lastChart>60000)await loadChart();
  if(active!=='overview'&&connected)await loadView(active,false);
  updateFreshness();
 }finally{coreBusy=false;$('refresh').disabled=false;clearTimeout(timer);if(connected&&!document.hidden)timer=setTimeout(refreshCore,15000);}
}

const endpoints={signals:[['Decision journal','journal'],['Source channels','channels']],strategies:[['Strategy engines','strategies'],['Strategy identity & attribution','identity'],['Registered Pine · paper state','pine'],['Neural readiness','neural'],['Latency measurements','latency'],['Strategy lineage','lineage']],intelligence:[['LuxAlgo ecosystem · MCP','luxalgo'],['Market source','market_intel'],['Whale options · feed provenance','whale'],['Edge statistics','edge'],['Trade journal','journal'],['Prop-firm research simulation','prop_sim'],['News risk window','news']],system:[['Process & guard health','health']]};
async function loadView(view,force){
 if(viewBusy||!connected)return;if(view==='overview'){if(!candles.length)await loadChart();else drawCharts();return;}if(view==='chart'){if(Date.now()-lastChart>60000||!candles.length)await loadChart();else drawCharts();if(connected)await loadPineRegistry();return;}
 if(!force&&Date.now()-(viewTimes.get(view)||0)<60000)return;viewBusy=true;
 const host=$(view+'-content');const config=endpoints[view];if(!config){viewBusy=false;return;}
 if(!host.childElementCount)empty(host,'Loading this workspace…');
 try{
  const results=await Promise.allSettled(config.map(([,path])=>api(path==='market_intel'?path+'?kind='+encodeURIComponent($('market-kind').value)+'&limit=20':path)));
  if(!connected)return;host.replaceChildren();let complete=true;
  results.forEach((result,i)=>{
   const {p,body}=section(config[i][0]);host.append(p);
   if(result.status==='fulfilled'){cache.set(config[i][1],result.value);renderEndpoint(body,config[i][1],result.value);if(config[i][1]==='pine')populatePine(result.value);}
   else{complete=false;empty(body,result.reason.message);if(cache.has(config[i][1])){body.append(el('p','Stale · last successful response below.','panel-copy'));const old=el('div');renderData(old,cache.get(config[i][1]));body.append(old);}}});
  // System view: also populate the health table
  if(view==='system'&&results[0].status==='fulfilled')renderHealthTable(results[0].value);
  if(complete)viewTimes.set(view,Date.now());updateFreshness();
 }finally{viewBusy=false;}}
async function switchView(view){if(!titles[view])view='overview';active=view;document.querySelectorAll('[data-view]').forEach(b=>{if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!=='view-'+view);$('view-title').textContent=titles[view][0];$('view-description').textContent=titles[view][1];if(connected)await loadView(view,false);window.scrollTo(0,0);}
function populatePine(data){if(!Array.isArray(data))return;const selected=$('pine-select').value;$('pine-select').replaceChildren(el('option','No overlay'));$('pine-select').firstChild.value='';data.forEach(p=>{const option=el('option',`${p.name||p.path} · ${p.paper?'paper':'registered'}`);option.value=p.path||p.name;$('pine-select').append(option);});if([...$('pine-select').options].some(o=>o.value===selected))$('pine-select').value=selected;}
function chartParams(){return {symbol:$('symbol').value.trim(),timeframe:$('timeframe').value,count:220};}
async function loadChart(){
 if(chartBusy||!connected)return false;chartBusy=true;updateChartControls();
 const params=chartParams(),key=params.symbol+' · '+params.timeframe,scope=accountScope,generation=client.generation;
 for(const id of ['chart-message','overview-chart-message'])$(id).textContent='Loading real broker candles…';
 try{
  const data=await api('candles?'+new URLSearchParams(params));
  if(!connected||scope!==accountScope||generation!==client.generation)return false;
  const supplied=Array.isArray(data)?data:(data?.candles||data?.bars||[]),next=normaliseCandles(supplied);
  const changed=JSON.stringify(next)!==JSON.stringify(candles)||chartContext!==key;
  if(chartContext!==key){plots={};resetChartViewport();}candles=next;chartContext=key;lastChart=Date.now();updateTelemetry();
  $('chart-title').textContent=key;$('overview-chart-title').textContent=key;
  const ms=candles.length?candles.at(-1)[0]:null,ignored=Array.isArray(supplied)?supplied.length-candles.length:0;
  const age=ms===null?'':' · Last bar '+new Date(ms).toISOString()+(Date.now()-ms>21600000?' · Older than 6h; session status unknown':'');
  const message=candles.length?`${candles.length} real MT5 bars · Last close ${price(candles.at(-1)[4])}${age} · Broker timestamps as supplied.${ignored?' '+ignored+' invalid or duplicate rows ignored.':''}`:'No broker bars returned. Check symbol and terminal. No simulated prices are shown.';
  for(const id of ['chart-message','overview-chart-message'])$(id).textContent=message;
  const old=ms!==null&&Date.now()-ms>21600000;$('quote-status').textContent=old?'Old bars · verify session':candles.length?'Broker bars · not a live quote':'Market unavailable';$('quote-status').className='hq-badge '+(old||!candles.length?'warn':'');$('overview-chart-message').className='source-note '+(old?'warn':'');
  if(changed||!$(active==='chart'?'chart':'overview-chart').width)drawCharts();
  if(active==='chart')await loadPineRegistry();return candles.length>0;
 }catch(e){if(!connected||scope!==accountScope||generation!==client.generation)return false;candles=[];plots={};resetChartViewport();updateTelemetry();$('quote-status').textContent='Market unavailable';$('quote-status').className='hq-badge warn';drawCharts();for(const id of ['chart-message','overview-chart-message'])$(id).textContent='Unavailable: '+e.message;return false;}
 finally{chartBusy=false;updateChartControls();}
}
function drawCharts(){
 if(!velas){void initVelaz();}
 if(velas&&velas.overview)velas.overview.setBars(candles);
 if(velas&&velas.chart)velas.chart.setBars(candles);
 updateChartControls();
}
async function initVelaz(){
 if(velas)return velas;
 velas={};
 if(typeof STURN!=='undefined'&&STURN.VelaChart){
  try{
   velas.overview=new STURN.VelaChart('overview-chart',{symbol:'XAUUSD',timeframe:'H1',theme:'dark',pollInterval:8000});
   velas.chart=new STURN.VelaChart('chart',{symbol:'XAUUSD',timeframe:'H1',theme:'dark',pollInterval:5000});
   await Promise.all([velas.overview.init(),velas.chart.init()]);
  }catch(e){console.error('VelaChart init failed',e);velas={};}
 }else{
  console.warn('STURN.VelaChart unavailable; charts use SVG fallback');
 }
 return velas;
}

function drawChart(target='chart'){
 if(!velas){void initVelaz();}
 if(velas&&velas[target])velas[target].setBars(candles);
 updateChartControls();
}
function runPine(){
 $('compile-message').textContent='Unavailable: a credential-free OS-isolated worker must be configured first. Source editing and export remain available; no simulation has run.';
}

$('connect-form').addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{await api('session',{method:'POST',body:JSON.stringify({token:$('token').value})});$('token').value='';auth(true);await refreshCore();}catch(error){$('connect-message').textContent=error.message;}finally{button.disabled=false;}});
$('logout').addEventListener('click',async()=>{try{await api('session',{method:'DELETE'});const response=await fetch('/api/state',{credentials:'same-origin'});if(response.status!==401)throw new Error('Session removal could not be verified. Retry Disconnect.');auth(false);cache.clear();viewTimes.clear();}catch(e){notice(e.message);}});
$('refresh').addEventListener('click',async()=>{viewTimes.delete(active);await refreshCore();});
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{location.hash=b.dataset.view;switchView(b.dataset.view);}));
window.addEventListener('hashchange',()=>{const v=location.hash.slice(1);if(v!==active)switchView(v);});
$('trace-close').addEventListener('click',closeEvidence);
$('chart-form').addEventListener('submit',e=>{e.preventDefault();loadChart();});
// Single interaction owners: chart navigation never fetches or executes a strategy.
for(const action of ['older','newer','zoom-in','zoom-out','reset'])$('chart-'+action).addEventListener('click',()=>changeChartWindow(action));
$('chart-export').addEventListener('click',exportChartCandles);$('chart').addEventListener('click',selectChartCandle);$('chart').addEventListener('keydown',stepChartCandle);
$('pine-select').addEventListener('change',()=>{
 $('compile-message').textContent=$('pine-select').value?'Metadata only: this registry entry does not include source code. Import a .pine file to edit it locally.':'No registered strategy selected. Import or edit source locally.';
});
for(const id of ['load-overlay','compile','run-pine'])$(id).addEventListener('click',runPine);
$('market-load').addEventListener('click',()=>loadView('intelligence',true));
$('pine-file').addEventListener('change',async e=>{
 const file=e.target.files[0];if(!file)return;
 try{
  if(file.size>250000){$('compile-message').textContent='Source exceeds 250 KB. Choose a smaller script.';return;}
  if(!/\.(pine|txt)$/i.test(file.name)){$('compile-message').textContent='Choose a .pine or .txt source file.';return;}
  // Preserve source exactly: rewriting whitespace can change Pine semantics and strings.
  $('pine-editor').value=await file.text();
  $('compile-message').textContent='Imported '+file.name+'. Editing only; simulation is unavailable.';
 }catch(error){$('compile-message').textContent='Source import failed: '+error.message;}
 finally{e.target.value='';}
});
const chartObserver=new ResizeObserver(drawCharts);if(velas){chartObserver.observe($('chart'));chartObserver.observe($('overview-chart'));}else{chartObserver.observe(document.body);}
document.addEventListener('visibilitychange',()=>{document.body.classList.toggle('page-hidden',document.hidden);if(document.hidden){clearTimeout(timer);clearTimeout(clockTimer);}else{tickClock();if(connected)refreshCore();}});
$('nav-toggle').addEventListener('click',()=>{const collapsed=$('nav-items').classList.toggle('nav-collapsed');$('nav-toggle').setAttribute('aria-expanded',String(!collapsed));});
const navMedia=matchMedia('(max-width:720px)');const adaptNav=()=>{$('nav-items').classList.toggle('nav-collapsed',navMedia.matches);$('nav-toggle').setAttribute('aria-expanded',String(!navMedia.matches));};adaptNav();navMedia.addEventListener('change',adaptNav);
document.addEventListener('keydown',e=>{if($('trace').hidden)return;if(e.key==='Escape'){e.preventDefault();closeEvidence();}if(e.key==='Tab'){const items=[...$('trace').querySelectorAll('button,a,input,summary,[tabindex="0"]')].filter(n=>n.getClientRects().length);const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}});
window.addEventListener('pagehide',()=>{clearTimeout(timer);chartObserver.disconnect();client.clear();});
window.addEventListener('pageshow',e=>{if(e.persisted){chartObserver.observe($('chart'));chartObserver.observe($('overview-chart'));refreshCore();}});
switchView(titles[location.hash.slice(1)]?location.hash.slice(1):'overview');
async function boot(){const nonce=window.__hqBootstrap;if(nonce){try{await api('bootstrap',{method:'POST',body:JSON.stringify({nonce})});}catch(e){/* single-use nonce gone or expired: fall back to the token form */}try{delete window.__hqBootstrap;}catch(e){window.__hqBootstrap=null;}}connected=true;await refreshCore();}
boot();
})();

