"""Controlled SDK/reader fixtures; never a live model quality benchmark."""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conversation_persona import classify_model_task
from verified_research import research_for_chat

class GroundingRegressionTests(unittest.TestCase):
    def test_current_questions_route_without_requiring_research_verb(self):
        for text in ['Bugün dolar kaç TL?', 'En son teknoloji haberleri neler?',
                     'What is the current EUR exchange rate?', 'Bugünkü maç sonucu ne?',
                     'iPhone 17 güncel fiyatı ne kadar?']:
            with self.subTest(text=text):
                self.assertEqual(classify_model_task(text), 'RESEARCH')

    def test_stable_chat_does_not_open_search(self):
        for text in ['Merhaba', 'Döviz kuru nedir?', 'Python nedir?',
                     'Bugün çok yoruldum', '2 kere 7 kaç?', 'Kodumu düzelt']:
            self.assertNotEqual(classify_model_task(text), 'RESEARCH')

    def test_private_email_does_not_reach_search(self):
        engine = Mock()
        result = asyncio.run(research_for_chat('Araştır: bana ait adres murat@example.org', engine_factory=lambda: engine))
        self.assertEqual(result['status'], 'research_blocked_sensitive_input')
        engine.research.assert_not_called()

    def test_secret_after_query_limit_cannot_be_truncated_away(self):
        engine = Mock()
        result = asyncio.run(research_for_chat('Araştır: '+ 'public ' * 180 + 'API key sk-proj-12345678901234567890', engine_factory=lambda: engine))
        self.assertEqual(result['status'], 'research_blocked_sensitive_input')
        engine.research.assert_not_called()

from grounded_search import google_search, parse_grounding, provider_failure, public_citation_url
from ultron.backend.app.cognitive.research_context import research_message_for_turn

def sdk_response(text='Güncel değer 42 TL.', url='https://example.org/report', widget=''):
    return N(candidates=[N(content=N(parts=[N(text=text)]),grounding_metadata=N(
        grounding_chunks=[N(web=N(uri=url,title='Resmî rapor'))],
        grounding_supports=[N(segment=N(start_index=0,end_index=len(text.encode()),text=text),grounding_chunk_indices=[0])],
        search_entry_point=N(rendered_content=widget)))],
        usage_metadata=N(prompt_token_count=12,candidates_token_count=18,total_token_count=30))

