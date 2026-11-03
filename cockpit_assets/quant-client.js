/* One account-scoped HTTP client; no persistent credential or financial cache. */
'use strict';
window.HQClient = class {
  constructor(){this.scope='unobserved';this.pending=new Map();this.generation=0;this.lastRTT=null;}
  clear(scope='unobserved'){
    this.generation++;this.scope=scope;
    for(const x of this.pending.values())x.controller.abort();
    this.pending.clear();
  }
  async request(path,options={}){
    const method=options.method||'GET',key=this.scope+':'+path;
    if(method==='GET'&&this.pending.has(key))return this.pending.get(key).promise;
    const controller=new AbortController(),generation=this.generation;
    const timeout=setTimeout(()=>controller.abort(),20000),started=performance.now();
    const promise=(async()=>{
      try{
        const response=await fetch('/api/'+path,{credentials:'same-origin',cache:'no-store',...options,headers:{'Content-Type':'application/json',...(options.headers||{})},signal:controller.signal});
        const data=await response.json();
        if(!response.ok){const error=new Error(data.error||'Request failed: '+response.status);error.status=response.status;throw error;}
        if(method==='GET'&&generation!==this.generation)throw new Error('Account changed; discarded previous response.');
        this.lastRTT=performance.now()-started;
        return data;
      }catch(e){if(e.name==='AbortError')throw new Error('Request cancelled or timed out. Refresh to retry.');throw e;}
      finally{clearTimeout(timeout);if(this.pending.get(key)?.controller===controller)this.pending.delete(key);}
    })();
    if(method==='GET')this.pending.set(key,{controller,promise});
    return promise;
  }
};
