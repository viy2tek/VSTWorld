const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor() { this.value = ''; this.children = []; this.listeners = {}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute() {}
  addEventListener(name, handler) { this.listeners[name] = handler; }
  querySelectorAll() { return []; }
  focus() {}
}
const elements = new Map();
const fields = new Map();
const get = (key) => {
  if (!elements.has(key)) elements.set(key, new Element());
  return elements.get(key);
};
get('#source-form').elements = {
  namedItem(key) { if (!fields.has(key)) fields.set(key, new Element()); return fields.get(key); },
  *[Symbol.iterator]() { yield* fields.values(); }
};
get('#editor-status').dataset = {};
const context = vm.createContext({
  document: {querySelector: get, createElement: () => new Element()},
  window: {addEventListener() {}},
  fetch: async () => ({ok: true, json: async () => ({revision: 'revision', sources: []})})
});
vm.runInContext(fs.readFileSync('vstworld/static/sources.js', 'utf8'), context);
(async () => {
  await new Promise(setImmediate);
  context.select(null);
  get('#site-url').value = 'https://example.com/';
  get('#site-url').listeners.input();
  assert.equal(get('#save-source').disabled, true, 'colar o link não pode abrir validação técnica antes da identificação');
  context.fillForm(vm.runInContext('({...blank(), respect_robots: false})', context));
  assert.equal(context.readForm().respect_robots, false, 'a opção de robots deve sobreviver ao formulário');
  context.setBusy(true);
  assert.equal(get('#raw-source').disabled, true, 'JSON não deve aceitar alterações enquanto um save está em andamento');
  context.setBusy(false);
  assert.equal(get('#raw-source').disabled, false);
  get('#raw-source').listeners.input();
  get('#source-form').listeners.submit({preventDefault() {}});
  assert.match(get('#editor-status').textContent, /Aplicar JSON/, 'salvar não pode descartar JSON ainda não aplicado');
  console.log('OK: JSON bloqueado durante gravação e alterações não aplicadas preservadas');
})().catch((error) => {console.error(error); process.exitCode = 1;});
