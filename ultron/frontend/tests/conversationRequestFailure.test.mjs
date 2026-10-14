import assert from 'node:assert/strict';
import test from 'node:test';
import { conversationRequestFailure, visibleConversationState } from '../src/dashboard/conversationRequestFailure.ts';

test('user interruption clears the thinking state without showing an abort error', () => {
  assert.deepEqual(
    conversationRequestFailure({ name: 'AbortError', message: 'The operation was aborted.' }),
    { state: 'IDLE', notification: null, suppressServerThinking: true },
  );
});

test('browser AbortError is classified as a silent interruption', () => {
  assert.deepEqual(
    conversationRequestFailure(new DOMException('The operation was aborted.', 'AbortError')),
    { state: 'IDLE', notification: null, suppressServerThinking: true },
  );
});

test('ordinary request failures clear thinking and remain visible', () => {
  assert.deepEqual(
    conversationRequestFailure(new Error('Network connection lost')),
    { state: 'IDLE', notification: 'Network connection lost', suppressServerThinking: false },
  );
});

test('timeouts are reported instead of being mistaken for user interruption', () => {
  assert.deepEqual(
    conversationRequestFailure({ name: 'TimeoutError', message: 'Request timed out' }),
    { state: 'IDLE', notification: 'Request timed out', suppressServerThinking: false },
  );
});

test('unknown failures produce a useful fallback', () => {
  assert.deepEqual(conversationRequestFailure(undefined), {
    state: 'IDLE',
    notification: 'İstek tamamlanamadı.',
    suppressServerThinking: false,
  });
});

test('cancelled request does not inherit a stale websocket THINKING state', () => {
  assert.equal(visibleConversationState('IDLE', 'THINKING', 'IDLE', 'IDLE', true), 'IDLE');
});

test('real task and native listening states are still visible after chat interruption', () => {
  assert.equal(visibleConversationState('IDLE', 'WORKING', 'IDLE', 'IDLE', true), 'WORKING');
  assert.equal(visibleConversationState('IDLE', 'THINKING', 'WORKING', 'IDLE', true), 'WORKING');
  assert.equal(visibleConversationState('IDLE', 'THINKING', 'IDLE', 'LISTENING', true), 'LISTENING');
});