class SDKContractTests(unittest.TestCase):
    def test_official_camel_case_json_and_sdk_objects_both_supported(self):
        result=parse_grounding(sdk_response(),model='configured-model')
        self.assertEqual(result['status'],'google_grounded')
        self.assertEqual(result['citations'],['https://example.org/report'])
        self.assertFalse(result['sources'][0]['page_read'])
        self.assertIsNone(result['sources'][0]['published_at'])
        self.assertEqual(result['sources'][0]['supports'],['Güncel değer 42 TL.'])
        response={'candidates':[{'content':{'parts':[{'text':'USD 42.'}]},'groundingMetadata':{
            'groundingChunks':[{'web':{'uri':'https://example.org/fx','title':'FX'}}],
            'groundingSupports':[{'segment':{'startIndex':0,'endIndex':7,'text':'USD 42.'},'groundingChunkIndices':[0]}]}}]}
        self.assertTrue(parse_grounding(response,model='configured')['ok'])

    def test_missing_or_invalid_support_is_not_success(self):
        for bad in ('missing','wrong_text','bad_index','split_utf8','private_url'):
            response=sdk_response()
            meta=response.candidates[0].grounding_metadata
            if bad=='missing': meta.grounding_supports=[]
            if bad=='wrong_text': meta.grounding_supports[0].segment.text='Fabricated evidence'
            if bad=='bad_index': meta.grounding_supports[0].grounding_chunk_indices=[99]
            if bad=='split_utf8': meta.grounding_supports[0].segment.end_index=2
            if bad=='private_url': meta.grounding_chunks[0].web.uri='http://169.254.169.254/latest'
            with self.subTest(bad=bad): self.assertFalse(parse_grounding(response,model='m')['ok'])

    def test_fabricated_urls_are_not_promoted_to_citations(self):
        result=parse_grounding(sdk_response('See https://invented.example/fake for a price.'),model='m')
        # The provider-attributed quote remains labelled as a quote, not a new citation.
        self.assertEqual(result['citations'],['https://example.org/report'])
        self.assertIn('[kaynak doğrulanmadı]',result['answer'])

    def test_no_unsupported_independent_verification_or_date(self):
        result=parse_grounding(sdk_response(),model='m')
        self.assertFalse(result['independent_verification'])
        self.assertEqual(result['confidence'],0)
        self.assertIn('yayın tarihi: kaynak metadatasında yok',result['answer'])

    def test_widget_drops_active_markup_and_private_links(self):
        result=parse_grounding(sdk_response(widget='<script>steal()</script><meta http-equiv="refresh" content="0;url=http://127.0.0.1"><a href="javascript:alert(1)" onclick="steal()">bad</a><a href="https://www.google.com/search?q=cpu">Google</a>'),model='m')
        widget=result['search_suggestions_html']
        for bad in ['script','meta','javascript','onclick','127.0.0.1']: self.assertNotIn(bad,widget)
        self.assertIn('https://www.google.com/search?q=cpu',widget)

    def test_budget_disabled_key_missing_and_model_missing_make_no_call(self):
        for env,status in [({},'grounding_disabled'),
            ({'GOLGE_GOOGLE_SEARCH_ENABLED':'true'},'grounding_budget_not_approved'),
            ({'GOLGE_GOOGLE_SEARCH_ENABLED':'true','GOLGE_GOOGLE_SEARCH_BUDGET_APPROVED':'true'},'grounding_model_not_configured')]:
            factory=Mock()
            with patch.dict(os.environ,env,clear=True): result=google_search('public news',client_factory=factory)
            self.assertEqual(result['status'],status); factory.assert_not_called()

    def test_quota_fallback_preserves_query_and_has_two_total_attempts(self):
        client=Mock();client.models.generate_content.side_effect=[RuntimeError('429 private body'),sdk_response()]
        factory=Mock(return_value=client)
        env={'GOLGE_GOOGLE_SEARCH_ENABLED':'true','GOLGE_GOOGLE_SEARCH_BUDGET_APPROVED':'true',
             'GEMINI_SEARCH_MODEL':'primary','GEMINI_SEARCH_FALLBACK_MODEL':'backup'}
        with patch.dict(os.environ,env,clear=True): result=google_search('Güncel ürün fiyatı',client_factory=factory)
        self.assertTrue(result['ok']);self.assertEqual(result['model'],'backup')
        self.assertEqual(len(result['attempts']),2)
        for call in client.models.generate_content.call_args_list:
            self.assertEqual(call.kwargs['contents'],'Güncel ürün fiyatı')
            self.assertEqual(len(call.kwargs['config'].tools),1)
            self.assertIsNotNone(call.kwargs['config'].tools[0].google_search)
        self.assertEqual(factory.call_args.kwargs['http_options'].retry_options.attempts,1)
        client.close.assert_called_once()
        self.assertNotIn('private body',str(result))

    def test_auth_failure_does_not_walk_fallback(self):
        client=Mock();client.models.generate_content.side_effect=RuntimeError('403 PERMISSION_DENIED private')
        env={'GOLGE_GOOGLE_SEARCH_ENABLED':'true','GOLGE_GOOGLE_SEARCH_BUDGET_APPROVED':'true',
             'GEMINI_SEARCH_MODEL':'primary','GEMINI_SEARCH_FALLBACK_MODEL':'backup'}
        with patch.dict(os.environ,env,clear=True): result=google_search('public news',client_factory=lambda **kw:client)
        self.assertFalse(result['ok']);self.assertEqual(client.models.generate_content.call_count,1)

    def test_distinct_safe_failure_categories(self):
        for status,want in [(429,'quota_exhausted'),(403,'access_denied'),(404,'model_not_found'),(504,'timeout'),(503,'service_unavailable'),(400,'invalid_request')]:
            exc=RuntimeError('private prompt');exc.code=status
            self.assertEqual(provider_failure(exc),want)
        self.assertEqual(provider_failure(ConnectionError()),'network_unavailable')

    def test_private_user_history_never_becomes_search_query(self):
        turns=[{'role':'user','content':'Araştır: yeni pil teknolojileri'},
               {'role':'assistant','content':'api key sk-proj-PRIVATE'}]
        self.assertEqual(research_message_for_turn('Araştırmaya devam et',turns),'yeni pil teknolojileri. Araştırmaya devam et')
        turns.append({'role':'user','content':'Başka konuya geç, özel aile konum'})
        self.assertIsNone(research_message_for_turn('Araştırmaya devam et',turns))

    def test_normal_followup_and_tool_requests_never_auto_search(self):
        for text in ['Devam et','Chrome aç','Dosyayı sil','Dünya göster','Dün ne demiştim?']:
            self.assertIsNone(research_message_for_turn(text))

    def test_url_protocol_userinfo_and_private_ip_are_rejected(self):
        for url in ['file:///etc/passwd','javascript:alert(1)','http://127.0.0.1','http://169.254.169.254','https://user:pass@example.org','http://localhost','http://example.org:8080/x']:
            self.assertIsNone(public_citation_url(url))

