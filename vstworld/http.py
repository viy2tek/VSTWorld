"""HTTPS público com DNS fixado por conexão, mantendo Host e validação TLS."""
import asyncio
import ipaddress
import socket

import httpx


def public_url(value: str) -> httpx.URL:
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as exc:
        raise ValueError('URL inválida') from exc
    if (url.scheme != 'https' or not url.host or url.username or url.password
            or url.port not in (None, 443) or url.fragment):
        raise ValueError('Use HTTPS público, sem credenciais, fragmento ou porta alternativa')
    if url.host.rstrip('.').endswith(('.local', '.localhost', '.internal')) or url.host.rstrip('.') == 'localhost':
        raise ValueError('Destino local não permitido')
    try:
        address = ipaddress.ip_address(url.host)
    except ValueError:
        return url
    if not address.is_global or getattr(address, 'ipv4_mapped', None):
        raise ValueError('IP não público')
    return url


class PublicTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.transport = httpx.AsyncHTTPTransport(
            trust_env=False, retries=0, limits=httpx.Limits(max_keepalive_connections=0))

    async def handle_async_request(self, request):
        url = public_url(str(request.url))
        addresses = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(
            url.host, 443, type=socket.SOCK_STREAM), timeout=10)
        ips = sorted({item[4][0] for item in addresses})
        if not ips:
            raise ValueError('DNS sem endereço público')
        for address in ips:
            public_url(f'https://[{address}]/' if ':' in address else f'https://{address}/')
        # Conectar ao IP validado impede uma segunda resolução de DNS na conexão.
        pinned = httpx.Request(request.method, url.copy_with(host=ips[0]),
                               headers=request.headers, stream=request.stream,
                               extensions={**request.extensions, 'sni_hostname': url.host})
        pinned.headers['Host'] = url.netloc.decode()
        pinned.headers['Connection'] = 'close'
        return await self.transport.handle_async_request(pinned)

    async def aclose(self):
        await self.transport.aclose()
