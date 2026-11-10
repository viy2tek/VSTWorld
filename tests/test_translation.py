from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import httpx

from vstworld.translation import translate_item, TranslationError, shield, restore


ITEM = {'title':'Brand Plugin v1.2.3', 'source':'Source', 'source_url':'https://source.example/item',
    'metadata':[{'label':'Разработчик','value':'Brand'}, {'label':'Версия','value':'1.2.3'},
                {'label':'Требования','value':'Установите Windows 10 x64.'}],
    'installation':[{'title':'Установка','blocks':[{'kind':'list','items':['Откройте setup.exe.', 'Требуется 2 GB.'],
        'links':[{'url':'https://source.example/setup.exe','label':'Инструкция'}]}]}],
    'images':[{'url':'https://source.example/picture.jpg'}], 'videos':[{'id':'abcdefghijk'}],
    'dates':{'published':'2026-11-09','modified':None}}


class TranslationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls=[]

    def transport(self, invalid=None, info=None, truncated=False, redirect=False):
        def handler(request):
            self.calls.append(request)
            self.assertEqual(str(request.url).split('/api')[0],'http://127.0.0.1:11434')
            if redirect:
                return httpx.Response(302,headers={'location':'https://elsewhere.example'})
            if request.url.path=='/api/show':
                return httpx.Response(200,json=info if info is not None else {'model_info':{'general.architecture':'qwen'}})
            payload=json.loads(request.content)
            self.assertFalse(payload['stream'])
            self.assertEqual(payload['format']['additionalProperties'],False)
            lines=json.loads(payload['prompt'])
            for line in lines['texts']:
                line['text']=invalid if invalid is not None else 'Translated: '+line['text']
            return httpx.Response(200,json={'done':True,'done_reason':'length' if truncated else 'stop','response':json.dumps(lines)})
        return httpx.MockTransport(handler)

    async def test_changes_only_eligible_text_and_preserves_original(self):
        before=deepcopy(ITEM)
        result=await translate_item(ITEM,'es',transport=self.transport())
        self.assertEqual(ITEM,before)
        for key in ('title','source','source_url','images','videos','dates'):
            self.assertEqual(result[key],ITEM[key])
        self.assertEqual(result['metadata'][:2],ITEM['metadata'][:2])
        self.assertIn('Windows 10 x64',result['metadata'][2]['value'])
        self.assertIn('setup.exe',result['installation'][0]['blocks'][0]['items'][0])
        self.assertEqual(result['installation'][0]['blocks'][0]['links'][0]['url'],ITEM['installation'][0]['blocks'][0]['links'][0]['url'])
        sent=''.join(r.content.decode() for r in self.calls if r.url.path=='/api/generate')
        self.assertNotIn('https://source.example/setup.exe',sent)
        self.assertNotIn('Brand Plugin',sent)

    async def test_unavailable_ollama_is_reported(self):
        def unavailable(request):
            raise httpx.ConnectError('offline',request=request)
        with self.assertRaises(TranslationError) as caught:
            await translate_item(ITEM,'pt',transport=httpx.MockTransport(unavailable))
        self.assertEqual(caught.exception.code,'ollama_unavailable')

    async def test_changed_numbers_or_tokens_rejected_atomically(self):
        for value in ('Translated 999','Translated without protected data'):
            original=deepcopy(ITEM)
            with self.assertRaises(TranslationError):
                await translate_item(ITEM,'en',transport=self.transport(invalid=value))
            self.assertEqual(ITEM,original)

    async def test_unsupported_language_is_rejected_before_request(self):
        with self.assertRaises(TranslationError):
            await translate_item(ITEM,'xx',transport=self.transport())
        self.assertEqual(self.calls,[])

    async def test_remote_identifiers_blocked_before_request(self):
        for model in ('qwen:cloud','https://example.com/model',''):
            with self.assertRaises(TranslationError):
                await translate_item(ITEM,'en',model=model,transport=self.transport())
        self.assertEqual(self.calls,[])

    async def test_remote_backing_and_truncation_rejected(self):
        with self.assertRaises(TranslationError):
            await translate_item(ITEM,'pt',transport=self.transport(info={'remote_host':'https://cloud.example','model_info':{'general.architecture':'qwen'}}))
        self.assertFalse(any(r.url.path=='/api/generate' for r in self.calls))
        with self.assertRaises(TranslationError):
            await translate_item(ITEM,'pt',transport=self.transport(truncated=True))

    async def test_size_bound_and_redirect_rejected(self):
        large=deepcopy(ITEM)
        large['installation'][0]['blocks'][0]['items']=['a'*16001]
        with self.assertRaises(TranslationError):
            await translate_item(large,'es',transport=self.transport())
        self.assertEqual(self.calls,[])
        with self.assertRaises(TranslationError):
            await translate_item(ITEM,'es',transport=self.transport(redirect=True))
        self.assertTrue(all(r.url.host=='127.0.0.1' for r in self.calls))

    def test_tokens_exact_and_not_duplicated(self):
        value,mapping=shield('Build 1.2.3: https://source.example/file.zip (64 bits)')
        self.assertEqual(restore(value,mapping),'Build 1.2.3: https://source.example/file.zip (64 bits)')
        token=next(iter(mapping))
        with self.assertRaises(TranslationError): restore(value+token,mapping)

    async def test_libretranslate_keeps_tokens_outside_translator(self):
        def handler(request):
            self.assertEqual(str(request.url), 'http://127.0.0.1:5000/translate')
            payload = json.loads(request.content)
            self.assertEqual(payload['source'], 'auto')
            self.assertEqual(payload['target'], 'pt')
            self.assertEqual(payload['format'], 'text')
            self.assertLessEqual(len(payload['q']), 6)
            self.assertNotIn('__VW_KEEP_', request.content.decode())
            self.assertNotIn('setup.exe', request.content.decode())
            return httpx.Response(200, json={'translatedText': ['Traduzido: '+text for text in payload['q']]})
        before = deepcopy(ITEM)
        result = await translate_item(ITEM, 'pt', provider='libretranslate', transport=httpx.MockTransport(handler))
        self.assertEqual(ITEM, before)
        self.assertEqual(result['metadata'][:2], ITEM['metadata'][:2])
        self.assertIn('Windows 10 x64', result['metadata'][2]['value'])
        self.assertIn('setup.exe', result['installation'][0]['blocks'][0]['items'][0])
        self.assertEqual(result['images'], ITEM['images'])

    async def test_libretranslate_invalid_and_redirect_rejected(self):
        for response in (httpx.Response(200, json={'translatedText': ['incomplete']}),
                         httpx.Response(302, headers={'location': 'https://elsewhere.example'}),
                         httpx.Response(400, json={'error': 'language unavailable'})):
            calls = []
            def handler(request):
                calls.append(request)
                return response
            with self.assertRaises(TranslationError):
                await translate_item(ITEM, 'es', provider='libretranslate', transport=httpx.MockTransport(handler))
            self.assertEqual(len(calls), 1)

    async def test_libretranslate_connection_failure(self):
        def handler(request):
            raise httpx.ConnectError('offline', request=request)
        with self.assertRaises(TranslationError) as caught:
            await translate_item(ITEM, 'pt', provider='libretranslate', transport=httpx.MockTransport(handler))
        self.assertEqual(caught.exception.code, 'libretranslate_unavailable')
