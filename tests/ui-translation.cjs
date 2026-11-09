const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag=tag; this.value=''; this.children=[]; this.listeners={}; this.disabled=false; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; }
  addEventListener(name,handler) { this.listeners[name]=handler; }
}
const elements=new Map();
const get=(selector)=>{if(!elements.has(selector))elements.set(selector,new Element('div'));return elements.get(selector);};
get('#translation-model').value='qwen3.5:4b';
get('#translation-provider').value='deepl';
const original={title:'Product v1.2.3',source:'Source',source_url:'https://source.example/item',
  metadata:[{label:'Требования',value:'Оригинал Windows 10'}],installation:[],dates:{},images:[],videos:[],notices:[]};
let translatedCalls=0,filesCalls=0,reject=false;
const clone=(value)=>JSON.parse(JSON.stringify(value));
const context=vm.createContext({URLSearchParams,location:{pathname:'/item/ref',search:''},
  window:{VSTI18n:{language:'es'},addEventListener(){}},
  document:{querySelector:get,createElement:(tag)=>new Element(tag),createTextNode:(text)=>({textContent:text})},
  fetch:async(path,options)=>{
    if(path==='/api/details')return {ok:true,json:async()=>clone(original)};
    if(path==='/api/files'){filesCalls++;return {ok:true,json:async()=>({files:[{kind:'arquivo',name:'Pesquisar.zip',url:'https://source.example/file.zip'}],notices:[]})};}
    if(path==='/api/translation-settings')return {ok:true,json:async()=>({deepl_configured:true})};
    assert.equal(path,'/api/translate');translatedCalls++;
    assert.equal(JSON.parse(options.body).target,'es');
    if(reject)return {ok:false,json:async()=>({error:'changed_technical_tokens'})};
    const item=clone(original);item.metadata[0].value='Traducción Windows 10';
    return {ok:true,json:async()=>({original:clone(original),item,target:'es',provider:'deepl'})};
  }});
vm.runInContext(fs.readFileSync('vstworld/static/item.js','utf8'),context);
(async()=>{
  await new Promise(setImmediate);
  assert.equal(get('#translation-target').value,'es');
  assert.equal(get('#files').children[0].children[2].textContent,'Pesquisar.zip');
  assert.equal(get('#files').children[0].children[2].className,'file-name');
  await get('#translate-item').listeners.click();
  assert.equal(get('#facts').children[1].textContent,'Traducción Windows 10');
  assert.equal(get('#item-title').textContent,original.title);
  assert.equal(get('#show-original').disabled,false);
  get('#show-original').listeners.click();
  assert.equal(get('#facts').children[1].textContent,original.metadata[0].value);
  assert.equal(get('#show-original').disabled,true);
  await get('#translate-item').listeners.click();
  assert.equal(translatedCalls,1,'alternar original/tradução não repete pedido cobrado');
  reject=true;get('#translation-provider').value='local';
  await get('#translate-item').listeners.click();
  assert.equal(get('#facts').children[1].textContent,original.metadata[0].value,'erro mantém o original');
  assert.match(get('#translation-status').textContent,/dados técnicos protegidos/);
  assert.equal(get('#translate-item').disabled,false);
  assert.equal(filesCalls,1,'traduzir não consulta downloads novamente');
  console.log('OK: tradução explícita, cache da página, original e falha sem perda de dados');
})().catch(error=>{console.error(error);process.exitCode=1;});
