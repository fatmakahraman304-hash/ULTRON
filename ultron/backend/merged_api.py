"""Authenticated additions to the original ULTRON HTTP service."""
import asyncio
import hmac
import os
from pathlib import Path
from aiohttp import web


def install(app, hub):
    token = os.environ.get('MARK_ULTRON_TOKEN', '')
    gate = asyncio.Lock()

    @web.middleware
    async def boundary(req, handler):
        if token and not hmac.compare_digest(req.headers.get('X-MARK-Token', ''), token):
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
        components['vault'] = bool(rt and rt.vault.health().get('ok'))
        return web.json_response({'service': 'mark-ultron', 'ok': all(components.values()),
            'components': components, 'audio_owner': os.environ.get('MARK_AUDIO_OWNER'),
            'ollama': hub.ai_status, 'pid': os.getpid()})

    async def invoke(req):
        try:
            body = await req.json()
            text = str(body.get('text', '')).strip()
            mode = body.get('mode', 'auto')
        except (ValueError, AttributeError):
            return web.json_response({'ok': False, 'error': 'bad request'}, status=400)
        if not text or len(text) > 50000 or mode not in ('auto', 'coding', 'general', 'fast', 'agent'):
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
            check = await hub.check_ollama()
            hub.ai_status = check['status']
            models = hub.ai_status.get('models', [])
            models = [m if isinstance(m, str) else m.get('name') for m in models]
            models = [m for m in models if m]
            if not models:
                return web.json_response({'ok': False, 'status': 'UNAVAILABLE',
                    'error': 'Ollama veya yerel model yok. INSTALL.bat model kurulumunu deneyebilir.'})
            if mode == 'auto':
                mode = 'coding' if any(w in text.lower() for w in ('kod', 'code', 'python', 'debug', 'program')) else 'general'
            from app.core.model_router import ModelRouter
            router = ModelRouter(rt.brain, rt.settings, get_models=lambda: models)
            try:
                answer = await asyncio.to_thread(router.ask, mode.upper(), text)
                return web.json_response({'ok': True, 'text': answer, 'model': router.resolve(mode.upper())})
            except Exception as exc:
                return web.json_response({'ok': False, 'status': 'UNAVAILABLE', 'error': str(exc)})

    async def shutdown(req):
        def stop():
            raise web.GracefulExit()
        asyncio.get_running_loop().call_later(0.2, stop)
        return web.json_response({'ok': True})

    async def frontend(req):
        root = Path(__file__).resolve().parents[1] / req.match_info['surface'] / 'dist'
        relative = req.match_info.get('asset') or 'index.html'
        target = (root / relative).resolve()
        if not target.is_relative_to(root.resolve()):
            raise web.HTTPForbidden()
        if not target.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(target)

    app.router.add_get('/api/merged/health', health)
    app.router.add_post('/api/merged/invoke', invoke)
    app.router.add_post('/api/merged/shutdown', shutdown)
    app.router.add_get('/{surface:frontend|frontend-mobile}/{asset:.*}', frontend)
