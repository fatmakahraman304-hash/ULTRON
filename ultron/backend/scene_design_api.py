"""Desktop data-only model design, installed Qwen first; no tool execution."""
import asyncio
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from aiohttp import web
from ultron.cloud_service.scene_design import description, validate, SYSTEM

async def design_request(request):
    from ultron.backend.cloud_client import CloudClient
    from integration.local_cloud_brain import local_chat_ready
    try:text=description(await request.json())
    except (ValueError,TypeError):return web.json_response({'error':'invalid_description'},status=400)
    client=request.app.get('scene_design_client')
    if client is None:
        client=CloudClient();request.app['scene_design_client']=client
    try:
        ready=await asyncio.get_running_loop().run_in_executor(client._local_executor,local_chat_ready)
        if ready:
            result=await client.local_chat('Create a 3D JSON assembly. '+text,SYSTEM,[])
            design=validate(result['reply'])
        elif client.enabled:
            result=await client._request('POST','/api/scene-design',json_body={'description':text})
            design=validate(result['design'])
        else:raise ValueError('no_provider')
    except Exception:
        return web.json_response({'error':'scene_design_unavailable'},status=502)
    return web.json_response({'design':design})

async def cleanup(app):
    client=app.get('scene_design_client')
    if client:
        client._local_executor.shutdown(wait=False,cancel_futures=True)
        client._executor.shutdown(wait=False,cancel_futures=True)
