"""Reproduz somente o pedido JSON de download observado no Plugins4Free."""
import json
import re

import httpx


CALL = re.compile(r'''^\s*startDownload\(\s*event\s*,\s*['"]?(\d{1,10})['"]?\s*,\s*['"]([^'"\\\r\n]{1,250})['"]\s*\)\s*;?\s*$''')
TOKEN = re.compile(r'''['"]X-CSRF-TOKEN['"]\s*:\s*['"]([^'"\\\r\n]{8,256})['"]''')


async def download_links(catalog, source, nodes, body):
    token = TOKEN.search(body.decode('utf-8', errors='replace'))
    if not token:
        return [], ['Não foi possível identificar o código temporário de download do Plugins4Free.']
    links, notices, seen = [], [], set()
    for node in nodes[:10]:
        call = CALL.fullmatch(node.get('onclick', ''))
        if not call or call.groups() in seen:
            continue
        seen.add(call.groups())
        try:
            response, content = await catalog.fetch(source, catalog.url(source, '/download'), method='POST',
                json_body={'plugin_id': int(call[1]), 'filename': call[2]},
                request_headers={'X-CSRF-TOKEN': token[1], 'Accept': 'application/json'},
                content_types=('application/json',))
            response.raise_for_status()
            payload = json.loads(content)
            if not isinstance(payload, dict) or not isinstance(payload.get('url'), str):
                raise ValueError('Resposta sem endereço')
            links.append({'href': catalog.url(source, payload['url'])})
        except (ValueError, httpx.HTTPError):
            notices.append('O Plugins4Free não disponibilizou um endereço de arquivo válido nesta tentativa.')
    if not links and not notices:
        notices.append('O formato dos botões de download do Plugins4Free não foi reconhecido.')
    return links, notices