class ModelRoutingTests(unittest.TestCase):
    def test_programming_conversation_is_not_a_code_generation_job(self):
        for text in ['Python nedir?', 'Python öğreniyorum', 'What is Python commonly used for?']:
            self.assertEqual(classify_model_task(text),'FAST')
        for text in ['Python fonksiyon yaz', 'Write Python code to parse JSON', 'Refactor this Python function']:
            self.assertEqual(classify_model_task(text),'CODING')

    def test_text_fallback_is_bounded_and_preserves_context(self):
        import app as cloud
        client=Mock();turns=[{'role':'user','content':'prior goal'}]
        env={'GEMINI_MODEL':'primary','GEMINI_FALLBACK_MODEL':'backup','GEMINI_MAX_RETRIES':'5','GEMINI_API_KEY':'fixture'}
        with patch.dict(os.environ,env), patch.object(cloud.genai,'Client',return_value=client), \
             patch.object(cloud,'_generate_with_model',side_effect=[RuntimeError('429'), 'yanıt']) as generate:
            self.assertEqual(cloud._gemini_reply('devam et','GÖLGE policy',turns,include_model=True),('yanıt','backup'))
            self.assertEqual(generate.call_count,2)
            for call in generate.call_args_list:
                self.assertIs(call.kwargs['turns'],turns)
                self.assertEqual(call.args[3],'GÖLGE policy')
        client.close.assert_called_once()

    def test_no_search_if_sensitive_or_tool_request(self):
        for text in ['API key sk-proj-12345678901234567890', 'My email is person@example.org']:
            factory=Mock()
            self.assertEqual(google_search(text,client_factory=factory)['status'],'research_blocked_sensitive_input')
            factory.assert_not_called()


class ResearchContinuationTests(unittest.TestCase):
    def test_multiple_bilingual_followups_reuse_query_without_assistant_text(self):
        turns = [{'role':'user','content':'Araştır: yeni pil teknolojileri'},
                 {'role':'assistant','content':'UNTRUSTED_PRIVATE_PROFILE'}]
        for followup in ('Araştırmaya devam et','Kaynakları karşılaştır','Continue research','Compare the sources'):
            resolved = research_message_for_turn(followup, turns)
            self.assertTrue(resolved.startswith('yeni pil teknolojileri.'))
            self.assertNotIn('UNTRUSTED_PRIVATE_PROFILE', resolved)
            turns.append({'role':'user','content':followup})

    def test_no_topic_does_not_search_for_literal_compare_sources(self):
        self.assertIsNone(research_message_for_turn('Kaynakları karşılaştır'))
        factory = Mock()
        result = asyncio.run(research_for_chat('Kaynakları karşılaştır',engine_factory=factory))
        self.assertEqual(result['status'], 'research_topic_missing')
        factory.assert_not_called()
