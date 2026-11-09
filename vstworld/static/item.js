'use strict';
const $ = (selector) => document.querySelector(selector);
const ref = location.pathname.split('/').pop();
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
    value.files.forEach((file) => $('#files').append(link(file.url, `${file.kind.toUpperCase()} · ${file.name}`, 'file-link')));
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
async function initialize() {
  const back = new URLSearchParams(location.search).get('back');
  if (back === '/' || back?.startsWith('/?')) $('#back').href = back;
  try {
    const item = await api('/api/details');
    document.title = `${item.title || 'Detalhes'} — VSTWorld`;
    $('#item-title').textContent = item.title || 'Detalhes do item';
    $('#item-source').textContent = item.source;
    $('#item-status').textContent = 'Dados extraídos da página original, sem o texto promocional.';
    if (item.metadata.length) {
      show('#facts-section');
      item.metadata.forEach((field) => $('#facts').append(node('dt', labels[field.label.toLowerCase()] || field.label), node('dd', field.value)));
    }
    const dates = [];
    if (item.dates.published) dates.push(`Publicação da página: ${item.dates.published}`);
    if (item.dates.modified) dates.push(`Atualização da página: ${item.dates.modified}`);
    if (dates.length) { show('#facts-section'); $('#page-dates').textContent = dates.join(' · '); }
    if (item.installation.length) {
      show('#install-section');
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
