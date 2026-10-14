export type ConversationRequestFailure = {
  state: 'IDLE';
  notification: string | null;
  suppressServerThinking: boolean;
};

export function conversationRequestFailure(error: unknown): ConversationRequestFailure {
  const candidate = error && typeof error === 'object'
    ? error as { name?: unknown; message?: unknown }
    : null;

  if (candidate?.name === 'AbortError') {
    return { state: 'IDLE', notification: null, suppressServerThinking: true };
  }

  const message = typeof error === 'string'
    ? error.trim()
    : typeof candidate?.message === 'string'
      ? candidate.message.trim()
      : '';

  return {
    state: 'IDLE',
    notification: message || 'İstek tamamlanamadı.',
    suppressServerThinking: false,
  };
}

export function visibleConversationState(
  localState: string,
  serverState: string,
  taskState: string,
  nativeState: string,
  suppressServerThinking: boolean,
): string {
  if (localState !== 'IDLE') return localState;
  const visibleServerState = suppressServerThinking && serverState === 'THINKING'
    ? 'IDLE'
    : serverState;
  if (visibleServerState !== 'IDLE') return visibleServerState;
  return taskState !== 'IDLE' ? taskState : nativeState;
}
