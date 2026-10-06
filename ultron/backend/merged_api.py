"""Authenticated additions to the original ULTRON HTTP service."""
import asyncio
import hmac
import os
import copy
from pathlib import Path
from aiohttp import web

from cloud_client import CloudClient


def install(app, hub):
    token = os.environ.get('MARK_ULTRON_TOKEN', '')
    gate = asyncio.Lock()
    cloud = CloudClient()

    @web.middleware
    async def boundary(req, handler):
        if req.path.startswith('/frontend-mobile/'):
            return web.json_response({'ok': False, 'error': 'DESKTOP_ONLY',
                'message': 'ULTRON uses the original MARK desktop interface. Start START.bat.'}, status=410)
        if req.path in ('/merged/hologram', '/merged/dashboard') and req.method == 'GET':
            return await handler(req)
        if token:
            header_ok = hmac.compare_digest(req.headers.get('X-MARK-Token', ''), token)
            cookie_ok = hmac.compare_digest(req.cookies.get('mark_session', ''), token)
            origin = req.headers.get('Origin')
            same_origin = origin == f'{req.scheme}://{req.host}'
            if not header_ok and (not cookie_ok or (origin and not same_origin)
                    or (req.method not in ('GET', 'HEAD') and not same_origin)):
                return web.json_response({'ok': False, 'error': 'unauthorized'}, status=401)
        if os.environ.get('MARK_AUDIO_OWNER') == 'mark' and req.path in {
            '/api/voice/live', '/api/voice/ptt'} and req.method == 'POST':
            return web.json_response({'ok': False, 'status': 'OWNED_BY_MARK'}, status=409)
        return await handler(req)

    app.middlewares.insert(0, boundary)

    async def health(req):
        rt = hub.bridge.runtime if hub.bridge and hub.bridge.available else None
        names = ('brain', 'memory', 'registry', 'agent', 'permissions', 'sandbox')
        components = {name: getattr(rt, name, None) is not None for name in names}
        components.update({name: getattr(hub, name, None) is not None
                           for name in ('task_engine', 'supervisor', 'world')})
        components['vault'] = bool(rt and rt.vault.health().get('available'))
        components['cloud'] = cloud.enabled
        required_ok = all(value for name, value in components.items() if name != 'cloud')
        return web.json_response({'service': 'mark-ultron', 'ok': required_ok,
            'components': components, 'audio_owner': os.environ.get('MARK_AUDIO_OWNER'),
            'ollama': hub.ai_status, 'cloud': {
                'enabled': cloud.enabled, 'last_ok_ts': cloud.last_ok_ts,
                'last_error': cloud.last_error}, 'pid': os.getpid()})

    async def invoke(req):
        try:
            body = await req.json()
            text = str(body.get('text', '')).strip()
            mode = body.get('mode', 'auto')
            selected_model = body.get('model')
        except (ValueError, AttributeError):
            return web.json_response({'ok': False, 'error': 'bad request'}, status=400)
        if not text or len(text) > 50000 or mode not in ('auto', 'coding', 'general', 'fast', 'agent', 'task', 'multi'):
            return web.json_response({'ok': False, 'error': 'invalid input'}, status=400)
        if gate.locked():
            return web.json_response({'ok': False, 'error': 'motor meşgul'}, status=409)
        async with gate:
            rt = hub.bridge.runtime if hub.bridge and hub.bridge.available else None
            if rt is None:
                return web.json_response({'ok': False, 'status': 'UNAVAILABLE', 'error': 'runtime yok'})
            if mode == 'agent':
                # Server-owned approval boundary; no caller can pass approved=True.
                await hub.agent.run(text, approved=False)
                return web.json_response({'ok': True, 'state': hub.agent.state,
                                          'pending_approval': hub.pending_task})
            if mode == 'task':
                task = await hub.supervisor.submit(text, budgets={}, spawn=True)
                return web.json_response({'ok': True, 'task_id': task['id'], 'status': task['status']})

            effective_mode = mode
            if effective_mode == 'auto':
                effective_mode = 'coding' if any(
                    w in text.lower() for w in ('kod', 'code', 'python', 'debug', 'program')
                ) else 'general'

            # Desktop chat uses the exact same Render/Supabase brain as the phone.
            # Explicit local model selection, coding/multi modes and agent/task tools stay local.
            if cloud.enabled and selected_model is None and effective_mode in ('general', 'fast'):
                try:
                    await hub.broadcast({'type': 'agent', 'state': 'THINKING'})
                    data = await cloud.chat(text)
                    answer = str(data.get('reply', '')).strip()
                    if not answer:
                        raise RuntimeError('ULTRON Cloud returned an empty reply')
                    hub.memory.add_session('assistant', answer)
                    await hub.on_activity('Desktop chat answered by shared ULTRON Cloud', 'success')
                    return web.json_response({
                        'ok': True,
                        'text': answer,
                        'model': 'cloud-gemini',
                        'source': 'cloud',
                        'conversation_id': data.get('conversation_id'),
                    })
                except Exception as exc:
                    # Cloud outage must never disable the desktop; fall back to local Ollama.
                    await hub.on_activity(
                        f'Cloud unavailable; local Ollama fallback: {str(exc)[:120]}', 'warn')
                finally:
                    await hub.broadcast({'type': 'agent', 'state': hub.agent.state})

            check = await hub.check_ollama()
            hub.ai_status = check['status']
            models = hub.ai_status.get('models', [])
            models = [m if isinstance(m, str) else m.get('name') for m in models]
            models = [m for m in models if m]
            if not models:
                return web.json_response({'ok': False, 'status': 'UNAVAILABLE',
                    'error': 'Ollama veya yerel model yok. INSTALL.bat model kurulumunu deneyebilir.'})
            mode = effective_mode
            from app.core.model_router import ModelRouter
            settings = copy.deepcopy(rt.settings)
            if selected_model:
                if not isinstance(selected_model, str) or selected_model not in models:
                    return web.json_response({'ok': False, 'error': 'MODEL NOT AVAILABLE'}, status=400)
                settings['llm'].setdefault('routing', {})[mode.lower()] = selected_model
            settings['llm'].setdefault('local_multi_model', {})['enabled'] = mode == 'multi'
            router = ModelRouter(rt.brain, settings, get_models=lambda: models)
            try:
                await hub.broadcast({'type': 'agent', 'state': 'THINKING'})
                answer = await asyncio.to_thread(router.ask, mode.upper(), text)
                return web.json_response({'ok': True, 'text': answer,
                                          'model': router.resolve(mode.upper()), 'source': 'local'})
            except Exception as exc:
                return web.json_response({'ok': False, 'status': 'UNAVAILABLE', 'error': str(exc)})
            finally:
                await hub.broadcast({'type': 'agent', 'state': hub.agent.state})

    async def tool(req):
        body = await req.json()
        name, arguments = body.get('name'), body.get('arguments', {})
        rt = hub.bridge.runtime if hub.bridge and hub.bridge.available else None
        if not isinstance(name, str) or not isinstance(arguments, dict) or rt is None:
            return web.json_response({'ok': False, 'error': 'invalid tool request'}, status=400)
        try:
            result = await asyncio.to_thread(rt.executor.execute, [(name, arguments)], approved=False)
            return web.json_response({'ok': True, 'result': result})
        except PermissionError as exc:
            return web.json_response({'ok': False, 'needs_approval': True, 'error': str(exc)})
        except Exception as exc:
            return web.json_response({'ok': False, 'error': str(exc)})

    async def shutdown(req):
        def stop():
            raise web.GracefulExit()
        asyncio.get_running_loop().call_later(0.2, stop)
        return web.json_response({'ok': True})

    async def document(req):
        import base64
        import binascii
        import io
        try:
            body=await req.json()
            name=str(body.get('name',''))
            data=base64.b64decode(body.get('data',''),validate=True)
            if not data or len(data)>8*1024*1024:
                raise ValueError('Dosya boş veya 8 MB sınırını aşıyor.')
            suffix=Path(name).suffix.lower()
            def extract():
                if suffix=='.pdf':
                    from pypdf import PdfReader
                    reader=PdfReader(io.BytesIO(data))
                    if reader.is_encrypted:
                        raise ValueError('Şifreli PDF desteklenmiyor.')
                    return '\n'.join((page.extract_text() or '')[:12000] for page in reader.pages[:30])[:36000]
                if suffix not in {'.txt','.md','.json','.csv','.py','.js','.ts','.tsx','.html','.css'}:
                    raise ValueError('PDF veya metin dosyası seçin.')
                return data.decode('utf-8-sig')[:36000]
            text=await asyncio.wait_for(asyncio.to_thread(extract),20)
            if not text.strip():
                raise ValueError('Dosyada okunabilir metin bulunamadı; taranmış PDF için OCR gerekir.')
            return web.json_response({'ok':True,'text':text})
        except (ValueError,TypeError,AttributeError,binascii.Error,UnicodeError) as exc:
            return web.json_response({'ok':False,'error':str(exc)},status=400)
        except Exception:
            return web.json_response({'ok':False,'error':'Dosya okunamadı. Geçerli bir PDF veya UTF-8 metin dosyası seçin.'},status=400)

    async def image(req):
        """Bounded image adapter to the existing vision implementation; no arbitrary paths."""
        import base64
        import io
        import tempfile
        from PIL import Image
        rt = hub.bridge.runtime if hub.bridge and hub.bridge.available else None
        if rt is None or rt.vision_llm is None:
            return web.json_response({'ok': False, 'error': 'Vision unavailable'}, status=503)
        try:
            body = await req.json()
            data = base64.b64decode(body.get('data', ''), validate=True)
            if not data or len(data) > 8*1024*1024:
                raise ValueError('En fazla 8 MB görüntü seçin.')
            def analyze():
                with Image.open(io.BytesIO(data)) as source:
                    if source.width*source.height > 20000000:
                        raise ValueError('Görüntü en fazla 20 megapiksel olabilir.')
                    source.load()
                    with tempfile.TemporaryDirectory(prefix='ultron-vision-') as folder:
                        path = Path(folder)/'upload.png'
                        source.convert('RGB').save(path)
                        if body.get('mode') == 'ocr':
                            import pytesseract
                            return pytesseract.image_to_string(source)
                        return rt.vision_llm.analyze(path, available_models=hub.ai_status.get('models', []))
            text = await asyncio.to_thread(analyze)
            return web.json_response({'ok': True, 'text': text})
        except Exception as exc:
            return web.json_response({'ok': False, 'error': str(exc)}, status=400)

    async def frontend(req):
        root = Path(__file__).resolve().parents[1] / req.match_info.get('surface', 'frontend') / 'dist'
        relative = req.match_info.get('asset') or 'index.html'
        if req.path.startswith('/hologram/'):
            if relative.endswith('.html') and relative != 'hologram.html':
                raise web.HTTPNotFound()
        elif relative.endswith('.html') and relative != 'index.html':
            raise web.HTTPNotFound()
        target = (root / relative).resolve()
        if not target.is_relative_to(root.resolve()):
            raise web.HTTPForbidden()
        if not target.is_file():
            raise web.HTTPNotFound()
        headers={}
        if target.name.startswith('hand.worker-') and target.suffix=='.js':
            # Local hand inference needs local WASM/model files only; block metrics endpoints.
            headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'"
        return web.FileResponse(target,headers=headers)

    async def dashboard(req):
        # Fragment never reaches HTTP logs. Exchange it for a session-only cookie.
        return web.Response(text='''<!doctype html><html lang="tr"><meta charset="utf-8">
<title>ULTRON</title><p id="status">Panel açılıyor…</p><script>
const showHologram = location.pathname.endsWith('/hologram');
const token = location.hash.slice(1); history.replaceState(null, '', location.pathname);
fetch('/api/merged/session', {method:'POST', headers:{'X-MARK-Token':token}})
.then(r => {if (!r.ok) throw Error('Yetkilendirme başarısız. MARK panelinden tekrar açın.');
location.replace(showHologram ? '/hologram/hologram.html' : '/frontend/index.html');})
.catch(e => document.getElementById('status').textContent=e.message);
</script></html>''', content_type='text/html', headers={'Cache-Control':'no-store',
            'Referrer-Policy':'no-referrer', 'Content-Security-Policy':
            "default-src 'none'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})

    async def session(req):
        if not token or not hmac.compare_digest(req.headers.get('X-MARK-Token', ''), token):
            raise web.HTTPUnauthorized()
        response = web.json_response({'ok': True}, headers={'Cache-Control':'no-store'})
        response.set_cookie('mark_session', token, httponly=True, samesite='Strict', path='/')
        return response

    app.router.add_get('/api/merged/health', health)
    app.router.add_post('/api/merged/invoke', invoke)
    app.router.add_post('/api/merged/tool', tool)
    app.router.add_post('/api/merged/shutdown', shutdown)
    app.router.add_post('/api/merged/document', document)
    app.router.add_post('/api/merged/image', image)
    app.router.add_get('/merged/dashboard', dashboard)
    app.router.add_get('/merged/hologram', dashboard)
    app.router.add_get('/hologram/{asset:.*}', frontend)
    app.router.add_post('/api/merged/session', session)
    app.router.add_get('/{surface:frontend|frontend-mobile}/{asset:.*}', frontend)
