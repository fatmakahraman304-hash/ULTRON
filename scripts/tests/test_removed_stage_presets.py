"""Exercise the real stage command handler without starting devices/providers.

AST loading avoids Hub's database/device startup. Only publication/activity and
undo checkpoint side effects are replaced; validation and handlers are real.
"""
import ast
import copy
import json
import math
import re
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from aiohttp import web

ROOT = Path(__file__).resolve().parents[2]


class RemovedStagePresetsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'ultron/backend/server.py').read_text())
        functions = {'_scene_defaults', '_scene_ensure', '_stage_number',
                     '_stage_int', 'api_stage_command'}
        nodes = [n for n in tree.body if
                 isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in functions
                 or isinstance(n, ast.Assign) and any(
                     isinstance(t, ast.Name) and t.id in {'_HOLOGRAM_KINDS', '_SCENE_KINDS', '_VIDEO_TEMPLATES'}
                     for t in n.targets)]
        self.ns = dict(web=web, copy=copy, json=json, math=math, re=re, time=time,
                       uuid=uuid, _stage_publish=AsyncMock(), _scene_checkpoint=Mock())
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<real-stage-handler>', 'exec'), self.ns)
        self.hub = SimpleNamespace(stage_state={
            'mode': 'core_idle', 'hologram': {'kind': 'network', 'label': 'GÖLGE'},
            'scene': self.ns['_scene_defaults'](), 'video': {}}, on_activity=AsyncMock())
        self.ns['hub'] = self.hub

    async def command(self, **body):
        return await self.ns['api_stage_command'](SimpleNamespace(json=AsyncMock(return_value=body)))

    async def test_removed_holograms_cannot_be_created_updated_or_added_to_scenes(self):
        for kind in ('energy', 'globe'):
            for operation in ('hologram_create', 'hologram', 'hologram_show',
                              'hologram_update', 'hologram_control', 'scene_add', 'scene_update'):
                with self.subTest(kind=kind, operation=operation):
                    before = copy.deepcopy(self.hub.stage_state)
                    response = await self.command(operation=operation, kind=kind)
                    self.assertEqual(response.status, 400)
                    self.assertEqual(self.hub.stage_state, before)
        self.ns['_stage_publish'].assert_not_awaited()
        self.ns['_scene_checkpoint'].assert_not_called()

    async def test_import_and_batch_do_not_restore_removed_objects(self):
        for operation in ('scene_load', 'scene_batch'):
            for kind in ('energy', 'globe'):
                with self.subTest(operation=operation, kind=kind):
                    objects = [{'kind': 'drone'}, {'kind': kind}]
                    before = copy.deepcopy(self.hub.stage_state)
                    response = await self.command(operation=operation, scene={'objects': objects}, objects=objects)
                    self.assertEqual(response.status, 400)
                    self.assertEqual(self.hub.stage_state, before)
        self.ns['_scene_checkpoint'].assert_not_called()

    async def test_serialized_imports_are_validated_before_checkpoint(self):
        for kind in ('energy', 'globe'):
            objects = [{'kind': kind}]
            self.assertEqual((await self.command(operation='scene_load',
                scene_json=json.dumps({'objects': objects}))).status, 400)
            self.assertEqual((await self.command(operation='scene_batch',
                objects_json=json.dumps(objects))).status, 400)
        self.ns['_scene_checkpoint'].assert_not_called()

    def test_old_snapshot_normalization_does_not_resurrect_removed_objects(self):
        saved = {'objects': [{'id': 'old', 'kind': 'energy'},
                             {'id': 'earth', 'kind': 'globe'},
                             {'id': 'keep', 'kind': 'drone'}],
                 'selected_ids': ['old', 'keep'], 'selected_id': 'old'}
        before = copy.deepcopy(saved)
        live = self.ns['_scene_ensure'](copy.deepcopy(saved))
        self.assertEqual([obj['id'] for obj in live['objects']], ['keep'])
        self.assertEqual(live['selected_ids'], ['keep'])
        self.assertEqual(live['selected_id'], 'keep')
        self.assertEqual(saved, before, 'normalization must not overwrite the source project')

    async def test_removed_intro_and_energy_video_templates_are_rejected(self):
        for template in ('ultron_intro', 'energy_core'):
            with self.subTest(template=template):
                before = copy.deepcopy(self.hub.stage_state)
                response = await self.command(operation='video_create', template=template)
                self.assertEqual(response.status, 400)
                self.assertEqual(self.hub.stage_state, before)

    async def test_supported_hologram_and_video_still_work(self):
        self.assertEqual((await self.command(operation='hologram_create', kind='drone')).status, 200)
        self.assertEqual(self.hub.stage_state['hologram']['kind'], 'drone')
        self.assertEqual((await self.command(operation='video_create', template='task_complete')).status, 200)
        self.assertEqual(self.hub.stage_state['video']['template'], 'task_complete')

    def test_named_ui_and_renderer_implementations_are_removed(self):
        dashboard = (ROOT / 'ultron/frontend/src/dashboard/Dashboard.tsx').read_text()
        renderer = (ROOT / 'ultron/frontend/src/dashboard/CenterStage.tsx').read_text()
        for label in ('Enerji hologramı', 'Dünya hologramı', 'GÖLGE intro render', 'ultron_intro', 'energy_core'):
            self.assertNotIn(label, dashboard)
        for obsolete in ("kind==='globe'", "kind:'energy'", "'ultron_intro'", "'energy_core'"):
            self.assertNotIn(obsolete, renderer)


if __name__ == '__main__':
    unittest.main(verbosity=2)
