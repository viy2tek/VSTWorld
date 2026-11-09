from copy import deepcopy
import json
import os
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
    def deepl(self, calls, invalid=None, status=200):
        def handler(request):
            calls.append(request)
            payload=json.loads(request.content)
            self.assertEqual(request.url.host,'api-free.deepl.com')
            self.assertEqual(request.headers['authorization'],'DeepL-Auth-Key test:fx')
            self.assertEqual(payload['target_lang'],'ES')
            values=[invalid if invalid is not None else 'Traducido: '+text for text in payload['text']]
            return httpx.Response(status,json={'translations':[{'text':text} for text in values]})
        return httpx.MockTransport(handler)

    async def test_online_changes_only_translatable_text_and_preserves_original(self):
        calls=[]
        before=deepcopy(ITEM)
        with patch.dict(os.environ,{'VSTWORLD_DEEPL_API_KEY':'test:fx'}):
            result=await translate_item(ITEM,'es','deepl',transport=self.deepl(calls))
        self.assertEqual(ITEM,before)
        for key in ('title','source','source_url','images','videos','dates'):
            self.assertEqual(result[key],ITEM[key])
        self.assertEqual(result['metadata'][:2],ITEM['metadata'][:2])
        self.assertIn('Windows 10 x64',result['metadata'][2]['value'])
        self.assertIn('setup.exe',result['installation'][0]['blocks'][0]['items'][0])
        self.assertEqual(result['installation'][0]['blocks'][0]['links'][0]['url'],ITEM['installation'][0]['blocks'][0]['links'][0]['url'])
        self.assertTrue(calls)
        sent=calls[0].content.decode()
        self.assertNotIn('https://source.example/setup.exe',sent)
        self.assertNotIn('Brand Plugin',sent)

    async def test_online_requires_key_without_sending_anything(self):
        calls=[]
        with patch.dict(os.environ,{'VSTWORLD_DEEPL_API_KEY':''}), self.assertRaises(TranslationError) as caught:
            await translate_item(ITEM,'es','deepl',transport=self.deepl(calls))
        self.assertEqual(caught.exception.code,'deepl_not_configured')
        self.assertEqual(calls,[])

    async def test_altered_numbers_or_placeholders_are_rejected_atomically(self):
        for value in ('Translated 999', 'Translated without protected data'):
            original=deepcopy(ITEM)
            with patch.dict(os.environ,{'VSTWORLD_DEEPL_API_KEY':'test:fx'}), self.assertRaises(TranslationError):
                await translate_item(ITEM,'es','deepl',transport=self.deepl([],invalid=value))
            self.assertEqual(ITEM,original)

    async def test_quota_and_unsupported_language(self):
        with patch.dict(os.environ,{'VSTWORLD_DEEPL_API_KEY':'test:fx'}), self.assertRaises(TranslationError) as caught:
            await translate_item(ITEM,'es','deepl',transport=self.deepl([],status=456))
        self.assertEqual(caught.exception.code,'deepl_quota')
        with self.assertRaises(TranslationError):
            await translate_item(ITEM,'xx','deepl')

    async def test_local_validates_model_and_schema(self):
        calls=[]
        def handler(request):
            self.assertEqual(str(request.url).split('/api')[0],'http://127.0.0.1:11434')
            calls.append(request)
            if request.url.path=='/api/show':
                return httpx.Response(200,json={'model_info':{'general.architecture':'qwen'}})
            payload=json.loads(request.content)
            self.assertFalse(payload['stream'])
            self.assertEqual(payload['format']['additionalProperties'],False)
            lines=json.loads(payload['prompt'])
            for line in lines['texts']:
                line['text']='Translated: '+line['text']
            return httpx.Response(200,json={'done':True,'response':json.dumps(lines)})
        result=await translate_item(ITEM,'en','local',transport=httpx.MockTransport(handler))
        self.assertTrue(result['installation'][0]['title'].startswith('Translated:'))
        self.assertEqual(result['title'],ITEM['title'])
        with self.assertRaises(TranslationError):
            await translate_item(ITEM,'en','local',model='qwen:cloud',transport=httpx.MockTransport(handler))

    async def test_local_remote_backing_and_truncation_are_rejected(self):
        for data in ({'remote_host':'https://cloud.example','model_info':{'general.architecture':'qwen'}},
                     {'model_info':{'general.architecture':'qwen'}}):
            def handler(request):
                if request.url.path=='/api/show': return httpx.Response(200,json=data)
                return httpx.Response(200,json={'done':True,'done_reason':'length','response':'{}'})
            with self.assertRaises(TranslationError):
                await translate_item(ITEM,'pt','local',transport=httpx.MockTransport(handler))

    async def test_bound_before_request_and_redirect_rejected(self):
        large=deepcopy(ITEM)
        large['installation'][0]['blocks'][0]['items']=['a'*16001]
        calls=[]
        with self.assertRaises(TranslationError):
            await translate_item(large,'es','deepl',transport=self.deepl(calls))
        self.assertEqual(calls,[])
        with patch.dict(os.environ,{'VSTWORLD_DEEPL_API_KEY':'test:fx'}), self.assertRaises(TranslationError):
            await translate_item(ITEM,'es','deepl',transport=httpx.MockTransport(lambda request:httpx.Response(302,headers={'location':'https://elsewhere.example'})))

    def test_tokens_are_exact_and_not_duplicated(self):
        value,mapping=shield('Build 1.2.3: https://source.example/file.zip (64 bits)')
        self.assertEqual(restore(value,mapping),'Build 1.2.3: https://source.example/file.zip (64 bits)')
        token=next(iter(mapping))
        with self.assertRaises(TranslationError): restore(value+token,mapping)
