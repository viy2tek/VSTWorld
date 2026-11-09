/* Fixed interface translations only; source content and form values stay untouched. */
(() => {
  'use strict';
  const supported = ['pt', 'en', 'es'];
  const preferenceKey = 'vstworld-language';
  let saved;
  try { saved = localStorage.getItem(preferenceKey); } catch {}
  let language = supported.includes(saved) ? saved : (navigator.language || 'pt').split('-')[0].toLowerCase();
  if (!supported.includes(language)) language = 'pt';
  let dictionary = {}, patterns = [];
  const originals = new WeakMap();
  const attributes = new WeakMap();
  const skip = 'script,style,code,pre,[data-i18n-skip],.title-result,.source-note,#item-source,#facts dd,#installation,#attribution a,.file-name,#test-output li';
  function translate(text) {
    if (language === 'pt') return text;
    const match = /^(\s*)([\s\S]*?)(\s*)$/.exec(text);
    const core = match[2];
    let result = dictionary[core]?.[language];
    if (result === undefined) {
      for (const pattern of patterns) {
        const captures = new RegExp(pattern.pt).exec(core);
        if (captures) {
          result = pattern[language].replace(/\$(\d+)/g, (_, index) => {
            const value = captures[Number(index)] || '';
            return pattern.translateCaptures?.includes(Number(index)) ? translate(value) : value;
          });
          break;
        }
      }
    }
    return result === undefined ? text : match[1] + result + match[3];
  }
  function updateText(node) {
    const parent = node.parentElement;
    if (!parent || parent.closest(skip + ',input,textarea')) return;
    const previous = originals.get(node);
    const source = previous && node.data === previous.rendered ? previous.source : node.data;
    if (parent.id === 'item-title' && !['Carregando item…','Detalhes do item','Não foi possível abrir o item'].includes(source)) return;
    // These nodes hold arbitrary source names, even when a name resembles a UI label.
    if (parent.matches('.source-heading h3,#source-list button,#results-title') &&
        !(parent.id === 'results-title' && (node.data === 'Catálogo' || /^Resultados para “/.test(node.data) || originals.has(node)))) return;
    const rendered = translate(source);
    originals.set(node, {source, rendered});
    if (node.data !== rendered) node.data = rendered;
  }
  function updateElement(element) {
    if (element.closest(skip)) return;
    let cache = attributes.get(element);
    if (!cache) { cache = {}; attributes.set(element, cache); }
    for (const name of ['placeholder', 'title', 'aria-label', 'alt']) {
      if (!element.hasAttribute(name)) continue;
      const current = element.getAttribute(name), previous = cache[name];
      const source = previous && current === previous.rendered ? previous.source : current;
      const rendered = translate(source);
      cache[name] = {source, rendered};
      if (current !== rendered) element.setAttribute(name, rendered);
    }
  }
  function scan(root = document.documentElement) {
    if (root.nodeType === 3) { updateText(root); return; }
    if (root.nodeType !== 1) return;
    updateElement(root);
    const walker = document.createTreeWalker(root, 5);
    let node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === 3) updateText(node);
      else updateElement(node);
    }
  }
  function applyLanguage() {
    document.documentElement.lang = language === 'pt' ? 'pt-BR' : language;
    const selector = document.getElementById('ui-language');
    if (selector) { selector.value = language; selector.setAttribute('aria-label', translate('Idioma da interface')); }
    scan();
  }
  window.VSTI18n = {
    get language() { return language; },
    translate,
    setLanguage(value) {
      if (!supported.includes(value)) return;
      language = value;
      try { localStorage.setItem(preferenceKey, language); } catch {}
      applyLanguage();
      window.dispatchEvent(new CustomEvent('vstworld:language', {detail: {language}}));
    }
  };
  document.getElementById('ui-language')?.addEventListener('change', event => window.VSTI18n.setLanguage(event.target.value));
  applyLanguage();
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'childList') record.addedNodes.forEach(scan);
      else if (record.type === 'characterData') updateText(record.target);
      else updateElement(record.target);
    }
  }).observe(document.documentElement, {subtree:true, childList:true, characterData:true, attributes:true, attributeFilter:['placeholder','title','aria-label','alt']});
  fetch('/static/locales.json').then(response => {
    if (!response.ok) throw new Error('Locale unavailable');
    return response.json();
  }).then(value => { dictionary = value.strings; patterns = value.patterns; applyLanguage(); }).catch(() => {});
})();
