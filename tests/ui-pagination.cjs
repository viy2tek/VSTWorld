// DOM mínimo para exercitar o controle de paginação sem dependência de navegador.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.value = ''; }
  append(...items) { for (const item of items) { item.parent = this; this.children.push(item); } }
  replaceChildren(...items) { this.children = []; this.append(...items); }
  setAttribute() {}
  addEventListener(name, handler) { this.listeners[name] = handler; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((item) => item !== this); }
}
async function check(failure) {
  const elements = new Map();
  let calls = 0;
  const context = vm.createContext({
    AbortController,
    URLSearchParams, location:{pathname:'/',search:''},
    document: {
      createElement: (tag) => new Element(tag),
      createTextNode: (text) => ({textContent: text}),
      querySelector: (selector) => {
        if (!elements.has(selector)) elements.set(selector, new Element('div'));
        return elements.get(selector);
      }
    },
    fetch: async (path) => ({ok: true, json: async () => {
      if (path === '/api/sources') return [];
      calls++;
      if (calls === 1) return {status: 'ok', items: [], next: 'next-page'};
      if (calls === 2) {
        if (failure === 'network') throw new Error('Connection lost');
        return {status: 'error', message: 'Fonte indisponível; tente novamente', items: []};
      }
      return {status: 'ok', items: [], next: null};
    }})
  });
  vm.runInContext(fs.readFileSync('vstworld/static/filters.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('vstworld/static/app.js', 'utf8'), context);
  vm.runInContext('state.generation = 1; state.controller = new AbortController()', context);
  const group = new Element('section');
  await context.searchSource({id: 'test', name: 'Test'}, 'query', null, group, 1);
  const more = group.children.find((item) => item.tag === 'button');
  assert.ok(more, 'próxima página deve estar disponível');
  await more.listeners.click();
  await new Promise(setImmediate);
  assert.ok(group.children.includes(more), `${failure}: falha não pode remover o botão para tentar novamente`);
  assert.equal(more.disabled, false);
  await more.listeners.click();
  await new Promise(setImmediate);
  assert.equal(calls, 3, 'retry deve consultar a mesma próxima página');
  assert.equal(group.children.includes(more), false, 'sucesso sem outra página remove o botão antigo');
  group.items = [
    {title:'Antigo',ref:'a',published:'2020-01-01',modified:null},
    {title:'Sem publicação',ref:'b',published:null,modified:'2026-01-01'},
    {title:'Recente',ref:'c',published:'2025-01-01',modified:null}
  ];
  elements.get('#sort').value = 'published-new';
  context.renderTitles(group);
  const titles = group.list.children.map(item => item.children[0].children[0].textContent);
  assert.deepEqual(titles, ['Recente','Antigo','Sem publicação']);
  assert.ok(group.list.children.every(item => item.children.length === 1), 'resultados mostram só o título');
  context.updateSorting();
  assert.equal(elements.get('#sort-modified').disabled, false);
  elements.get('#f-system').value = 'windows';
  context.updateFilterCount();
  assert.equal(elements.get('#filter-count').textContent, '1 ativo(s)', 'resumo mostra filtro ativo mesmo recolhido');
  elements.get('#f-system').value = '';
  context.updateFilterCount();
  assert.equal(elements.get('#filter-count').textContent, '', 'data padrão não conta como filtro ativo');
}
(async () => {
  await check('source');
  await check('network');
  console.log('OK: retry de paginação após erro de fonte e falha de rede');
})().catch((error) => { console.error(error); process.exitCode = 1; });
