"""Regression tests at the real MARK-to-ULTRON process boundary."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import pytest
from integration.paths import ROOT, BACKEND
from integration.launcher import Services, stop_process
from integration.bridge import Bridge


def load_file(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

wake=load_file('merged_wake_test',BACKEND/'app/voice/wake.py')
router_module=load_file('merged_router_test',BACKEND/'app/core/model_router.py')

@pytest.mark.parametrize('exists',[False,True])
def test_wake_fields_always_initialized(tmp_path,exists):
    directory=tmp_path if exists else tmp_path/'missing'
    engine=wake.OpenWakeWordEngine(directory)
    assert engine.models==[]
    assert engine._model is None
    assert engine.available is False
    assert engine.status()['error']
    engine.stop()


def test_custom_wake_preferred(tmp_path,monkeypatch):
    monkeypatch.setenv('ULTRON_WAKE_MODEL','ultron')
    for name in ('ultron.onnx','other_keyword.onnx'):
        (tmp_path/name).write_bytes(b'file-presence-fixture')
    engine=wake.OpenWakeWordEngine(tmp_path)
    assert [m.name for m in engine.models]==['ultron.onnx']

@pytest.mark.parametrize('models',[
    ['qwen2.5-coder:7b','qwen3:4b','qwen3:8b','llava:7b'],
    ['qwen2.5-coder:7b'],['general:7b'],['other:small','another:small']])
def test_router_never_selects_absent_configured_model(models):
    class Brain:
        model='not-installed:7b'
    router=router_module.ModelRouter(Brain(),{'llm':{'routing':{'coding':'missing:7b'}}},lambda:models)
    for task in ('GENERAL','CODING','VISION','FAST'):
        assert router.resolve(task) in models


def test_ollama_offline_bounded_attempts():
    class Brain:
        model='missing:7b'
        def __init__(self):self.calls=0
        def ask(self,*args,**kwargs):
            self.calls+=1
            raise RuntimeError('offline')
    brain=Brain()
    router=router_module.ModelRouter(brain,{},lambda:[],sleep=lambda _:None)
    with pytest.raises(RuntimeError,match='offline'):router.ask('GENERAL','hello')
    assert brain.calls==1


def test_mark_core_preserved():
    # Core voice/UI implementations remain available in the MARK namespace.
    result=subprocess.run([sys.executable,'-m','integration.doctor','--probe','MARK imports'],cwd=ROOT,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr


def test_missing_bridge_fails_promptly():
    with pytest.raises(RuntimeError):Bridge(url='',token='').health()


def test_owned_child_cleanup():
    process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
    stop_process(process)
    assert process.poll() is not None

@pytest.fixture(scope='module')
def service():
    with Services() as s:
        s.start()
        yield s
    assert s.backend.poll() is not None


def test_http_health_and_core_components(service):
    health=service.bridge.health()
    assert health['ok'] and all(health['components'].values())
    assert health['audio_owner']=='mark'


def test_service_rejects_bad_token(service):
    with pytest.raises(urllib.error.HTTPError) as exc:
        Bridge(service.bridge.url,'bad-token').health()
    assert exc.value.code==401


def test_browser_session_assets_and_csrf(service):
    from urllib.request import Request, urlopen
    url=service.bridge.url
    with urlopen(Request(url+'/api/merged/session',data=b'',headers={'X-MARK-Token':service.bridge.token})) as response:
        cookie=response.headers['Set-Cookie']
        assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
    headers={'Cookie':cookie.split(';')[0]}
    for surface in ('frontend/index.html', 'merged/dashboard'):
        with urlopen(Request(url+'/'+surface, headers=headers)) as response:
            assert response.status == 200
    for surface in ('frontend-mobile/index.html',):
        with pytest.raises(urllib.error.HTTPError) as disabled:
            urlopen(Request(url+'/'+surface, headers=headers))
        assert disabled.value.code == 410
    with pytest.raises(urllib.error.HTTPError) as exc:
        urlopen(Request(url+'/api/merged/tool',data=b'{}',headers={**headers,'Origin':'https://untrusted.example'}))
    assert exc.value.code==401
    with pytest.raises(urllib.error.HTTPError):
        urlopen(Request(url+'/api/merged/tool',data=b'{}',headers=headers))
    payload=json.dumps({'name':'calculate','arguments':{'text':'2+3'}}).encode()
    with urlopen(Request(url+'/api/merged/tool',data=payload,headers={**headers,'Origin':url,'Content-Type':'application/json'})) as response:
        assert json.load(response)['result']==['5']


def test_microphone_cannot_be_claimed_by_backend(service):
    with pytest.raises(urllib.error.HTTPError) as exc:
        service.bridge.request('/api/voice/live',{'action':'start'})
    assert exc.value.code==409


def test_memory_roundtrip_through_mark_bridge(service):
    response=service.bridge.request('/api/memory/v16/add',{'kind':'TEST','text':'merged boundary roundtrip'})
    try:
        rows=service.bridge.request('/api/memory/v16')['rows']
        assert any(row['id']==response['id'] and row['content']=='merged boundary roundtrip' for row in rows)
    finally:
        assert service.bridge.request('/api/memory/v16/delete',{'id':response['id']})['ok']


def test_real_tool_execution_with_security_and_audit(service):
    result=service.bridge.request('/api/merged/tool',{'name':'calculate','arguments':{'text':'2+3'}})
    assert result['ok'] and result['result']==['5']


def test_caller_cannot_self_approve_write(service,tmp_path):
    path=tmp_path/'must-not-exist.txt'
    result=service.bridge.request('/api/merged/tool',{'name':'write_text','arguments':{'path':str(path),'content':'forbidden'},'approved':True})
    assert not result['ok']
    assert not path.exists()


def test_second_instance_does_not_spawn(service):
    with pytest.raises(RuntimeError,match='zaten'):
        with Services():
            pytest.fail('second instance acquired lock')


def test_plugin_reaches_real_backend(service,monkeypatch):
    monkeypatch.setenv('MARK_ULTRON_URL',service.bridge.url)
    monkeypatch.setenv('MARK_ULTRON_TOKEN',service.bridge.token)
    plugin=load_file('merged_plugin_test',ROOT/'plugins/ultron_capability.py')
    # Invalid mode proves a real HTTP roundtrip and an intelligible failure, no model dependency.
    assert '400' in plugin.run({'text':'test','mode':'invalid'})


def test_document_extracts_utf8_and_bounds_content(service):
    import base64
    text='Türkçe belge\n'+'a'*40000
    result=service.bridge.request('/api/merged/document',{'name':'belge.txt','data':base64.b64encode(text.encode()).decode()})
    assert result['ok'] and result['text']==text[:36000]


@pytest.mark.parametrize('name,data',[('bad.txt','%%%'),('empty.txt',''),('program.exe','aGVsbG8='),('broken.pdf','aGVsbG8=')])
def test_document_rejects_invalid_files(service,name,data):
    with pytest.raises(urllib.error.HTTPError) as exc:
        service.bridge.request('/api/merged/document',{'name':name,'data':data})
    assert exc.value.code==400


def test_unrelated_wake_model_is_not_ultron(tmp_path, monkeypatch):
    monkeypatch.setenv('ULTRON_WAKE_MODEL', 'ultron')
    (tmp_path/'other_keyword.onnx').write_bytes(b'fixture')
    engine = wake.OpenWakeWordEngine(tmp_path)
    assert not engine.available
    assert engine.models == []


def test_missing_custom_model_cannot_download_different_keyword(tmp_path, monkeypatch):
    from core import wake_word
    monkeypatch.setattr(wake_word, 'selected_model', lambda: str(tmp_path/'ultron.onnx'))
    ok, message = wake_word.install_and_download(logger=lambda _: None)
    assert not ok
    assert 'ULTRON' in message
    assert not wake_word.is_ready()


def test_hologram_is_available_without_alternate_desktop(service):
    from urllib.request import Request, urlopen
    headers = {'X-MARK-Token': service.bridge.token}
    with urlopen(Request(service.bridge.url+'/hologram/hologram.html',headers=headers)) as response:
        assert b'<title>ULTRON Hologram</title>' in response.read()
    with pytest.raises(urllib.error.HTTPError) as disabled:
        urlopen(Request(service.bridge.url+'/hologram/index.html',headers=headers))
    assert disabled.value.code == 404
    assets = list((ROOT/'ultron/frontend/dist/assets').glob('hand.worker-*.js'))
    assert assets
    with urlopen(Request(service.bridge.url+'/hologram/assets/'+assets[0].name,headers=headers)) as response:
        assert "connect-src 'self'" in response.headers.get('Content-Security-Policy','')
