"""Authenticated additions to the original ULTRON HTTP service."""
import asyncio
import hmac
import hashlib
import os
import copy
import secrets
import uuid
from pathlib import Path
from aiohttp import web

from cloud_client import CloudClient, safe_cloud_error
from ultron.cloud_service.conversation_persona import classify_intent
from ultron.cloud_service.text_normalization import fold_turkish
import re


def _requested_local_system_facts(text: str) -> tuple[str, ...]:
    """Recognize explicit questions about THIS computer, never generic OS advice.

    Do not send device details to a chat model just to interpret the request.
    """
    t = fold_turkish(text)
    personal = bool(re.search(
        r"\b(?:benim|bilgisayarim(?:in|daki|da)?|laptopum(?:un|daki|da)?|"
        r"cihazim(?:in|daki|da)?|pc(?:m|min))\b", t,
    ))
    patterns = (
        ("windows", r"\b(?:windows|isletim sistemi)(?:\s+\w+)?\s+surumum(?:u)?\b",
         r"\b(?:windows|isletim sistemi)(?:\s+\w+)?\s+surum\w*\b"),
        ("cpu", r"\b(?:islemci(?:\s+model)?|cpu(?:\s+model)?)m(?:i)?\b|"
         r"\b(?:islemci|cpu)\s+modelim(?:i)?\b",
         r"\b(?:islemci|cpu)(?:\s+model\w*)?\b"),
        ("ram", r"\b(?:ramim(?:i)?|bellegim(?:i)?|"
         r"(?:ram|bellek)\s+(?:miktarim|kapasitem)(?:i)?)\b",
         r"\b(?:ram|bellek)\b"),
        ("timezone", r"\bsaat\s+dilimim(?:i)?\b",
         r"\bsaat\s+dilim\w*\b"),
        ("microphone", r"\b(?:varsayilan\s+)?mikrofonum(?:u)?\b",
         r"\b(?:mikrofon|microphone)\w*\b"),
    )
    fields = []
    for name, owned_pattern, general_pattern in patterns:
        if re.search(owned_pattern, t) or (
            personal and re.search(general_pattern, t)
        ):
            fields.append(name)
    # Clear ownership and at least one specific machine fact are required.
    # "Windows 11'in özellikleri" or "RAM nedir?" remain normal chat.
    if not fields:
        return ()
    # A generic question with no ownership isn't a request for local data.
    if not personal and not any(re.search(p[1], t) for p in patterns):
        return ()
    return tuple(fields)


def _format_local_system_facts(status: dict, fields: tuple[str, ...]) -> str:
    """Only display the requested fields, never process/window/network inventory."""
    labels = {
        "windows": "Windows sürümü", "cpu": "İşlemci modeli",
        "ram": "Toplam RAM", "timezone": "Saat dilimi",
        "microphone": "Varsayılan mikrofon",
    }
    results = {
        "windows": (f"{status.get('os_name')} (derleme {status.get('os_version')})"
                    if status.get("os_name") and status.get("os_version")
                    else status.get("os_name")),
        "cpu": status.get("cpu_model"),
        "ram": (f"{status['ram_total_gb']} GB"
                if isinstance(status.get("ram_total_gb"), (float, int))
                and status["ram_total_gb"] > 0 else None),
        "timezone": status.get("timezone"),
        "microphone": status.get("default_microphone"),
    }
    return "\n".join(f"{labels[field]}: {results[field] or 'Bilgi okunamadı'}"
                     for field in fields)

from app.core.request_cancellation import (
    ProviderRequestCancelled, RequestCancellationRegistry,
    valid_request_id, valid_request_key,
)


