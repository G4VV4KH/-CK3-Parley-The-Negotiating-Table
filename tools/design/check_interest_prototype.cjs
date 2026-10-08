// Design-only checks. These do not execute CK3 or production Parley scripts.
// Supply the external prototype HTML as an absolute first argument. Playwright
// and Chrome are caller-provided prerequisites only for opt-in --browser checks.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

async function main() {
  const fragment = process.argv[2];
  if (!fragment || !path.isAbsolute(fragment)) throw new Error('Supply the absolute prototype fragment path');
  const html = fs.readFileSync(fragment, 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  new vm.Script(script);
  const context = vm.createContext({});
  vm.runInContext(script.split('// UI binding')[0] + '\nthis.quote=interestQuote;this.fixtures=INTEREST_SCENARIOS;this.transform=interestTransform;', context);
  let checks = 0;
  const near = (actual, expected) => { assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`); checks++; };
  const yes = condition => { assert.ok(condition); checks++; };
  const fixture = (i, w, extra = {}) => ({gain:100,loss:60,interest:i,willingness:w,relation:1,...extra});
  near(context.quote(context.fixtures.war,'standard').score,20);
  near(context.quote(context.fixtures.surplus,'standard').score,-960);
  near(context.quote(context.fixtures.domain,'standard').score,-60);
  for (let i = 0; i <= 100; i++) {
    for (const mode of ['mild','standard','strict']) {
      const q = context.quote(fixture(i/100,(100-i)/100,{relation:1.4}),mode);
      yes(Number.isFinite(q.score));
      yes(q.i>=0 && q.i<=1 && q.w>=0.01 && q.w<=1);
      yes(q.penalty>=-1e-8);
      near(q.before-q.penalty,q.score);
      near(q.gainPenalty+q.lossPenalty,q.penalty);
      if (i===0) near(q.gain,0);
      const off = context.quote(fixture(i/100,(100-i)/100,{relation:1.4}),'off');
      near(off.penalty,0); near(off.score,80);
    }
    const mild=context.quote(fixture(i/100,(100-i)/100),'mild');
    const standard=context.quote(fixture(i/100,(100-i)/100),'standard');
    const strict=context.quote(fixture(i/100,(100-i)/100),'strict');
    yes(mild.score>=standard.score-1e-8 && standard.score>=strict.score-1e-8);
  }
  for (const mode of ['mild','standard','strict']) {
    near(context.quote(fixture(1,1),mode).penalty,0);
    near(context.quote(fixture(0,1,{gain:100,loss:0,relation:1.4}),mode).score,0);
    near(context.quote(fixture(0,0,{gain:0,loss:0}),mode).score,0);
  }
  console.log(JSON.stringify({kind:'DESIGN_ARITHMETIC',status:'PASS',checks,native:'NOT_RUN',coverage:'Smooth presets, bounds, finite zero-willingness handling, exact fixture arithmetic, Off bypass, strictness ordering, no opinion gain at zero incoming interest. No live native inputs, amount-band integration or settlement tested.'}));

  // A narrow DOM stub validates bindings and event arithmetic, not rendering.
  class Element {
    constructor() { this.children=[];this.events={};this.attributes={};this.hidden=false;this.textContent=''; }
    setAttribute(key,value) { this.attributes[key]=value; }
    addEventListener(key,callback) { this.events[key]=callback; }
    appendChild(child) { this.children.push(child); }
    replaceChildren() { this.children=[]; }
  }
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);
  assert.equal(new Set(ids).size,ids.length);
  const elements = Object.fromEntries(ids.map(id=>[id,new Element()]));
  elements['parley-interest-draft'].querySelector = selector => {
    const result=elements[selector.slice(1)];
    assert.ok(result,`Unknown element ${selector}`); return result;
  };
  const doc = {getElementById:id=>elements[id],createElement:()=>new Element()};
  const ui = vm.createContext({document:doc,window:{addEventListener:()=>{}},Intl});
  vm.runInContext(script,ui);
  assert.equal(elements['pi-score'].textContent,'-960');
  elements['pi-mode'].events.change({target:{value:'off'}});
  assert.equal(elements['pi-score'].textContent,'+300');
  assert.equal(elements['pi-in-badge'].hidden,true);
  assert.equal(elements['pi-interest-row'].hidden,true);
  elements['pi-mode'].events.change({target:{value:'strict'}});
  assert.equal(elements['pi-in-badge'].hidden,false);
  assert.ok(Number(elements['pi-score'].textContent.replaceAll('\u00a0','').replace(',','.'))<-960);
  elements['pi-out-badge'].events.click();
  assert.match(elements['pi-detail-title'].textContent,/готовность отдать/);
  assert.match(elements['pi-out-badge'].attributes['data-tooltip'],/не вероятность/);
  elements['pi-interest-button'].events.click();
  assert.equal(elements['pi-detail-lines'].children.length,3);
  elements['pi-detail-toggle'].events.click();
  assert.equal(elements['pi-detail'].hidden,true);
  vm.runInContext("piState.scenario='war';piState.mode='standard';piRender();",ui);
  assert.equal(elements['pi-score'].textContent,'+20');
  vm.runInContext("piState.scenario='domain';piRender();",ui);
  assert.equal(elements['pi-score'].textContent,'-60');
  console.log(JSON.stringify({kind:'DESIGN_DOM_STUB',status:'PASS',coverage:'Unique IDs, resolved bindings, initial result, Off/Strict events, badge/detail events, three scenario results and tooltip strings. No browser layout or real hover rendering.'}));

  if (!process.argv.includes('--browser')) {
    console.log(JSON.stringify({kind:'DESIGN_BROWSER',status:'NOT_VERIFIED',reason:'Browser check is opt-in; the initial attempt was blocked by the system remote-debugging policy. Do not bypass that policy.'}));
    return;
  }
  let chromium;
  try { ({chromium}=require('playwright')); }
  catch { console.log(JSON.stringify({kind:'DESIGN_BROWSER',status:'NOT_VERIFIED',reason:'Caller-installed Playwright unavailable through Node package resolution'})); return; }
  let browser;
  try { browser = await chromium.launch({headless:true,channel:'chrome'}); }
  catch (error) { console.log(JSON.stringify({kind:'DESIGN_BROWSER',status:'NOT_VERIFIED',reason:'Browser prerequisite unavailable or launch blocked: '+String(error)})); return; }
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror',error=>errors.push(String(error)));
    await page.setContent(html);
    await page.locator('#pi-mode').selectOption('off');
    assert.equal(await page.locator('#pi-score').textContent(),'+300');
    assert.equal(await page.locator('#pi-interest-row').isVisible(),false);
    assert.equal(await page.locator('#pi-in-badge').isVisible(),false);
    await page.locator('#pi-mode').selectOption('standard');
    assert.equal(await page.locator('#pi-score').textContent(),'-960');
    assert.equal(await page.locator('#pi-in-badge').isVisible(),true);
    await page.locator('#pi-out-badge').click();
    assert.match(await page.locator('#pi-detail-title').textContent(),/готовность отдать/);
    assert.match(await page.locator('#pi-detail-lines').textContent(),/Расход полезного резерва/);
    assert.match(await page.locator('#pi-out-badge').getAttribute('data-tooltip'),/не вероятность/);
    await page.locator('#pi-interest-button').click();
    assert.match(await page.locator('#pi-detail-lines').textContent(),/Общий штраф/);
    const overflow = [];
    for (const width of [320,640,736]) {
      await page.setViewportSize({width,height:1200});
      const result = await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
      assert.ok(result.scroll<=result.width,JSON.stringify(result));
      overflow.push({width,overflow:false});
    }
    await page.setViewportSize({width:736,height:1200});
    await page.locator('#pi-in-badge').click();
    const screenshot = path.join(path.dirname(fragment),'parley-negotiation-interests-preview.png');
    await page.locator('#parley-interest-draft').screenshot({path:screenshot});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({kind:'DESIGN_BROWSER',status:'PASS',overflow,screenshot,coverage:'Local HTML rendering, rule switch, detail click, tooltip payload and responsive width. Host tooltip rendering and native CK3 layout NOT_VERIFIED.'}));
  } finally { await browser.close(); }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
