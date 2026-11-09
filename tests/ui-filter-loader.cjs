const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag=tag; this.value=''; this.children=[]; this.listeners={}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; }
  setAttribute() {}
  addEventListener(name, handler) { this.listeners[name]=handler; }
}
async function setup(cancel=false) {
  const elements=new Map(); let calls=0, active=0, maxActive=0;
  const element=(selector)=>{ if(!elements.has(selector)) elements.set(selector,new Element('div')); return elements.get(selector); };
  const context=vm.createContext({AbortController,URLSearchParams,location:{pathname:'/',search:''},
    document:{querySelector:element,createElement:(tag)=>new Element(tag),createTextNode:(text)=>({textContent:text})},
    fetch:async(path,options)=>{
      if(path==='/api/sources') return {ok:true,json:async()=>[]};
      assert.equal(path,'/api/details'); calls++; active++; maxActive=Math.max(maxActive,active);
      const ref=JSON.parse(options.body).ref;
      if(cancel) await new Promise((resolve,reject)=> options.signal.addEventListener('abort',()=>reject(new Error('aborted'))));
      else await new Promise(setImmediate);
      active--;
      return {ok:true,json:async()=>({filters:{developer:ref==='a'?'':'Acme',version:'1.2.3',format:['vst3']},dates:{published:'2026-11-09',modified:null}})};
    }});
  vm.runInContext(fs.readFileSync('vstworld/static/filters.js','utf8'),context);
  vm.runInContext(fs.readFileSync('vstworld/static/app.js','utf8'),context);
  await new Promise(setImmediate);
  const items=['a','b','c','d','e','f'].map(ref=>({ref,title:ref,filters:ref==='a'?{developer:'Existing'}:{}}));
  const group=new Element('section'); group.items=items; group.list=new Element('div');
  context.testGroup=group;
  vm.runInContext('state.groups=[testGroup]; state.count=testGroup.items.length; state.generation=1;',context);
  element('#f-developer').value='Acme';
  const running=context.loadFilterFacts();
  await new Promise(setImmediate);
  if(cancel) vm.runInContext('state.detailController.abort()',context);
  await running;
  assert.ok(maxActive<=3,'a leitura não deve disparar todas as fichas simultaneamente');
  assert.equal(vm.runInContext('state.enriching',context),false);
  if(cancel) {
    assert.equal(calls,3,'parar deve impedir novos pedidos na fila');
    assert.ok(items.every(item=>!item.detailsLoaded));
    assert.match(element('#filter-progress').textContent,/0 ficha/);
  } else {
    assert.equal(calls,6);
    assert.ok(items.every(item=>item.detailsLoaded));
    assert.equal(items[0].filters.developer,'Existing','não perder dado da listagem quando ficha omite esse campo');
    assert.equal(group.visibleCount,5);
    await context.loadFilterFacts();
    assert.equal(calls,6,'não reler fichas já confirmadas na mesma consulta');
  }
}
(async()=>{await setup();await setup(true);console.log('OK: leitura de fichas limitada, interrompível e sem perder fatos conhecidos');})().catch(error=>{console.error(error);process.exitCode=1;});
