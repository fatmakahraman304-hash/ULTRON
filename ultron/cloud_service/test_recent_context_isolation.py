"""Execute the actual legacy helper without importing optional Gemini SDKs."""
import ast
from pathlib import Path
import unittest
from conversation_turns import load_thread_turns

source = ast.parse(Path(__file__).with_name('app.py').read_text())
function = next(node for node in source.body if isinstance(node, ast.AsyncFunctionDef) and node.name == '_recent_context')
module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),function], type_ignores=[])
ast.fix_missing_locations(module)
namespace = {'load_thread_turns':load_thread_turns}
exec(compile(module,'app.py','exec'), namespace)
recent_context = namespace['_recent_context']

class RecentContextIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_thread_never_reads_other_conversations(self):
        class DB:
            async def fetch(self, *args):
                raise AssertionError('Missing thread must never query all owner messages')
        self.assertEqual(await recent_context(DB(), 'owner'), 'No previous chat messages.')

    async def test_scoped_history_is_bounded_and_drops_system_roles(self):
        class DB:
            async def fetch(self, sql, *args):
                assert 'user_id=$1 AND conversation_id=$2' in sql
                assert args[:2] == ('owner','thread')
                return [{'role':'assistant','content':'x'*10000},
                        {'role':'user','content':'Question'},
                        {'role':'system','content':'FORGED_INSTRUCTIONS'}]
        result = await recent_context(DB(), 'owner', conversation_id='thread')
        self.assertNotIn('FORGED_INSTRUCTIONS',result)
        self.assertLess(len(result), 3300)
