'use strict';
const $ = (selector) => document.querySelector(selector);
const ref = location.pathname.split('/').pop();
let sourceItem = null, activeOriginal = null;
const translatedItems = new Map();
let showingTranslation = false;
const labels = {'дата выпуска':'Data de lançamento', 'год выпуска':'Ano de lançamento', 'версия':'Versão',
  'разработчик':'Desenvolvedora', 'издатель':'Distribuidora', 'сайт разработчика':'Site da desenvolvedora',
  'формат':'Formato', 'форматы':'Formatos', 'разрядность':'Arquitetura', 'таблэтка':'Ativação informada pela fonte',
  'таблетка':'Ativação informada pela fonte', 'системные требования':'Requisitos do sistema', 'размер':'Tamanho',
  'язык интерфейса':'Idioma', 'операционная система':'Sistema operacional', 'платформа':'Plataforma',
  'version':'Versão', 'developer':'Desenvolvedora', 'publisher':'Distribuidora', 'size':'Tamanho',
  'release date':'Data de lançamento', 'system requirements':'Requisitos do sistema', 'format':'Formato', 'operating system':'Sistema operacional'};
function node(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}
function link(url, text, className) {
  const result = node('a', text, className);
  result.href = url; result.target = '_blank'; result.rel = 'noopener noreferrer';
  return result;
}
async function api(path) {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ref})});
  const value = await response.json();
  if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Não foi possível carregar este item. Refaça a pesquisa.');
  return value;
}
function show(id) { $(id).hidden = false; }
function addLinks(container, links) {
  if (!links?.length) return;
  const list = node('ul', undefined, 'install-links');
  links.forEach((item) => {const li = node('li'); li.append(link(item.url, item.label || item.url)); list.append(li);});
  container.append(list);
}
async function downloads() {
  $('#retry-files').disabled = true;
  $('#files').replaceChildren(node('p', 'Verificando os links disponibilizados pela fonte…', 'hint'));
  try {
    const value = await api('/api/files');
    $('#files').replaceChildren();
    value.files.forEach((file) => {
      const anchor = link(file.url, undefined, 'file-link');
      anchor.append(node('span', file.kind.toUpperCase()), document.createTextNode(' · '), node('span', file.name, 'file-name'));
      $('#files').append(anchor);
    });
    value.notices.forEach((text) => $('#files').append(node('p', text, 'hint')));
    if (value.files.some((file) => file.kind === 'torrent' || file.kind === 'magnet')) $('#files').append(node('p', 'Torrents e magnets precisam de um cliente BitTorrent externo.', 'hint'));
    $('#files').append(node('p', 'Links informados pela fonte. Licença, integridade e segurança dos arquivos não verificadas.', 'hint'));
  } catch (error) { $('#files').replaceChildren(node('p', error.message)); }
  finally { $('#retry-files').disabled = false; $('#retry-files').textContent = 'Verificar downloads novamente'; }
}
function imageViewer(image, thumbnail) {
  const dialog = $('#image-dialog'), full = $('#full-image');
  let fallback = false;
  $('#image-status').textContent = 'Consultando a maior imagem disponibilizada pela origem…';
  full.onload = () => {
    const dimensions = `${full.naturalWidth} × ${full.naturalHeight} pixels`;
    const larger = full.naturalWidth > thumbnail.naturalWidth || full.naturalHeight > thumbnail.naturalHeight;
    $('#image-status').textContent = fallback ? `Original indisponível. Miniatura: ${dimensions}.` :
      (larger || image.original_available ? `Imagem disponibilizada pela fonte: ${dimensions}.` : `Nenhuma resolução maior confirmada. Imagem recebida: ${dimensions}.`);
  };
  full.onerror = () => {
    if (!fallback) { fallback = true; full.src = image.thumbnail; }
    else { $('#image-status').textContent = 'A origem não disponibilizou esta imagem no momento.'; }
  };
  full.removeAttribute('src');
  full.src = image.url;
  dialog.showModal();
}
$('#close-image').addEventListener('click', () => $('#image-dialog').close());
$('#retry-files').addEventListener('click', downloads);
function renderText(item, target = '') {
  $('#facts').replaceChildren();
  $('#installation').replaceChildren();
  $('#page-dates').textContent = '';
  $('#installation').lang = target === 'pt' ? 'pt-BR' : target;
  $('#facts-section').hidden = !item.metadata.length && !item.dates.published && !item.dates.modified;
  $('#install-section').hidden = !item.installation.length;
  item.metadata.forEach((field) => {
    const value = node('dd', field.value);
    value.lang = target === 'pt' ? 'pt-BR' : target;
    $('#facts').append(node('dt', labels[field.label.toLowerCase()] || field.label), value);
  });
  const dates = [];
  if (item.dates.published) dates.push(`Publicação da página: ${item.dates.published}`);
  if (item.dates.modified) dates.push(`Atualização da página: ${item.dates.modified}`);
  $('#page-dates').textContent = dates.join(' · ');
  item.installation.forEach((section) => {
    const container = node('div'); container.append(node('h3', section.title || 'Instruções da fonte'));
    section.blocks.forEach((block) => {
      if (block.kind === 'list') {
        const list = node('ul', undefined, 'install-block source-list');
        block.items.forEach((text) => list.append(node('li', text)));
        container.append(list);
      } else container.append(node('p', block.text, 'install-block'));
      addLinks(container, block.links);
    });
    $('#installation').append(container);
  });
}
const translationErrors = {
  libretranslate_unavailable:'LibreTranslate indisponível. Inicie o serviço local na porta 5000 e aguarde o carregamento dos idiomas.',
  ollama_unavailable:'Ollama indisponível. Inicie o Ollama e instale o modelo local escolhido.',
  local_model_required:'Escolha um modelo instalado localmente. Modelos remotos não são permitidos neste modo.',
  changed_technical_tokens:'A tradução alterou dados técnicos protegidos e foi descartada. O original foi mantido.',
  translation_too_long:'Esta ficha excede o limite de tradução de 16.000 caracteres ou 160 trechos. O original foi mantido.',
  invalid_translation:'A tradução não pôde ser validada. O original foi mantido.'
};
window.addEventListener('vstworld:language', (event) => {
  if (!showingTranslation && !$('#translate-item').disabled) $('#translation-target').value = event.detail.language;
});
$('#show-original').addEventListener('click', () => {
  if (!sourceItem) return;
  renderText(activeOriginal || sourceItem);
  showingTranslation = false;
  $('#translation-status').textContent = 'Original da fonte.';
  $('#show-original').disabled = true;
});
$('#translate-item').addEventListener('click', async () => {
  if (!sourceItem) return;
  const target = $('#translation-target').value;
  const model = $('#translation-model').value.trim();
  const provider = $('#translation-provider').value;
  const key = JSON.stringify([target, provider, provider === 'local' ? model : '']);
  const controls = ['#translate-item','#show-original','#translation-target','#translation-model','#translation-provider'];
  controls.forEach((selector) => { $(selector).disabled = true; });
  $('#translation-status').textContent = 'Traduzindo os textos da ficha… Isso pode levar alguns minutos.';
  try {
    let result = translatedItems.get(key);
    if (!result) {
      const response = await fetch('/api/translate', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ref, target, provider, model: model || 'qwen3.5:4b'})});
      result = await response.json();
      if (!response.ok) throw new Error(translationErrors[result.error] || result.detail || translationErrors.invalid_translation);
      translatedItems.set(key, result);
    }
    activeOriginal = result.original;
    renderText(result.item, result.target);
    showingTranslation = true;
    $('#translation-status').textContent = 'Tradução automática. Confira as instruções e os dados técnicos com o original antes de usá-los.';
  } catch (error) {
    renderText(activeOriginal || sourceItem);
    showingTranslation = false;
    $('#translation-status').textContent = error.message;
  } finally {
    controls.forEach((selector) => { $(selector).disabled = false; });
    $('#show-original').disabled = !showingTranslation;
  }
});
async function initialize() {
  const back = new URLSearchParams(location.search).get('back');
  if (back === '/' || back?.startsWith('/?')) $('#back').href = back;
  try {
    const item = await api('/api/details');
    sourceItem = item;
    renderText(item);
    show('#translation-panel');
    $('#translation-target').value = window.VSTI18n?.language || 'pt';
    document.title = `${item.title || 'Detalhes'} — VSTWorld`;
    $('#item-title').textContent = item.title || 'Detalhes do item';
    $('#item-source').textContent = item.source;
    $('#item-status').textContent = 'Dados extraídos da página original, sem o texto promocional.';
    if (item.images.length) {
      show('#gallery-section');
      item.images.forEach((image, index) => {
        const button = node('button'); button.type = 'button';
        const thumbnail = node('img'); thumbnail.src = image.thumbnail; thumbnail.alt = `Screenshot ${index + 1}`; thumbnail.loading = 'lazy';
        button.append(thumbnail, node('span', `Ampliar screenshot ${index + 1}`), node('small', image.original_available ? 'Link de imagem identificado' : 'Resolução original será verificada ao abrir'));
        button.addEventListener('click', () => imageViewer(image, thumbnail));
        $('#gallery').append(button);
      });
    }
    const videos = item.videos.filter((video) => /^[A-Za-z0-9_-]{11}$/.test(video.id));
    if (videos.length) {
      show('#videos-section');
      videos.forEach((video, index) => {
        const container = node('div', undefined, 'video');
        const button = node('button', `Reproduzir vídeo ${index + 1} do YouTube`); button.type = 'button';
        button.addEventListener('click', () => {
          const iframe = node('iframe'); iframe.src = `https://www.youtube-nocookie.com/embed/${video.id}?autoplay=1`;
          iframe.referrerPolicy = 'strict-origin-when-cross-origin';
          iframe.title = `Vídeo ${index + 1} do item`; iframe.allow = 'autoplay; encrypted-media; picture-in-picture'; iframe.allowFullscreen = true;
          container.replaceChildren(iframe);
        });
        container.append(button); $('#videos').append(container);
      });
    }
    if (item.notices.length) { show('#notices-section'); item.notices.forEach((text) => $('#notices').append(node('li', text))); }
    $('#attribution').append(document.createTextNode('Conteúdo de '), link(item.source_url, item.source + ' — página original'));
    show('#downloads-section'); downloads();
  } catch (error) { $('#item-title').textContent = 'Não foi possível abrir o item'; $('#item-status').textContent = error.message; }
}
initialize();