def install(app, hub):
    token = os.environ.get('MARK_ULTRON_TOKEN', '')
    gate = asyncio.Lock()
    cloud = CloudClient()
    cancellations = RequestCancellationRegistry()

    def request_owner(req):
        # Existing desktop auth remains authoritative. Hash credentials before
        # using them as in-memory map keys; never put bearer values in records.
        credential = req.headers.get('X-MARK-Token', '') or req.cookies.get('mark_session', '')
        if credential:
            return 'mark:' + hashlib.sha256(credential.encode('utf-8')).hexdigest()
        return 'local-anonymous'

    async def await_until_cancelled(awaitable, record):
        """Detach a non-cancellable executor-backed provider on UI interruption."""
        provider_task = asyncio.create_task(awaitable)
        cancel_task = asyncio.create_task(record.cancel_event.wait())
        try:
            done, _ = await asyncio.wait((provider_task, cancel_task),
                                         return_when=asyncio.FIRST_COMPLETED)
            if cancel_task in done and record.cancel_event.is_set():
                provider_task.cancel()
                await asyncio.gather(provider_task, return_exceptions=True)
                return None, True
            return await provider_task, False
        finally:
            cancel_task.cancel()
            await asyncio.gather(cancel_task, return_exceptions=True)

    @web.middleware
    async def boundary(req, handler):
        if req.path.startswith('/frontend-mobile/'):
            return web.json_response({'ok': False, 'error': 'DESKTOP_ONLY',
                'message': 'Bu özellik GÖLGE masaüstü uygulamasında kullanılabilir. START.bat ile uygulamayı başlat.'}, status=410)
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
        audio_owner = os.environ.get('MARK_AUDIO_OWNER')
        if audio_owner == 'mark':
            audio_owner = 'desktop'
        return web.json_response({'service': 'GÖLGE', 'ok': required_ok,
            'components': components, 'audio_owner': audio_owner,
            'ollama': hub.ai_status, 'cloud': {
                'enabled': cloud.enabled, 'last_ok_ts': cloud.last_ok_ts,
                'last_error': cloud.last_error}, 'pid': os.getpid()})

    async def invoke(req):
        try:
            body = await req.json()
            text = str(body.get('text', '')).strip()
            mode = body.get('mode', 'auto')
            selected_model = body.get('model')
            request_id = body.get('request_id') or str(uuid.uuid4())
            request_key = body.get('request_key') or secrets.token_hex(32)
        except (ValueError, AttributeError):
            return web.json_response({'ok': False, 'error': 'bad request'}, status=400)
        if not text or len(text) > 50000 or mode not in ('auto', 'coding', 'general', 'fast', 'agent', 'task', 'multi'):
            return web.json_response({'ok': False, 'error': 'invalid input'}, status=400)
        if not valid_request_id(request_id) or not valid_request_key(request_key):
            return web.json_response({'ok': False, 'error': 'invalid request identity'}, status=400)
        try:
            record = cancellations.register(request_owner(req), request_id, request_key)
        except ValueError:
            return web.json_response({'ok': False, 'error': 'request identity conflict'}, status=409)
        rt = hub.bridge.runtime if hub.bridge and hub.bridge.available else None
        if rt is None:
            cancellations.finish(record, 'failed')
            return web.json_response({'ok': False, 'status': 'UNAVAILABLE', 'error': 'runtime yok',
                                      'request_id': request_id})
        if record.cancel_event.is_set():
            cancellations.finish(record, 'cancelled_before_start')
            return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                                      'request_id': request_id, 'provider_stopped': False,
                                      'text': ''})
        # A locally-owned machine fact question is read on the laptop, never
        # answered by Cloud Gemini or guessed by a text-only Ollama model.
        # It is strictly read-only and does not invoke arbitrary tools.
        local_facts = (_requested_local_system_facts(text)
                       if mode in ('auto', 'general', 'fast') else ())
        if local_facts:
            cancellations.set_provider(record, 'desktop-system-facts',
                                       cancellable=False, started=False)
            if record.cancel_event.is_set():
                cancellations.finish(record, 'cancelled_before_start')
                return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                    'request_id': request_id, 'provider_stopped': False, 'text': ''})
            try:
                from actions.system_monitor import get_system_status
                cancellations.set_provider(record, 'desktop-system-facts',
                                           cancellable=False, started=True)
                facts = await asyncio.to_thread(get_system_status, include_details=True)
                if record.cancel_event.is_set():
                    cancellations.finish(record, 'output_suppressed')
                    return web.json_response({'ok': False, 'status': 'output_suppressed',
                        'request_id': request_id, 'provider_stopped': False, 'text': ''})
                answer = _format_local_system_facts(facts, local_facts)
                cancellations.finish(record, 'completed')
                return web.json_response({'ok': True, 'text': answer,
                                          'source': 'desktop-local-read-only',
                                          'request_id': request_id})
            except Exception:
                # Fail closed: don't invent facts or reveal raw local exceptions.
                cancellations.finish(record, 'failed')
                return web.json_response({'ok': False,
                    'text': 'Bilgisayarın sistem bilgileri şu anda okunamadı.',
                    'error_code': 'local_system_facts_unavailable',
                    'request_id': request_id}, status=503)
        # Explicit arithmetic in the Windows Calculator uses only its verified
        # accessibility button controls. No global key presses and no Cloud LLM.
        if mode in ('auto', 'general', 'fast'):
            from app.tools.calculator_gui import extract_calculator_expression
            calculator_expression = extract_calculator_expression(text)
            if calculator_expression:
                cancellations.set_provider(record, 'desktop-calculator-ui',
                                           cancellable=False, started=False)
                if record.cancel_event.is_set():
                    cancellations.finish(record, 'cancelled_before_start')
                    return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                        'request_id': request_id, 'provider_stopped': False, 'text': ''})
                async with gate:
                    if record.cancel_event.is_set():
                        cancellations.finish(record, 'cancelled_before_start')
                        return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                            'request_id': request_id, 'provider_stopped': False, 'text': ''})
                    from app.tools.calculator_gui import run_calculator_expression
                    cancellations.set_provider(record, 'desktop-calculator-ui',
                                               cancellable=False, started=True)
                    outcome = await asyncio.to_thread(
                        run_calculator_expression, calculator_expression)
                if record.cancel_event.is_set():
                    cancellations.finish(record, 'output_suppressed')
                    return web.json_response({'ok': False, 'status': 'output_suppressed',
                        'request_id': request_id, 'provider_stopped': False,
                        'operation_continues': True, 'text': ''})
                ok = bool(outcome.get('ok') and outcome.get('verified'))
                code = str(outcome.get('error_code', 'calculator_not_verified'))
                reply = (
                    'Hesap Makinesi tuşlarına işlem girildi; ekrandaki sonuç '
                    + str(outcome.get('result')) + ' olarak doğrulandı.'
                    if ok else
                    'Hesap Makinesi işlemi doğrulanamadı. '
                    'Başka pencereye tuş gönderilmedi. Hata kodu: ' + code
                )
                cancellations.finish(record, 'completed' if ok else 'failed')
                return web.json_response({
                    'ok': ok, 'text': reply, 'verified': ok,
                    'source': 'desktop-calculator-ui',
                    'request_id': request_id,
                    **({'error_code': code} if not ok else {}),
                })
        intent = classify_intent(text)
        # General/coding/fast are presentation/model preferences. An
        # explicit computer operation still belongs to the existing local
        # approval-gated agent, never the read-only Cloud chat path.
        if intent.kind == 'computer_task' and mode in ('auto', 'general', 'coding', 'fast'):
            mode = 'agent'
        if mode == 'agent':
            cancellations.set_provider(record, 'computer-task', cancellable=False, started=False)
            if record.cancel_event.is_set():
                cancellations.finish(record, 'cancelled_before_start')
                return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                    'request_id': request_id, 'provider_stopped': False, 'text': ''})
            # Stop only the conversational delivery. Once started, computer
            # work remains under its own approval/task lifecycle.
            async with gate:
                if record.cancel_event.is_set():
                    cancellations.finish(record, 'cancelled_before_start')
                    return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                        'request_id': request_id, 'provider_stopped': False, 'text': ''})
                cancellations.set_provider(record, 'computer-task', cancellable=False, started=True)
                result = await hub.agent.run(text, approved=False)
            if record.cancel_requested:
                cancellations.finish(record, 'output_suppressed')
                return web.json_response({'ok': False, 'status': 'output_suppressed',
                    'request_id': request_id, 'provider_stopped': False,
                    'operation_continues': True, 'text': ''})
            result = result if isinstance(result, dict) else {}
            state = str(getattr(hub.agent, 'state', 'UNKNOWN'))
            message = str(getattr(hub.agent, 'message', '') or '').strip()
            waiting = state == 'WAITING_APPROVAL' or result.get('result') == 'waiting-approval'
            partial = state == 'DONE' and message.startswith('PLAN PARTIAL ')
            no_intent = result.get('result') == 'no-intent'
            completed = (state == 'DONE' and result.get('ok') is True
                         and not partial and not no_intent)
            if waiting:
                pending = getattr(hub, 'pending_task', None)
                task_id = pending.get('id') if isinstance(pending, dict) else result.get('task_id')
                response_text = 'İşlem güvenlik onayı bekliyor.'
                if task_id:
                    response_text += f' Onay isteği: {task_id}.'
            elif completed:
                response_text = message or str(result.get('output') or '').strip()
                if not response_text:
                    response_text = 'İşlem tamamlandı ve agent sonucu doğruladı.'
            elif state == 'ERROR':
                response_text = message or 'İşlem başarısız oldu.'
            elif state == 'DONE' and message:
                response_text = message
            else:
                response_text = 'İşlemin sonucu doğrulanamadı; tamamlandı diyemem.'
            cancellations.finish(record, 'completed' if completed or waiting else 'failed')
            return web.json_response({
                'ok': waiting or completed, 'text': response_text, 'state': state,
                'result': result, 'completed': completed,
                'pending_approval': waiting,
                'intent': intent.kind,
                'request_id': request_id,
            })
        if mode == 'task':
            cancellations.set_provider(record, 'task-queue', cancellable=False, started=False)
            if record.cancel_event.is_set():
                cancellations.finish(record, 'cancelled_before_start')
                return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                    'request_id': request_id, 'provider_stopped': False, 'text': ''})
            cancellations.set_provider(record, 'task-queue', cancellable=False, started=True)
            task = await hub.supervisor.submit(text, budgets={}, spawn=True)
            cancellations.finish(record, 'completed')
            return web.json_response({'ok': True, 'task_id': task['id'], 'status': task['status'],
                                      'request_id': request_id})

        effective_mode = mode
        if effective_mode == 'auto':
            effective_mode = 'coding' if any(
                w in text.lower() for w in ('kod', 'code', 'python', 'debug', 'program')
            ) else 'general'

        # Desktop chat uses the exact same Render/Supabase brain as the phone.
        # Explicit local model selection, coding/multi modes and agent/task tools stay local.
        if cloud.enabled and selected_model is None and effective_mode in ('general', 'fast'):
            def request_cloud_cancel():
                cancel_chat = getattr(cloud, 'cancel_chat', None)
                if callable(cancel_chat):
                    async def send_cancel():
                        try:
                            await cancel_chat(request_id, request_key)
                        except Exception:
                            pass
                    asyncio.create_task(send_cancel())
            cancellations.set_provider(record, 'gemini-cloud', cancellable=False,
                                        cancel_callback=request_cloud_cancel, started=False)
            if record.cancel_event.is_set():
                cancellations.finish(record, 'cancelled_before_start')
                return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                    'request_id': request_id, 'provider_stopped': False, 'text': ''})
            try:
                await hub.broadcast({'type': 'agent', 'state': 'THINKING'})
                if record.cancel_event.is_set():
                    cancellations.finish(record, 'cancelled_before_start')
                    return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                        'request_id': request_id, 'provider_stopped': False, 'text': ''})
                cancellations.set_provider(record, 'gemini-cloud', cancellable=False,
                    cancel_callback=request_cloud_cancel, started=True)
                data, cancelled = await await_until_cancelled(
                    cloud.chat(text, request_id=request_id, request_key=request_key), record)
                if cancelled or record.cancel_event.is_set():
                    cancellations.finish(record, 'output_suppressed')
                    return web.json_response({'ok': False, 'status': 'output_suppressed',
                        'request_id': request_id, 'provider': 'gemini-cloud',
                        'provider_stopped': False, 'text': ''})
                answer = str(data.get('reply', '')).strip()
                if not answer:
                    raise RuntimeError('GÖLGE Cloud returned an empty reply')
                hub.memory.add_session('assistant', answer)
                await hub.on_activity('Desktop chat answered by shared GÖLGE Cloud', 'success')
                cancellations.finish(record, 'completed')
                return web.json_response({
                    'ok': True,
                    'text': answer,
                    'model': 'cloud-gemini',
                    'source': 'cloud',
                    'conversation_id': data.get('conversation_id'),
                    'request_id': request_id,
                })
            except Exception as exc:
                if record.cancel_event.is_set():
                    cancellations.finish(record, 'output_suppressed')
                    return web.json_response({'ok': False, 'status': 'output_suppressed',
                        'request_id': request_id, 'provider': 'gemini-cloud',
                        'provider_stopped': False, 'text': ''})
                # Cloud outage must never disable the desktop; fall back to local Ollama.
                await hub.on_activity(
                    f'Cloud unavailable; local Ollama fallback ({safe_cloud_error(exc)})', 'warn')
            finally:
                await hub.broadcast({'type': 'agent', 'state': hub.agent.state})

        check = await hub.check_ollama()
        hub.ai_status = check['status']
        models = hub.ai_status.get('models', [])
        models = [m if isinstance(m, str) else m.get('name') for m in models]
        models = [m for m in models if m]
        if not models:
            cancellations.finish(record, 'failed')
            return web.json_response({'ok': False, 'status': 'UNAVAILABLE',
                'error': 'Ollama veya yerel model yok. INSTALL.bat model kurulumunu deneyebilir.',
                'request_id': request_id})
        mode = effective_mode
        from app.core.model_router import ModelRouter, safe_provider_error
        settings = copy.deepcopy(rt.settings)
        if selected_model:
            if not isinstance(selected_model, str) or selected_model not in models:
                cancellations.finish(record, 'failed')
                return web.json_response({'ok': False, 'error': 'MODEL NOT AVAILABLE',
                                          'request_id': request_id}, status=400)
            settings['llm'].setdefault('routing', {})[mode.lower()] = selected_model
        settings['llm'].setdefault('local_multi_model', {})['enabled'] = mode == 'multi'
        router = ModelRouter(rt.brain, settings, get_models=lambda: models)
        multi_model = router.local_multi_enabled()
        cancellations.set_provider(record,
            'ollama-local-multi' if multi_model else 'ollama-stream',
            cancellable=not multi_model, started=False)
        if record.cancel_event.is_set():
            cancellations.finish(record, 'cancelled_before_start')
            return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                'request_id': request_id, 'provider_stopped': False, 'text': ''})
        try:
            await hub.broadcast({'type': 'agent', 'state': 'THINKING'})
            if record.cancel_event.is_set():
                cancellations.finish(record, 'cancelled_before_start')
                return web.json_response({'ok': False, 'status': 'cancelled_before_start',
                    'request_id': request_id, 'provider_stopped': False, 'text': ''})
            cancellations.set_provider(record, record.provider,
                                        cancellable=not multi_model, started=True)
            if multi_model:
                answer, cancelled = await await_until_cancelled(
                    asyncio.to_thread(router.ask, mode.upper(), text), record)
                if cancelled or record.cancel_event.is_set():
                    cancellations.finish(record, 'output_suppressed')
                    return web.json_response({'ok': False, 'status': 'output_suppressed',
                        'request_id': request_id, 'provider': 'ollama-local-multi',
                        'provider_stopped': False, 'text': ''})
            else:
                answer = await router.ask_cancellable(
                    mode.upper(), text, cancel_event=record.cancel_event)
            if record.cancel_event.is_set():
                # The provider already returned; a cancel racing with response
                # delivery suppresses output but cannot be reported as stopped.
                cancellations.finish(record, 'output_suppressed')
                return web.json_response({'ok': False,
                    'status': 'output_suppressed',
                    'request_id': request_id, 'provider': record.provider,
                    'provider_stopped': False, 'text': ''})
            cancellations.finish(record, 'completed')
            return web.json_response({'ok': True, 'text': answer,
                                     'model': router.resolve(mode.upper()), 'source': 'local',
                                     'request_id': request_id})
        except ProviderRequestCancelled as exc:
            cancellations.finish(record, 'provider_cancelled',
                                 provider_stopped=exc.provider_stopped)
            stopped = cancellations.describe(request_owner(req), request_id, request_key)
            return web.json_response({'ok': False, 'status': stopped['status'],
                'request_id': request_id, 'provider': 'ollama-stream',
                'provider_stopped': stopped['provider_stopped'], 'text': ''})
        except Exception as exc:
            if record.cancel_event.is_set():
                cancellations.finish(record, 'output_suppressed')
                return web.json_response({'ok': False, 'status': 'output_suppressed',
                    'request_id': request_id, 'provider': record.provider,
                    'provider_stopped': False, 'text': ''})
            cancellations.finish(record, 'failed')
            error_code = safe_provider_error(exc)
            message = ('Yerel model şu anda erişilemiyor; biraz sonra yeniden deneyin.'
                       if error_code == 'provider_temporarily_unavailable'
                       else 'Yerel model isteği tamamlanamadı.')
            return web.json_response({'ok': False, 'status': 'UNAVAILABLE',
                                          'error': message, 'error_code': error_code,
                                          'request_id': request_id}, status=503)
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

    async def cancel_request(req):
        try:
            body = await req.json()
            request_id = body.get('request_id')
            request_key = body.get('request_key')
        except (ValueError, AttributeError):
            return web.json_response({'ok': False, 'error': 'bad request'}, status=400)
        if not valid_request_id(request_id) or not valid_request_key(request_key):
            return web.json_response({'ok': False, 'error': 'invalid request identity'}, status=400)
        owner = request_owner(req)
        result = cancellations.cancel(owner, request_id, request_key)
        record = cancellations.lookup(owner, request_id, request_key)
        if record is not None and result.get('status') == 'cancellation_requested' \
                and record.provider_cancellable and record.provider_started:
            # Give Ollama's streaming request a short chance to observe the
            # cancellation and close its transport. If it does not, report the
            # request as pending instead of claiming it stopped.
            await cancellations.wait_terminal(record, 0.35)
            result = cancellations.describe(owner, request_id, request_key)
        return web.json_response({'ok': result.get('status') != 'not_found', **result})

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
        import binascii
        import io
        import tempfile
        from PIL import Image, UnidentifiedImageError
        from app.core.model_router import safe_provider_error
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
        except (ValueError, TypeError, binascii.Error, UnidentifiedImageError) as exc:
            return web.json_response({'ok': False, 'error': str(exc)}, status=400)
        except Exception as exc:
            error_code = safe_provider_error(exc)
            message = ('Görsel analizi için yerel model şu anda erişilemiyor.'
                       if error_code == 'provider_temporarily_unavailable'
                       else 'Görsel analizi tamamlanamadı.')
            return web.json_response({'ok': False, 'error': message,
                                      'error_code': error_code}, status=502)

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
<title>GÖLGE</title><p id="status">Panel açılıyor…</p><script>
const showHologram = location.pathname.endsWith('/hologram');
const token = location.hash.slice(1); history.replaceState(null, '', location.pathname);
fetch('/api/merged/session', {method:'POST', headers:{'X-MARK-Token':token}})
.then(r => {if (!r.ok) throw Error('Yetkilendirme başarısız. GÖLGE masaüstü uygulamasından tekrar açın.');
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
    app.router.add_post('/api/merged/cancel', cancel_request)
    app.router.add_post('/api/merged/tool', tool)
    app.router.add_post('/api/merged/shutdown', shutdown)
    app.router.add_post('/api/merged/document', document)
    app.router.add_post('/api/merged/image', image)
    app.router.add_get('/merged/dashboard', dashboard)
    app.router.add_get('/merged/hologram', dashboard)
    app.router.add_get('/hologram/{asset:.*}', frontend)
    app.router.add_post('/api/merged/session', session)
    app.router.add_get('/{surface:frontend|frontend-mobile}/{asset:.*}', frontend)
