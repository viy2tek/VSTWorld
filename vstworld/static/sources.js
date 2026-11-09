'use strict';
const $ = (selector) => document.querySelector(selector);
const form = $('#source-form');
const state = {sources: [], revision: '', selected: null, dirty: false, rawDirty: false, urlChanged: false, ready: false, busy: false, version: 0};
const blank = () => ({id: '', name: '', enabled: true, respect_robots: true, base_url: '', hosts: [],
  search_path: '', method: 'GET', query_param: 'q', params: {}, max_query: 200,
  item_selector: '', title_selector: '', link_selector: null, description_selector: null,
  next_selector: null, download_selector: '', detail_selector: null, published_selector: null,
  modified_selector: null, interval: 1, sections: [], note: ''});
function element(tag, text) {
  const value = document.createElement(tag);
  if (text !== undefined) value.textContent = text;
  return value;
}
function message(text, error = false) {
  $('#editor-status').textContent = text;
  $('#editor-status').dataset.error = String(error);
}
function markDirty() {
  state.dirty = true;
  state.version++;
  $('#dirty-label').textContent = 'Alterações não salvas';
  $('#save-source').disabled = state.busy || !state.ready;
}
async function request(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  const result = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(result.detail) ? result.detail.map((item) =>
      `${item.loc.filter((part) => part !== 'body').join('.')}: ${item.msg}`).join('\n') : result.detail;
    throw new Error(detail || 'Falha na solicitação. Tente novamente.');
  }
  return result;
}
function readForm() {
  const value = blank();
  for (const key of Object.keys(value)) {
    const field = form.elements.namedItem(key);
    if (key === 'enabled' || key === 'respect_robots') value[key] = field.checked;
    else if (key === 'hosts') value[key] = field.value.split(',').map((host) => host.trim()).filter(Boolean);
    else if (key === 'max_query' || key === 'interval') value[key] = Number(field.value);
    else if (key === 'params' || key === 'sections') {
      try { value[key] = JSON.parse(field.value || (key === 'params' ? '{}' : '[]')); }
      catch { throw new Error(`${key === 'params' ? 'Parâmetros' : 'Seções'}: JSON inválido. Confira vírgulas, aspas e colchetes.`); }
      if (key === 'sections' ? !Array.isArray(value[key]) : (!value[key] || Array.isArray(value[key]) || typeof value[key] !== 'object')) {
        throw new Error(key === 'sections' ? 'Seções precisam ser uma lista JSON.' : 'Parâmetros precisam ser um objeto JSON.');
      }
    } else value[key] = ['link_selector', 'description_selector', 'next_selector', 'detail_selector', 'published_selector', 'modified_selector'].includes(key) ? field.value.trim() || null : field.value;
  }
  return value;
}
function fillForm(source) {
  const value = {...blank(), ...source};
  for (const [key, item] of Object.entries(value)) {
    const field = form.elements.namedItem(key);
    if (!field) throw new Error(`Campo não suportado: ${key}`);
    if (key === 'enabled' || key === 'respect_robots') field.checked = item;
    else if (key === 'hosts') field.value = Array.isArray(item) ? item.join(', ') : '';
    else if (key === 'params' || key === 'sections') field.value = JSON.stringify(item, null, 2);
    else field.value = item ?? '';
  }
  $('#raw-source').value = JSON.stringify(value, null, 2);
  state.rawDirty = false;
  state.urlChanged = false;
  $('#site-url').value = value.base_url;
  $('#editor-title').textContent = state.selected === null ? 'Nova fonte' : `Editar ${value.name}`;
  $('#test-output').replaceChildren();
  state.version++;
}
function renderList() {
  $('#source-list').replaceChildren();
  if (!state.sources.length) $('#source-list').append(element('p', 'Nenhuma fonte cadastrada.'));
  state.sources.forEach((source, index) => {
    const button = element('button', source.name);
    button.type = 'button';
    button.setAttribute('aria-current', String(state.selected === index));
    button.append(element('small', source.enabled ? 'Habilitada' : 'Desativada'));
    button.addEventListener('click', () => ifClean(() => select(index)));
    $('#source-list').append(button);
  });
  $('#delete-source').disabled = state.selected === null || state.busy;
}
function select(index) {
  state.selected = index;
  state.dirty = false;
  state.ready = index !== null;
  $('#dirty-label').textContent = '';
  $('#decision').hidden = true;
  $('#advanced-settings').open = false;
  $('#detection-checks').replaceChildren();
  $('#detection-report').textContent = '';
  fillForm(index === null ? blank() : state.sources[index]);
  renderList();
  $('#save-source').disabled = !state.ready || state.busy;
}
function decision(text, action) {
  $('#decision-text').textContent = text;
  $('#decision').hidden = false;
  $('#decision-confirm').onclick = () => { $('#decision').hidden = true; action(); };
  $('#decision-cancel').onclick = () => { $('#decision').hidden = true; };
  $('#decision-confirm').focus();
}
function ifClean(action) {
  if (state.busy) return;
  if (state.dirty) decision('Descartar as alterações não salvas desta fonte?', action);
  else action();
}
function setBusy(busy) {
  state.busy = busy;
  $('#raw-source').disabled = busy;
  for (const field of form.elements) field.disabled = busy;
  for (const selector of ['#new-source', '#reload-sources', '#apply-json', '#refresh-json', '#test-source', '#detect-source', '#site-url']) $(selector).disabled = busy;
  for (const button of $('#source-list').querySelectorAll('button')) button.disabled = busy;
  $('#delete-source').disabled = busy || state.selected === null;
  $('#save-source').disabled = busy || !state.ready;
}
async function persist(sources, selectedId) {
  setBusy(true);
  message('Salvando configuração…');
  try {
    const result = await request('/api/source-config', {revision: state.revision, sources});
    state.sources = result.sources;
    state.revision = result.revision;
    const index = state.sources.findIndex((source) => source.id === selectedId);
    select(index >= 0 ? index : (state.sources.length ? 0 : null));
    message('Fontes salvas e aplicadas. Recarregue outras abas do catálogo para atualizar seus resultados.');
  } catch (error) { message(error.message, true); }
  finally { setBusy(false); }
}
form.addEventListener('input', () => { state.ready = true; markDirty(); });
form.addEventListener('invalid', () => { $('#advanced-settings').open = true; }, true);
$('#site-url').addEventListener('input', () => { markDirty(); state.urlChanged = true; });
$('#raw-source').addEventListener('input', () => { state.rawDirty = true; markDirty(); });
window.addEventListener('beforeunload', (event) => {
  if (state.dirty) { event.preventDefault(); event.returnValue = ''; }
});
form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (state.busy) return;
  try {
    if (state.urlChanged) throw new Error('Clique em Identificar site para preparar a configuração desse endereço antes de salvar.');
    if (state.rawDirty) throw new Error('O JSON avançado tem alterações. Clique em Aplicar JSON ao formulário antes de salvar.');
    const source = readForm();
    const sources = state.sources.slice();
    if (sources.some((item, index) => item.id === source.id && index !== state.selected)) throw new Error('Já existe uma fonte com esse identificador. Escolha outro.');
    if (state.selected === null) sources.push(source);
    else sources[state.selected] = source;
    persist(sources, source.id);
  } catch (error) { message(error.message, true); }
});
$('#new-source').addEventListener('click', () => ifClean(() => { select(null); message('Cole o link do site e clique em Identificar site.'); $('#site-url').focus(); }));
$('#delete-source').addEventListener('click', () => {
  if (state.busy || state.selected === null) return;
  const index = state.selected;
  decision(`Remover “${state.sources[index].name}” do catálogo?`, () => persist(state.sources.filter((_, item) => item !== index)));
});
async function load() {
  setBusy(true);
  try {
    const result = await request('/api/source-config');
    state.sources = result.sources;
    state.revision = result.revision;
    select(state.sources.length ? 0 : null);
    message('Configuração carregada. Escolha uma fonte ou adicione um site.');
  } catch (error) { message(error.message, true); }
  finally { setBusy(false); }
}
$('#reload-sources').addEventListener('click', () => ifClean(load));
$('#refresh-json').addEventListener('click', () => {
  const refresh = () => {
    try { $('#raw-source').value = JSON.stringify(readForm(), null, 2); state.rawDirty = false; message('JSON atualizado com os campos do formulário.'); }
    catch (error) { message(error.message, true); }
  };
  if (state.rawDirty) decision('Substituir as alterações no JSON pelos campos atuais do formulário?', refresh);
  else refresh();
});
$('#apply-json').addEventListener('click', () => {
  try {
    const value = JSON.parse($('#raw-source').value);
    if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('Use um objeto JSON para uma única fonte.');
    for (const key of Object.keys(value)) if (!Object.hasOwn(blank(), key)) throw new Error(`Campo não suportado: ${key}`);
    fillForm(value);
    state.ready = true;
    markDirty();
    message('JSON aplicado ao formulário. Revise e clique em Salvar fonte para persistir.');
  } catch (error) { message(`Não foi possível aplicar o JSON: ${error.message}`, true); }
});
$('#detect-source').addEventListener('click', async () => {
  if (state.busy) return;
  let url = $('#site-url').value.trim();
  if (!url) { message('Cole o link do site que deseja adicionar.', true); $('#site-url').focus(); return; }
  if (!url.includes('://')) url = 'https://' + url;
  if (url.startsWith('http://')) url = 'https://' + url.slice(7);
  setBusy(true);
  message('Inspecionando o site e conferindo sua busca…');
  $('#detection-checks').replaceChildren();
  try {
    const result = await request('/api/source-detect', {url});
    if (result.source) {
      const index = state.sources.findIndex((source) => source.id === result.source.id);
      state.selected = index >= 0 ? index : null;
      fillForm(result.source);
      state.ready = true;
      markDirty();
      renderList();
    }
    const names = {homepage:'Página do site', form:'Busca', results:'Resultados', search:'Teste da busca',
      pagination:'Próxima página', detail:'Página do item', download:'Links de download', robots:'Política da fonte', access:'Acesso', url:'Endereço'};
    const verified = {homepage:'Acessível.', form:'Campo de pesquisa identificado.', results:'Títulos identificados.',
      search:'O teste encontrou resultados.', pagination:'Link encontrado; a página seguinte ainda não foi testada.',
      detail:'Página consultada.', download:'Link encontrado; o arquivo não foi baixado nem validado.', robots:'Regras da fonte verificadas.'};
    result.checks.forEach((check) => {
      const text = check.name === 'form' && check.status !== 'verified' ? check.message :
        check.status === 'verified' ? (verified[check.name] || 'Verificado.') :
        check.status === 'blocked' ? 'Não foi possível consultar esta parte do site. Veja o relatório avançado para o motivo.' :
        check.name === 'robots' ? 'Segue a política de acesso já definida para esta fonte.' : 'Ainda não confirmado nesta amostra.';
      const item = element('li', `${names[check.name] || check.name}: ${text}`);
      item.dataset.status = check.status;
      $('#detection-checks').append(item);
    });
    $('#detection-report').textContent = result.checks.map((check) => `${check.name}: ${check.message}`).join('\n');
    message(result.source ? 'Fonte preparada. Confira o que foi identificado e clique em Salvar fonte.' :
      'Não conseguimos identificar este site automaticamente. Veja as verificações; a configuração manual fica em Avançadas.', !result.source);
  } catch (error) { message(error.message, true); }
  finally { setBusy(false); }
});
$('#test-source').addEventListener('click', async () => {
  if (!form.reportValidity() || state.busy) return;
  if (state.rawDirty) { message('Aplique o JSON ao formulário antes de testar.', true); return; }
  let source;
  try { source = readForm(); } catch (error) { message(error.message, true); return; }
  const query = $('#test-query').value;
  const section = $('#test-section').value.trim() || null;
  if (!query.trim() && !section) { message('Informe uma consulta de teste ou o identificador de uma seção.', true); return; }
  const version = state.version;
  const button = $('#test-source');
  button.disabled = true;
  button.textContent = 'Testando…';
  $('#test-output').replaceChildren(element('p', 'Consultando a fonte com a configuração atual…'));
  try {
    const result = await request('/api/source-test', {source, query, section});
    if (version !== state.version) return;
    const output = $('#test-output');
    output.replaceChildren(element('p', result.status === 'ok' ? `${result.count} resultado(s) extraído(s). ${result.has_next ? 'Próxima página identificada.' : 'Nenhuma próxima página identificada.'}` : result.message));
    if (result.message && result.status === 'ok') output.append(element('p', result.message));
    const list = element('ul');
    result.items.forEach((item) => list.append(element('li', item.title)));
    output.append(list);
  } catch (error) { if (version === state.version) $('#test-output').replaceChildren(element('p', error.message)); }
  finally { button.disabled = state.busy; button.textContent = 'Testar configuração'; }
});
load();
