---
slug: agent-reports.verify_website_live
type: note
graph: gitnexus
---

"""Real-browser read-only website verification. No broker actions or credentials printed."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
errors, responses = [], []
with sync_playwright() as p:
    candidates = sorted((Path.home() / 'AppData/Local/ms-playwright').glob('chromium-*/chrome-win64/chrome.exe'), reverse=True)
    browser = p.chromium.launch(executable_path=str(candidates[0]), headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 960})
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('response', lambda r: responses.append({'path': r.url.split('8490')[-1], 'status': r.status}) if '/api/' in r.url else None)
    page.goto('http://127.0.0.1:8490/', wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(6500)
    initial = page.evaluate('''() => ({title:document.title, appHidden:document.querySelector('#app')?.hidden,
      connection:document.querySelector('#connection')?.textContent,
      body:document.body.innerText.slice(0,1800),
      buttons:[...document.querySelectorAll('[data-view]')].map(n=>({view:n.dataset.view,text:n.textContent.trim()}))})''')
    views = []
    for item in initial['buttons']:
        page.locator('[data-view="'+item['view']+'"]').first.click()
        page.wait_for_timeout(2000)
        views.append(page.evaluate('''() => ({hash:location.hash,visible:[...document.querySelectorAll('.view')].filter(n=>!n.hidden).map(n=>({id:n.id,text:n.innerText.slice(0,2600)})),overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth})'''))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(500)
    mobile = page.evaluate('''() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})''')
    states = page.evaluate('''async () => {
      const out={}; for (const path of ['state','health','channels','pine','strategies','events?limit=5']) {
        try {const r=await fetch('/api/'+path,{credentials:'same-origin'}); const d=await r.json();
          out[path]={status:r.status,keys:Object.keys(d),summary:path==='health'?d:undefined};
        } catch(e){out[path]={error:e.message};}
      } return out;
    }''')
    result = {'initial':initial,'views':views,'mobile':mobile,'page_errors':errors,'api_responses':responses,'api_samples':states}
    target = BASE / 'agent-reports/website-live-current.json'
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    context.close()
    browser.close()

