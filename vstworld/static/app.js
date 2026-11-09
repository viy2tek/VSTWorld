'use strict';
const $ = (selector) => document.querySelector(selector);
const state = {sources: [], generation: 0, pending: 0, count: 0, groups: [], enriching:false, searchContext:null};
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function external(url, label, className) {
  const link = node('a', label, className);
  link.href = url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  return link;
}
async function api(path, body, signal) {
  const response = await fetch(path, body === undefined ? {signal} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Solicitação inválida. Refaça a pesquisa.');
  return data;
}
function notice(text, error = false) { return node('p', text, `notice${error ? ' error' : ''}`); }
function updateStatus() {
  const visible = state.groups.reduce((sum, group) => sum + (group.visibleCount || 0), 0);
  const unknown = state.groups.reduce((sum, group) => sum + (group.unknownCount || 0), 0);
  $('#status').textContent = `${visible} de ${state.count} itens carregados` +
    (state.pending ? ` · ${state.pending} fonte(s) consultando…` : '') +
    (unknown ? ` · ${unknown} sem dados para os filtros` : '');
  const invalid = validateFilters(readFilters());
  if (invalid) $('#status').textContent = invalid;
  $('#results').setAttribute('aria-busy', String(state.pending > 0));
  $('#load-facts').disabled = state.enriching || state.count === 0;
  $('#cancel-facts').disabled = !state.enriching;
}
function renderItem(item) {
  const article = node('article', undefined, 'result title-result');
  const heading = node('h4');
  const link = node('a', item.title);
  link.href = `/item/${encodeURIComponent(item.ref)}?back=${encodeURIComponent(location.pathname + location.search)}`;
  heading.append(link);
  article.append(heading);
  return article;
}
function renderTitles(group) {
  const mode = $('#sort').value || 'source';
  const key = mode === 'modified' ? 'modified' : 'published';
  const filters = readFilters();
  const items = group.items.filter((item) => filterVerdict(item, filters) === 'match');
  group.visibleCount = items.length;
  group.unknownCount = group.items.filter((item) => filterVerdict(item, filters) === 'unknown').length;
  if (mode !== 'source') items.sort((a, b) => {
    const left = Date.parse(a[key]), right = Date.parse(b[key]);
    if (!Number.isFinite(left)) return Number.isFinite(right) ? 1 : 0;
    if (!Number.isFinite(right)) return -1;
    return mode === 'published-old' ? left - right : right - left;
  });
  group.list.replaceChildren(...items.map(renderItem));
  if (!items.length && group.items.length) group.list.append(notice('Nenhum item carregado corresponde aos filtros com os dados disponíveis.'));
}
function syncFilterURL() {
  if (typeof history === 'undefined') return;
  const params = writeFilterParams(new URLSearchParams(location.search));
  if ($('#sort').value && $('#sort').value !== 'source') params.set('sort', $('#sort').value);
  else params.delete('sort');
  history.replaceState(null, '', '/' + (params.size ? '?' + params : ''));
}
function refreshFilteredResults() {
  updateFilterCount();
  const error = validateFilters(readFilters());
  if (error) { $('#status').textContent = error; return; }
  syncFilterURL();
  state.groups.forEach(renderTitles);
  updateStatus();
}
function updateFilterCount() {
  const filters = readFilters();
  const count = Object.entries(filters).filter(([key,value]) => key !== 'dateField' && Boolean(value)).length;
  $('#filter-count').textContent = count ? `${count} ativo(s)` : '';
}
function updateSourceCount() {
  const count = state.sources.filter((source) => source.enabled && document.getElementById(`source-${source.id}`).checked).length;
  $('#source-count').textContent = `${count} selecionada(s)`;
}
function updateSorting() {
  const items = state.groups.flatMap((group) => group.items || []);
  const published = items.some((item) => filterDate(String(item.published || '').slice(0,10)));
  const modified = items.some((item) => filterDate(String(item.modified || '').slice(0,10)));
  $('#sort-published').disabled = !published;
  $('#sort-oldest').disabled = !published;
  $('#sort-modified').disabled = !modified;
  $('#sort').disabled = !published && !modified;
  if ((!published && ['published-new','published-old'].includes($('#sort').value)) || (!modified && $('#sort').value === 'modified')) {
    $('#sort').value = 'source'; syncFilterURL();
  }
  $('#sort-note').textContent = published || modified
    ? 'Ordena apenas os itens carregados de cada fonte. Sem data ficam ao final.'
    : 'Ordem da fonte. Não há datas verificáveis para ordenar estes resultados.';
}
async function searchSource(source, query, section, group, generation, cursor = null) {
  state.pending++;
  updateStatus();
  const loading = notice(cursor ? 'Carregando próxima página…' : 'Consultando a fonte…');
  group.append(loading);
  try {
    group.native = group.native || state.native || {};
    const result = await api('/api/search', {source: source.id, query, section, cursor, filters:group.native}, state.controller.signal);
    if (generation !== state.generation) return;
    loading.remove();
    if (result.status === 'error') {
      group.append(notice(result.message, true));
      return false;
    }
    if (!group.items) {
      group.items = [];
      group.list = node('div', undefined, 'title-list');
      group.append(group.list);
      if (!state.groups.includes(group)) state.groups.push(group);
    }
    group.items.push(...result.items);
    renderTitles(group);
    updateSorting();
    state.count += result.items.length;
    if (result.message) group.append(notice(result.message));
    if (result.next) {
      const more = node('button', `Próxima página · ${source.name}`, 'more');
      more.type = 'button';
      more.addEventListener('click', async () => {
        more.disabled = true;
        const loaded = await searchSource(source, query, section, group, generation, result.next);
        if (loaded) more.remove();
        else more.disabled = false;
      });
      group.append(more);
    }
    return true;
  } catch (error) {
    if (generation === state.generation) {
      loading.remove();
      group.append(notice('Falha na conexão com o aplicativo. Tente novamente.', true));
    }
    return false;
  } finally {
    if (generation === state.generation) { state.pending--; updateStatus(); }
  }
}
function startSearch(sectionSource = null, section = null) {
  const filters = readFilters(), invalid = validateFilters(filters);
  if (invalid) { $('#status').textContent = invalid; return; }
  const query = section ? '' : $('#query').value;
  const selected = sectionSource ? [sectionSource] : state.sources.filter((source) =>
    source.enabled && document.getElementById(`source-${source.id}`).checked);
  if (!selected.length || (!section && !query.trim())) {
    $('#status').textContent = !selected.length ? 'Selecione ao menos uma fonte.' : 'Digite o nome do que procura.';
    if (!query.trim()) $('#query').focus();
    return;
  }
  state.controller?.abort();
  state.detailController?.abort();
  state.enriching = false;
  $('#filter-progress').textContent = '';
  state.controller = new AbortController();
  state.generation++;
  state.pending = 0;
  state.count = 0;
  state.groups = [];
  state.searchContext = section ? {source:sectionSource, section} : null;
  state.native = {system:filters.system, format:filters.format, architecture:filters.architecture};
  if (typeof history !== 'undefined') {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (section) { params.set('section', section); params.set('source', sectionSource.id); }
    params.set('sources', selected.map((source) => source.id).join(','));
    writeFilterParams(params, filters);
    if ($('#sort').value && $('#sort').value !== 'source') params.set('sort', $('#sort').value);
    history.replaceState(null, '', '/' + (params.size ? '?' + params : ''));
  }
  $('#results').replaceChildren();
  $('#results-title').textContent = section ? sectionSource.sections.find((item) => item.id === section).name : `Resultados para “${query}”`;
  selected.forEach((source) => {
    const group = node('section', undefined, 'source-results');
    const header = node('div', undefined, 'source-heading');
    header.append(node('h3', source.name), node('span', 'Fonte original', 'badge'));
    group.append(header);
    $('#results').append(group);
    searchSource(source, query, section, group, state.generation);
  });
}
function searchWithFilters() {
  if (state.searchContext) startSearch(state.searchContext.source, state.searchContext.section);
  else startSearch();
}
async function loadFilterFacts() {
  if (state.enriching || !state.count) return;
  const generation = state.generation;
  const records = state.groups.flatMap((group) => group.items).filter((item) => !item.detailsLoaded);
  if (!records.length) { $('#filter-progress').textContent = 'As fichas destes itens já foram lidas.'; return; }
  state.detailController = new AbortController();
  const signal = state.detailController.signal;
  state.enriching = true;
  let index = 0, done = 0, errors = 0;
  $('#filter-progress').textContent = `Lendo fichas: 0/${records.length}…`;
  updateStatus();
  async function worker() {
    while (!signal.aborted && generation === state.generation && index < records.length) {
      const item = records[index++];
      try {
        const detail = await api('/api/details', {ref:item.ref}, signal);
        if (signal.aborted || generation !== state.generation) return;
        if (!detail.filters || !detail.dates) throw new Error('Ficha sem dados de filtro');
        item.filters = {...item.filters};
        for (const [key, value] of Object.entries(detail.filters)) {
          if (Array.isArray(value) ? value.length : Boolean(value)) item.filters[key] = value;
        }
        item.published = detail.dates.published || item.published;
        item.modified = detail.dates.modified || item.modified;
        item.detailsLoaded = true;
      } catch (error) { if (signal.aborted) return; errors++; }
      if (generation !== state.generation) return;
      done++;
      updateSorting();
      refreshFilteredResults();
      $('#filter-progress').textContent = `Fichas processadas: ${done}/${records.length}${errors ? ` · ${errors} falha(s), tente novamente ou refaça a pesquisa` : ''}.`;
    }
  }
  try { await Promise.all(Array.from({length:Math.min(3, records.length)}, worker)); }
  finally {
    if (generation === state.generation) {
      state.enriching = false;
      if (signal.aborted) $('#filter-progress').textContent = `Leitura interrompida. ${done} ficha(s) processada(s).`;
      updateStatus();
    }
  }
}
$('#sort').addEventListener('change', refreshFilteredResults);
$('#apply-filters').addEventListener('click', searchWithFilters);
$('#clear-filters').addEventListener('click', () => {
  restoreFilters(new URLSearchParams()); $('#sort').value = 'source';
  if (state.count && Object.values(state.native || {}).some(Boolean)) searchWithFilters();
  else refreshFilteredResults();
});
$('#load-facts').addEventListener('click', loadFilterFacts);
$('#cancel-facts').addEventListener('click', () => state.detailController?.abort());
for (const id of ['system','format','architecture','kind','developer','version','dateField','from','to']) {
  $('#f-' + id).addEventListener('input', refreshFilteredResults);
  $('#f-' + id).addEventListener('change', refreshFilteredResults);
}
$('#query').addEventListener('input', () => { state.searchContext = null; });
$('#search-form').addEventListener('submit', (event) => {event.preventDefault(); searchWithFilters();});
async function initialize() {
  try {
    state.sources = await api('/api/sources');
    const params = new URLSearchParams(location.search);
    restoreFilters(params);
    updateFilterCount();
    if (Object.entries(readFilters()).some(([key,value]) => key !== 'dateField' && Boolean(value))) $('#filters-panel').open = true;
    if (['source','published-new','published-old','modified'].includes(params.get('sort'))) $('#sort').value = params.get('sort');
    state.sources.forEach((source) => {
      const container = node('div', undefined, 'source-option');
      const label = node('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `source-${source.id}`;
      checkbox.checked = source.enabled && (!params.has('sources') || params.get('sources').split(',').includes(source.id));
      checkbox.disabled = !source.enabled;
      checkbox.addEventListener('change', updateSourceCount);
      label.append(checkbox, document.createTextNode(source.name + (source.enabled ? '' : ' · desativada')));
      container.append(label);
      if (source.note) {
        const info = node('details', undefined, 'source-info');
        info.append(node('summary', 'Sobre esta fonte'), node('p', source.note, 'source-note'));
        container.append(info);
      }
      $('#source-options').append(container);
      if (source.enabled) source.sections.forEach((section) => {
        const button = node('button', `${section.name} · ${source.name}`);
        button.type = 'button';
        button.addEventListener('click', () => startSearch(source, section.id));
        $('#sections').append(button);
      });
    });
    updateSourceCount();
    $('#status').textContent = 'Pronto para pesquisar';
    $('#results').append(node('p', 'Pesquise nas fontes selecionadas ou navegue pelos itens recentes.', 'empty'));
    if (params.get('q')) { $('#query').value = params.get('q'); startSearch(); }
    else if (params.get('section')) {
      const source = state.sources.find((item) => item.id === params.get('source') && item.enabled);
      if (source && source.sections.some((item) => item.id === params.get('section'))) startSearch(source, params.get('section'));
    }
  } catch (error) {
    $('#status').textContent = 'Não foi possível carregar as fontes.';
    $('#results').append(notice('Verifique se o servidor está em execução e recarregue a página.', true));
  }
}
initialize();
