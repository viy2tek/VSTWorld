const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const controls = new Map();
const context = vm.createContext({
  URLSearchParams,
  document: {querySelector(selector) {
    if (!controls.has(selector)) controls.set(selector, {value: ''});
    return controls.get(selector);
  }}
});
vm.runInContext(fs.readFileSync('vstworld/static/filters.js', 'utf8'), context);
const {filterVerdict: verdict, validateFilters: validate, restoreFilters, readFilters, writeFilterParams} = context;
const item = {title: 'Kontakt VST3 Win64 Release 2030 v9', filters: {}};
assert.equal(verdict(item, {}), 'match');
for (const key of ['system', 'format', 'architecture', 'kind', 'developer', 'version']) {
  assert.equal(verdict(item, {[key]: 'x'}), 'unknown', key + ' must use metadata, never title');
}
assert.equal(verdict({filters: {format: ['au']}}, {format: 'vst3', developer: 'unknown'}), 'mismatch');
assert.equal(verdict({filters: {developer: 'Áudio Élite', version: 'v1.2.3 beta'}}, {developer: 'audio elite', version: '1.2'}), 'match');
assert.equal(verdict({filters: {version: '1.2.3'}}, {version: '>=1.0'}), 'mismatch', 'version is a substring, not a semver expression');
assert.equal(verdict({filters: {kind: ['samples']}}, {kind: 'instrument'}), 'mismatch');
assert.equal(verdict({filters: {kind: ['effect']}}, {kind: 'effect'}), 'match');
for (const format of ['vst', 'vst2', 'vst3']) assert.equal(verdict({filters: {format: [format]}}, {format: 'vst'}), 'match');
assert.equal(verdict({filters: {format: ['vst']}}, {format: 'vst2'}), 'unknown');
assert.equal(verdict({filters: {format: ['vst']}}, {format: 'vst3'}), 'unknown');
assert.equal(verdict({filters: {format: ['vst'], kind: ['effect']}}, {format: 'vst2', kind: 'instrument'}), 'mismatch');
assert.equal(verdict({filters: {format: ['vst3']}}, {format: 'vst2'}), 'mismatch');
const builds = {filters: {system: ['windows', 'macos'], architecture: ['64'], targets: [{system: 'windows', architecture: '64'}, {system: 'macos', architecture: null}]}};
assert.equal(verdict(builds, {system: 'windows', architecture: '64'}), 'match');
assert.equal(verdict(builds, {system: 'macos', architecture: '64'}), 'unknown');
assert.equal(verdict(builds, {system: 'linux', architecture: '64'}), 'mismatch');
builds.filters.targets[1].architecture = '32';
assert.equal(verdict(builds, {system: 'macos', architecture: '64'}), 'mismatch');
builds.filters.targets.push({system: 'macos', architecture: '64'});
assert.equal(verdict(builds, {system: 'macos', architecture: '64'}), 'match');
builds.filters.targets = [];
assert.equal(verdict(builds, {system: 'macos', architecture: '64'}), 'match', 'explicit global metadata is the fallback');
const range = {from: '2024-02-29', to: '2024-02-29', dateField: 'published'};
assert.equal(validate(range), '');
assert.equal(verdict({published: '2024-02-29T23:59:59-12:00'}, range), 'match', 'preserve page date, not UTC date');
assert.equal(verdict({published: '2024-02-28'}, range), 'mismatch');
assert.equal(verdict({published: '2024-03-01'}, range), 'mismatch');
assert.equal(verdict({published: '2024-02-30'}, range), 'unknown');
assert.equal(verdict({release: '2024-02-29', modified: '2024-02-29'}, range), 'unknown');
assert.equal(verdict({modified: '2024-02-29'}, {...range, dateField: 'modified'}), 'match');
for (const date of ['2023-02-29', '2024-02-30', '2024-13-01', '2024-04-31', 'invalid']) assert.ok(validate({from: date}));
assert.ok(validate({from: '2024-02-29', to: '2024-02-28'}));
assert.ok(validate({developer: 'x'.repeat(121)}));
assert.ok(validate({version: 'x'.repeat(121)}));
assert.ok(validate({system: 'android'}));
const params = new URLSearchParams('q=original&section=recent&source=a&sources=a,b&sort=published-old&f-system=macos&f-format=vst3&f-developer=%C3%81udio&f-from=2024-02-29&f-dateField=modified');
restoreFilters(params);
assert.equal(readFilters().system, 'macos');
assert.equal(readFilters().developer, 'Áudio');
assert.equal(readFilters().dateField, 'modified');
assert.equal(writeFilterParams(params), params);
for (const [key, value] of [['q', 'original'], ['section', 'recent'], ['source', 'a'], ['sources', 'a,b'], ['sort', 'published-old']]) assert.equal(params.get(key), value);
restoreFilters(new URLSearchParams('f-system=android&f-format=invalid&f-architecture=128&f-kind=invalid&f-dateField=release&f-from=2024-02-30&f-developer=' + 'x'.repeat(121)));
assert.equal(readFilters().system, '');
assert.equal(readFilters().format, '');
assert.equal(readFilters().architecture, '');
assert.equal(readFilters().kind, '');
assert.equal(readFilters().dateField, 'published');
assert.equal(readFilters().from, '');
assert.equal(readFilters().developer.length, 120);
restoreFilters(new URLSearchParams());
writeFilterParams(params);
assert.equal(params.has('f-system'), false);
assert.equal(params.has('f-dateField'), false);
assert.equal(params.get('sources'), 'a,b');
console.log('OK: filtros, metadados desconhecidos, pares de plataforma, datas e URL');
