'use strict';

const FILTER_CHOICES = {
  system: ['windows', 'macos', 'linux'],
  format: ['vst', 'vst2', 'vst3', 'au', 'aax', 'kontakt'],
  architecture: ['32', '64'],
  kind: ['instrument', 'effect', 'samples', 'presets', 'software'],
  dateField: ['published', 'modified']
};
const FILTER_KEYS = ['system', 'format', 'architecture', 'kind', 'developer', 'version', 'dateField', 'from', 'to'];

function filterDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith('0000')) return '';
  const date = new Date(value + 'T00:00:00Z');
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value ? value : '';
}

function filterText(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
}

function readFilters() {
  const filters = {};
  for (const key of FILTER_KEYS) {
    filters[key] = document.querySelector('#f-' + key)?.value.trim() || (key === 'dateField' ? 'published' : '');
  }
  return filters;
}

function validateFilters(filters) {
  for (const [key, choices] of Object.entries(FILTER_CHOICES)) {
    if (filters[key] && !choices.includes(filters[key])) return 'Selecione uma opção válida para os filtros.';
  }
  if (['developer', 'version'].some((key) => (filters[key] || '').length > 120)) return 'Fabricante e versão devem ter no máximo 120 caracteres.';
  if (['from', 'to'].some((key) => filters[key] && !filterDate(filters[key]))) return 'Informe datas válidas no formato ano-mês-dia.';
  if (filters.from && filters.to && filters.from > filters.to) return 'A data inicial deve ser anterior ou igual à data final.';
  return '';
}

function writeFilterParams(params, filters = readFilters()) {
  for (const key of FILTER_KEYS) {
    const value = filters[key] || '';
    if (value && !(key === 'dateField' && value === 'published')) params.set('f-' + key, value);
    else params.delete('f-' + key);
  }
  return params;
}

function restoreFilters(params) {
  for (const key of FILTER_KEYS) {
    let value = params.get('f-' + key) || '';
    if (FILTER_CHOICES[key] && !FILTER_CHOICES[key].includes(value)) value = '';
    if (key === 'from' || key === 'to') value = filterDate(value);
    if (key === 'developer' || key === 'version') value = value.trim().slice(0, 120);
    const control = document.querySelector('#f-' + key);
    if (control) control.value = value || (key === 'dateField' ? 'published' : '');
  }
  return readFilters();
}

function filterVerdict(item, filters) {
  const metadata = item.filters || {};
  const verdicts = [];
  const listVerdict = (key, wanted) => {
    const values = Array.isArray(metadata[key]) ? metadata[key] : [];
    if (!values.length) return 'unknown';
    if (values.some((value) => value === wanted || (key === 'format' && wanted === 'vst' && ['vst2', 'vst3'].includes(value)))) return 'match';
    if (key === 'format' && ['vst2', 'vst3'].includes(wanted) && values.includes('vst')) return 'unknown';
    return 'mismatch';
  };
  const targets = Array.isArray(metadata.targets) ? metadata.targets : [];
  if (filters.system && filters.architecture && targets.length) {
    // Keep platform/bitness pairs together: a Windows build cannot supply a Mac build's bitness.
    const platformTargets = targets.filter((target) => target.system === filters.system);
    if (!platformTargets.length) verdicts.push(targets.some((target) => target.system) ? 'mismatch' : 'unknown');
    else if (platformTargets.some((target) => target.architecture === filters.architecture)) verdicts.push('match');
    else verdicts.push(platformTargets.some((target) => !target.architecture) ? 'unknown' : 'mismatch');
  } else {
    for (const key of ['system', 'architecture']) if (filters[key]) verdicts.push(listVerdict(key, filters[key]));
  }
  for (const key of ['format', 'kind']) if (filters[key]) verdicts.push(listVerdict(key, filters[key]));
  for (const key of ['developer', 'version']) {
    if (!filterText(filters[key])) continue;
    const value = filterText(metadata[key]);
    verdicts.push(!value ? 'unknown' : value.includes(filterText(filters[key])) ? 'match' : 'mismatch');
  }
  if (filters.from || filters.to) {
    const value = item[filters.dateField || 'published'];
    const day = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}(?:$|T| )/.test(value) ? filterDate(value.slice(0, 10)) : '';
    verdicts.push(!day ? 'unknown' : (filters.from && day < filters.from) || (filters.to && day > filters.to) ? 'mismatch' : 'match');
  }
  return verdicts.includes('mismatch') ? 'mismatch' : verdicts.includes('unknown') ? 'unknown' : 'match';
}
