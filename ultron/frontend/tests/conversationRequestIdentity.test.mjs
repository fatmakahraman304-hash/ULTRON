import assert from 'node:assert/strict';
import test from 'node:test';
import { createConversationRequestIdentity, isCurrentConversationResponse } from '../src/dashboard/conversationRequestIdentity.ts';

test('each chat request has an independent UUID and unguessable cancel key', () => {
  const first = createConversationRequestIdentity();
  const second = createConversationRequestIdentity();
  assert.match(first.request_id, /^[0-9a-f-]{36}$/i);
  assert.match(first.request_key, /^[0-9a-f]{64}$/);
  assert.notEqual(first.request_id, second.request_id);
  assert.notEqual(first.request_key, second.request_key);
});

test('late response from an interrupted request cannot be accepted as the active turn', () => {
  assert.equal(isCurrentConversationResponse('new-id', 'old-id', 'old-id'), false);
  assert.equal(isCurrentConversationResponse('new-id', 'new-id', 'old-id'), false);
  assert.equal(isCurrentConversationResponse('new-id', 'new-id', 'new-id'), true);
});
