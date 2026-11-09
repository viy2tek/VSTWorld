'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const base = path.join(__dirname, '../vstworld/static');
const locales = JSON.parse(fs.readFileSync(path.join(base, 'locales.json'), 'utf8'));
const script = fs.readFileSync(path.join(base, 'i18n.js'), 'utf8');

class Element {
  constructor(tag, attrs = {}, children = []) {
    this.nodeType = 1; this.tagName = tag; this.attrs = attrs; this.id = attrs.id;
    this.children = children; this.value = ''; this.events = {};
    children.forEach(child => { child.parentElement = this; });
  }
  matches(selectors) {
    return selectors.split(',').some(selector => {
      const parts = selector.trim().split(' '), last = parts.pop();
      const matches = last.startsWith('#') ? this.id === last.slice(1) : last.startsWith('.')
        ? (this.attrs.class || '').split(' ').includes(last.slice(1))
        : last.startsWith('[') ? this.hasAttribute(last.slice(1, -1)) : this.tagName === last;
      return matches && (!parts.length || this.parentElement?.closest(parts.join(' ')));
    });
  }
  closest(selector) { return this.matches(selector) ? this : this.parentElement?.closest(selector); }
  hasAttribute(name) { return Object.hasOwn(this.attrs, name); }
  getAttribute(name) { return this.attrs[name]; }
  setAttribute(name, value) { this.attrs[name] = value; }
  addEventListener(name, callback) { this.events[name] = callback; }
}
const text = data => ({nodeType:3, data});
async function launch({saved = null, browserLanguage = 'pt-BR', blocked = false} = {}) {
  const label = text('  Pesquisar\n'), dynamic = text('Pronto para pesquisar');
  const product = text('Pesquisar'), sourceValue = text('Sistema'), code = text('Pesquisar');
  const title = text('Carregando item…');
  const sourceName = text('Pesquisar'), enabled = text('Habilitada'), installation = text('Pesquisar'), note = text('Pesquisar');
  const skipped = text('English');
  const input = new Element('input', {placeholder:'Busque por nome'}); input.value = 'unsaved user text';
  const selector = new Element('select', {id:'ui-language', 'data-i18n-skip':'', 'aria-label':'Idioma da interface'}, [new Element('option', {}, [skipped])]);
  const tree = new Element('html', {}, [new Element('button', {}, [label]), new Element('p', {}, [dynamic]),
    new Element('article', {class:'title-result'}, [product]), new Element('dl', {id:'facts'}, [new Element('dd', {}, [sourceValue])]),
    new Element('pre', {}, [code]), new Element('h1', {id:'item-title'}, [title]), input, selector,
    new Element('div', {id:'source-list'}, [new Element('button', {}, [sourceName, new Element('small', {}, [enabled])])]),
    new Element('div', {id:'installation'}, [installation]), new Element('p', {class:'source-note'}, [note])]);
  const flatten = root => root.children?.flatMap(child => [child, ...flatten(child)]) || [];
  let observer, stored, event;
  const window = {dispatchEvent(value) { event = value; }};
  const document = {documentElement:tree, getElementById:id => flatten(tree).find(node => node.id === id),
    createTreeWalker(root) { const nodes = flatten(root); let index = 0; return {nextNode:() => nodes[index++]}; }};
  vm.runInNewContext(script, {window, document, navigator:{language:browserLanguage},
    localStorage:{getItem() { if (blocked) throw Error(); return saved; }, setItem(key, value) { if (blocked) throw Error(); stored = [key,value]; }},
    MutationObserver:class { constructor(callback) { observer = callback; } observe() {} },
    CustomEvent:class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    fetch:async () => ({ok:true,json:async () => locales})});
  await new Promise(resolve => setImmediate(resolve));
  return {api:window.VSTI18n, tree, label, dynamic, product, sourceValue, sourceName, enabled, installation, note, skipped, code, input, title, selector,
    observe:records => observer(records), stored:() => stored, event:() => event};
}
(async () => {
  const ui = await launch({saved:'en', browserLanguage:'es-MX'});
  assert.equal(ui.api.language, 'en'); assert.equal(ui.tree.lang, 'en');
  assert.equal(ui.label.data, '  Search\n'); assert.equal(ui.input.attrs.placeholder, 'Search by name');
  assert.equal(ui.input.value, 'unsaved user text');
  assert.equal(ui.product.data, 'Pesquisar'); assert.equal(ui.sourceValue.data, 'Sistema'); assert.equal(ui.code.data, 'Pesquisar');
  assert.equal(ui.sourceName.data, 'Pesquisar'); assert.equal(ui.enabled.data, 'Enabled');
  assert.equal(ui.installation.data, 'Pesquisar'); assert.equal(ui.note.data, 'Pesquisar'); assert.equal(ui.skipped.data, 'English');
  assert.equal(ui.title.data, 'Loading item…'); assert.equal(ui.selector.attrs['aria-label'], 'Interface language');
  assert.equal(ui.api.translate('Resultados para “Pesquisar $1”'), 'Results for “Pesquisar $1”');
  assert.equal(ui.api.translate('3 de 7 itens carregados · 2 fonte(s) consultando… · 1 sem dados para os filtros'),
    '3 of 7 items loaded · Querying 2 source(s)… · 1 without filter data');
  assert.equal(ui.api.translate('Fichas processadas: 2/5 · 1 falha(s), tente novamente ou refaça a pesquisa.'),
    'Details processed: 2/5 · 1 failure(s), try again or repeat the search.');
  assert.equal(ui.api.translate('Publicação da página: 2026-11-09 · Atualização da página: 2026-11-10'),
    'Page published: 2026-11-09 · Page updated: 2026-11-10');
  assert.equal(ui.api.translate('Busca: Campo de pesquisa identificado.'), 'Search: Search field identified.');
  ui.api.setLanguage('es');
  assert.equal(ui.label.data, '  Buscar\n'); assert.equal(ui.input.value, 'unsaved user text');
  assert.equal(ui.stored()[1], 'es'); assert.equal(ui.event().detail.language, 'es');
  const added = text('Salvar fonte'); added.parentElement = new Element('button', {}, [added]);
  ui.observe([{type:'childList', addedNodes:[added.parentElement]}]);
  assert.equal(added.data, 'Guardar fuente');
  ui.input.setAttribute('placeholder', 'Nome de um item conhecido');
  ui.observe([{type:'attributes', target:ui.input}]);
  assert.equal(ui.input.attrs.placeholder, 'Nombre de un elemento conocido');
  ui.title.data = 'Pesquisar'; ui.observe([{type:'characterData', target:ui.title}]);
  assert.equal(ui.title.data, 'Pesquisar');
  ui.dynamic.data = 'Carregando próxima página…';
  ui.observe([{type:'characterData', target:ui.dynamic}]);
  assert.equal(ui.dynamic.data, 'Cargando la página siguiente…');
  ui.observe([{type:'characterData', target:ui.dynamic}]);
  assert.equal(ui.dynamic.data, 'Cargando la página siguiente…');
  ui.api.setLanguage('pt'); assert.equal(ui.label.data, '  Pesquisar\n');
  assert.equal(ui.dynamic.data, 'Carregando próxima página…'); assert.equal(ui.tree.lang, 'pt-BR');
  ui.api.setLanguage('xx'); assert.equal(ui.api.language, 'pt');
  const blocked = await launch({browserLanguage:'es-AR', blocked:true});
  assert.equal(blocked.api.language, 'es'); blocked.api.setLanguage('en'); assert.equal(blocked.label.data, '  Search\n');
  assert.equal((await launch({saved:'invalid', browserLanguage:'fr-FR'})).api.language, 'pt');
  for (const [source, translations] of Object.entries(locales.strings)) {
    assert.equal(typeof translations.en, 'string', source); assert.equal(typeof translations.es, 'string', source);
    assert(!source.includes('\uFFFD'), source);
  }
  console.log('UI i18n checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
