/* Matrix research panels: read-only, no financial payloads in storage. */
(() => {
  'use strict';
  const host = document.getElementById('matrix-panel-grid');
  if (!host) return;
  const key = 'hq.matrix.panels.v1', panels = new Map();
  let prefs = {};
  try { prefs = JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch (_) {}
  const save = () => { try { localStorage.setItem(key, JSON.stringify(prefs)); } catch (_) {} };
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = String(text); if (cls) n.className = cls; return n; };
  const api = window.HQMatrix = window.HQMatrix || {};
  // Keep an existing injection API and all legacy Matrix helpers intact.
  const upstream = typeof api.registerPanel === 'function' ? api.registerPanel.bind(api) : null;
  const order = () => [...panels.values()].sort((a,b) => a.pref.position-b.pref.position).forEach(p => host.append(p.card));
  function registerPanel(spec) {
    if (panels.has(spec.id)) return panels.get(spec.id);
    const stored = prefs[spec.id] || {};
    const pref = prefs[spec.id] = { visible: typeof stored.visible === 'boolean' ? stored.visible : !window.matchMedia('(max-width:650px)').matches, position: Number.isFinite(stored.position) ? stored.position : panels.size, config: {} };
    for (const [k, values] of Object.entries(spec.config || {}).filter(([, values]) => Array.isArray(values))) pref.config[k] = values.includes(stored.config?.[k]) ? stored.config[k] : values[0];
    const card = node('article', undefined, 'matrix-data-panel'); card.id = 'matrix-panel-' + spec.id;
    const heading = node('div', undefined, 'matrix-panel-heading'), title = node('h3', spec.title);
    heading.append(title);
    const status = node('span', 'Awaiting observation', 'matrix-panel-status'); status.setAttribute('role', 'status');
    const body = node('div', undefined, 'matrix-panel-body');
    const footer = node('p', '/api/' + spec.endpoint, 'matrix-panel-source');
    const controls = node('div', undefined, 'matrix-panel-controls');
    const p = {spec, pref, card, body, status, footer, busy:false, controller:null};
    const button = (text, label, action) => { const b = node('button', text); b.type='button'; b.setAttribute('aria-label', label+' '+spec.title); b.onclick=action; return b; };
    controls.append(button('↻', 'Refresh', () => refresh(p)), button('↑', 'Move up', () => move(p,-1)), button('↓', 'Move down', () => move(p,1)));
    const toggle = button('Collapse', 'Toggle', () => { pref.visible=!pref.visible; show(); save(); });
    function show() { body.hidden=!pref.visible; toggle.textContent=pref.visible?'Collapse':'Expand'; toggle.setAttribute('aria-expanded', String(pref.visible)); }
    controls.append(toggle); heading.append(controls); card.append(heading,status);
    for (const [k,values] of Object.entries(spec.config || {}).filter(([, values]) => Array.isArray(values))) {
      const label=node('label',k+' '), select=node('select');
      select.setAttribute('aria-label',spec.title+' '+k);
      values.forEach(value => { const o=node('option', value); o.value=value; select.append(o); }); select.value=pref.config[k];
      select.onchange=()=>{pref.config[k]=select.value;save();refresh(p);}; label.append(select);body.append(label);
    }
    p.content=node('div'); body.append(p.content); card.append(body,footer); panels.set(spec.id,p); show(); order();
    if (upstream) { try { upstream({...spec, element:card, render:()=>card, refresh:()=>refresh(p)}); } catch (_) { /* Local host remains usable if upstream uses another contract. */ } }
    return p;
  }
  if (!upstream) api.registerPanel = registerPanel;
  function move(p,delta) { const list=[...panels.values()].sort((a,b)=>a.pref.position-b.pref.position), i=list.indexOf(p), j=i+delta; if(j<0||j>=list.length)return; [list[i],list[j]]=[list[j],list[i]];list.forEach((x,k)=>x.pref.position=k);order();save(); }
  const statusBadge = (status) => {
    const s = String(status || '').replace(/\s/g, '').toLowerCase();
    const c = statusColors[s] || 'neutral';
    return '<span class="order-status status-' + s + '" style="color:var(--' + c + ');border:1px solid currentColor">' + (status || '—') + '</span>';
  };

  const renderOrders = (data) => {
    if (!Array.isArray(data)) return '<p style="color:var(--fg-muted)">No orders</p>';
    return '<table class="orders"><thead><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Status</th><th>Price</th><th>Filled</th><th>Avg</th><th>Account</th></tr></thead><tbody>' +
      data.map(o => '<tr><td class="data-mono">' + o.symbol + '</td><td>' + (o.side || '—') + '</td><td class="data-mono">' + (o.quantity ?? o.notional ?? '—') + '</td><td>' + statusBadge(o.status) + '</td><td class="data-mono">' + (o.limitPrice ?? o.stopPrice ?? '—') + '</td><td class="data-mono">' + (o.filledQuantity || 0) + '</td><td class="data-mono">' + (o.filledAvgPrice ?? '—') + '</td><td class="data-mono">' + (o.clientOrderId ?? o.id?.slice(-8)) + '</td></tr>').join('') +
      '</tbody></table>';
  };

  const renderAccounts = (data) => {
    if (!Array.isArray(data)) return '<p style="color:var(--fg-muted)">No accounts</p>';
    return '<table class="accounts"><thead><tr><th>Account</th><th>Broker</th><th>Environment</th><th>Mode</th><th>Equity</th><th>Positions</th></tr></thead><tbody>' +
      data.map(a => '<tr><td class="data-mono">' + a.id + '</td><td class="data-mono">' + (a.broker || '—') + '</td><td class="data-mono">' + (a.environment || '—') + '</td><td class="data-mono">' + (a.mode || '—') + '</td><td class="data-mono" style="color:var(--ok)">$' + Number(a.equity || 0).toFixed(2) + '</td><td class="data-mono">' + (a.positions?.length ?? 0) + '</td></tr>').join('') +
      '</tbody></table>';
  };

  function render(value, depth=0) {
    if (value === null || value === undefined) return node('span','Unobserved');
    if (typeof value !== 'object') return node('span', typeof value==='boolean' ? (value?'Yes':'No') : String(value).slice(0,1200));
    if (depth>3) return node('span',JSON.stringify(value).slice(0,1200));
    if (Array.isArray(value)) {
      if (value.length && value[0].symbol && value[0].side) {
        const d = node('div'); d.innerHTML = renderOrders(value); return d;
      }
      if (value.length && value[0].equity !== undefined) {
        const d = node('div'); d.innerHTML = renderAccounts(value); return d;
      }
      const list=node('ol'); value.slice(-12).forEach(v=>{ const li=node('li');li.append(render(v,depth+1));list.append(li); });if(!value.length)list.append(node('li','No recorded observations'));return list;
    }
    const dl=node('dl');Object.entries(value).slice(0,28).forEach(([k,v])=>{dl.append(node('dt',k.replace(/_/g,' '))); const dd=node('dd'); if (/url$/i.test(k) && typeof v==='string') { try { const url=new URL(v);if(['https:','http:'].includes(url.protocol)){const a=node('a',v);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';dd.append(a);}else dd.append(render(v,depth+1)); } catch (_) {dd.append(render(v,depth+1));} } else dd.append(render(v,depth+1)); dl.append(dd);});if(!Object.keys(value).length)dl.append(node('dd','No recorded observations'));return dl;
  }

  function renderDeck(id,data) {
    const box=node('div'), text=v=>v==null?'Unobserved':String(v);
    if(id==='golden-eye') {
      box.append(node('p',data.reason || 'Recorded observations; timestamps identify freshness.'));
      const table=node('table'), head=node('tr');
      ['Symbol / TF','Regime','Strength','Consensus','Latest signal','Observed'].forEach(s=>head.append(node('th',s)));table.append(head);
      (data.rows||[]).forEach(r=>{const tr=node('tr');
        [r.symbol+' / '+r.timeframe,text(r.regime),text(r.strength),text(r.consensus),
         r.latest_signal ? text(r.latest_signal.action)+' · '+text(r.latest_signal.ts) : 'No signal',
         r.observed_at ? r.observed_at+' · '+(r.stale?'STALE':'RECENT') : 'Not observed'].forEach(v=>tr.append(node('td',v)));table.append(tr);});
      box.append(table,node('small',data.notice||''));
    } else {
      const dl=node('dl');
      [['Neural readiness',data.ready?'READY FOR TRAINING':'NOT READY'],
        ['Verified labels',text(data.label_count)+' / '+text(data.min_labels)],
        ['Holdout AUC',data.holdout_auc==null?'Unavailable (no validated holdout)':text(data.holdout_auc)],
        ['Setup confidence',data.setup_confidence?text(data.setup_confidence.value)+' · '+text(data.setup_confidence.symbol)+' · '+text(data.setup_confidence.observed_at):'Unavailable (stub predictions excluded)']]
        .forEach(([k,v])=>dl.append(node('dt',k),node('dd',v)));
      box.append(dl,node('small',data.notice||''));
      if(data.diagnostic_evaluation) {const d=node('details');d.append(node('summary','Diagnostic evaluation (not holdout)'),render(data.diagnostic_evaluation));box.append(d);}
    }
    return box;
  }
  async function refresh(p) {
    if (p.busy || document.hidden) return;
    p.busy=true; p.controller=new AbortController(); const timer=setTimeout(()=>p.controller.abort(),12000);
    let query;
    // Ticker rotation for pine-live panel
    if (p.spec.id === 'pine-live' && p.spec.config.rotate) {
      const symbols = p.spec.config.symbol;
      if (!p._tickerIndex) p._tickerIndex = 0;
      p._tickerIndex = (p._tickerIndex + 1) % symbols.length;
      const currentSymbol = symbols[p._tickerIndex];
      query=new URLSearchParams({...p.spec.params, symbol: currentSymbol, ...p.pref.config});
    } else {
      query=new URLSearchParams({...p.spec.params,...p.pref.config});
    }
    const path = p.spec.baseUrl
      ? p.spec.baseUrl + '/api/' + p.spec.endpoint + (query.size ? '?' + query : '')
      : '/api/'+p.spec.endpoint + (query.size ? '?' + query : '');
    try {
      const response = await fetch(path, {credentials: p.spec.baseUrl ? 'include' : 'same-origin', cache: 'no-store', signal: p.controller.signal});
      const data=await response.json(); if(!response.ok)throw new Error(data.error || 'HTTP '+response.status);
      p.content.replaceChildren(['golden-eye','ai-brain'].includes(p.spec.id)?renderDeck(p.spec.id,data):render(data));
      // Display daily P/L with red/green coloring for pine-live panel
      if (p.spec.id === 'pine-live' && p.spec.config.dailyPnL && data && data.length) {
        const dailyPnL = data.reduce((sum, candle) => sum + (candle.close - candle.open), 0);
        const pnlColor = dailyPnL >= 0 ? '#75e4a7' : '#ee9891';
        const pnlText = dailyPnL >= 0 ? '+' : '';
        const pnlElement = node('div', undefined, `Daily P/L: ${pnlText}${dailyPnL.toFixed(2)}`);
        pnlElement.style.color = pnlColor;
        pnlElement.style.marginTop = '8px';
        pnlElement.style.fontWeight = 'bold';
        p.content.appendChild(pnlElement);
      }
      p.card.dataset.condition=data.available===false||data.error?'unavailable':'observed';
      p.status.textContent=data.available===false||data.error?'Unavailable · '+(data.reason||data.error||'not provided'):'Observed · '+new Date().toLocaleTimeString();
      p.footer.textContent = (p.spec.baseUrl || '/api') + '/' + p.spec.endpoint + ' · received ' + new Date().toISOString() + ' · source timestamps above';
    } catch(error) { p.card.dataset.condition='unavailable';p.status.textContent='Unavailable · '+(error.name==='AbortError'?'request timed out':error.message);p.content.replaceChildren(node('p','No current observation. Retrying automatically; no simulated values.')); }
    finally {clearTimeout(timer);p.busy=false;p.controller=null;}
  }
  const specs=[
    {id:'golden-eye',title:'GOLDEN EDGE',endpoint:'golden-eye'},
    {id:'ai-brain',title:'AI BRAIN',endpoint:'ai-brain'},
    {id:'luxalgo',title:'LuxAlgo Regime',endpoint:'luxalgo'},
    {id:'edge',title:'Edge Stats',endpoint:'edge'},
    {id:'prop-sim',title:'Prop Firm Sim',endpoint:'prop_sim',config:{paths:['2000','5000','10000']}},
    {id:'market-intel',title:'Market Intel',endpoint:'market_intel',params:{limit:'8'},config:{kind:['congress','insider','contracts','lobbying','short_volume']}},
    {id:'neural-health',title:'Neural Health',endpoint:'neural.health'},
    {id:'pine-live',title:'PineTS Live',endpoint:'pine_series',params:{count:'100',strategy:'strategies/rsi_ema_trend.pine'},config:{symbol:['XAUUSD','EURUSD','GBPUSD','USDJPY'],timeframe:['H1','M15','H4','D1'],rotate:true,dailyPnL:true}}
  ];
  specs.forEach(spec => { if(upstream)registerPanel(spec);else window.HQMatrix.registerPanel(spec); });
  specs.push({id:'orders-live',title:'Orders',endpoint:'trade-relay/orders',config:{status:['open','partially_filled','filled','canceled','rejected','expired','pending']}});
  specs.push({id:'accounts-live',title:'Accounts',endpoint:'trade-relay/accounts'});
  const poll=()=>panels.forEach(refresh); poll();const interval=setInterval(poll,5000);
  // Subscribe to an existing shared event stream, never invent a second SSE
  // connection: the current /api/matrix/stream SSE endpoint is finite snapshot replay.
  window.addEventListener('hq:matrix-event',poll);window.addEventListener('hq:state',poll);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
  window.addEventListener('pagehide',()=>{clearInterval(interval);panels.forEach(p=>p.controller?.abort());},{once:true});
  api.refreshPanels=poll;
})();
