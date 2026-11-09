'use strict';
const $ = (selector) => document.querySelector(selector);
const state = {sources: [], generation: 0, pending: 0, count: 0, groups: []};
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
  $('#status').textContent = state.pending ? `${state.pending} fonte(s) consultando… · ${state.count} resultado(s)` : `${state.count} resultado(s) nesta consulta`;
  $('#results').setAttribute('aria-busy', String(state.pending > 0));
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
  const items = [...group.items];
  if (mode !== 'source') items.sort((a, b) => {
    const left = Date.parse(a[key]), right = Date.parse(b[key]);
    if (!Number.isFinite(left)) return Number.isFinite(right) ? 1 : 0;
    if (!Number.isFinite(right)) return -1;
    return mode === 'published-old' ? left - right : right - left;
  });
  group.list.replaceChildren(...items.map(renderItem));
}
function updateSorting() {
  const items = state.groups.flatMap((group) => group.items || []);
  const published = items.some((item) => item.published);
  const modified = items.some((item) => item.modified);
  $('#sort-published').disabled = !published;
  $('#sort-oldest').disabled = !published;
  $('#sort-modified').disabled = !modified;
  $('#sort').disabled = !published && !modified;
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
    const result = await api('/api/search', {source: source.id, query, section, cursor}, state.controller.signal);
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
  const query = section ? '' : $('#query').value;
  const selected = sectionSource ? [sectionSource] : state.sources.filter((source) =>
    source.enabled && document.getElementById(`source-${source.id}`).checked);
  if (!selected.length || (!section && !query.trim())) {
    $('#status').textContent = !selected.length ? 'Selecione ao menos uma fonte.' : 'Digite o nome do que procura.';
    if (!query.trim()) $('#query').focus();
    return;
  }
  state.controller?.abort();
  state.controller = new AbortController();
  state.generation++;
  state.pending = 0;
  state.count = 0;
  state.groups = [];
  $('#sort').value = 'source';
  if (typeof history !== 'undefined') {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (section) { params.set('section', section); params.set('source', sectionSource.id); }
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
$('#sort').addEventListener('change', () => state.groups.forEach(renderTitles));
$('#search-form').addEventListener('submit', (event) => {event.preventDefault(); startSearch();});
async function initialize() {
  try {
    state.sources = await api('/api/sources');
    state.sources.forEach((source) => {
      const container = node('div', undefined, 'source-option');
      const label = node('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `source-${source.id}`;
      checkbox.checked = source.enabled;
      checkbox.disabled = !source.enabled;
      label.append(checkbox, document.createTextNode(source.name + (source.enabled ? '' : ' · desativada')));
      container.append(label);
      if (source.note) container.append(node('p', source.note, 'source-note'));
      $('#source-options').append(container);
      if (source.enabled) source.sections.forEach((section) => {
        const button = node('button', `${section.name} · ${source.name}`);
        button.type = 'button';
        button.addEventListener('click', () => startSearch(source, section.id));
        $('#sections').append(button);
      });
    });
    $('#source-count').textContent = `${state.sources.filter((source) => source.enabled).length} habilitada(s)`;
    $('#status').textContent = 'Pronto para pesquisar';
    $('#results').append(node('p', 'Pesquise nas fontes selecionadas ou navegue pelos itens recentes.', 'empty'));
    const params = new URLSearchParams(location.search);
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
