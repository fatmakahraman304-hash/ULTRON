export type ConversationRequestIdentity = { request_id: string; request_key: string };

export function createConversationRequestIdentity(): ConversationRequestIdentity {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  const request_key = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
  return { request_id: crypto.randomUUID(), request_key };
}

export function isCurrentConversationResponse(
  activeRequestId: string | null | undefined,
  expectedRequestId: string,
  responseRequestId: string | null | undefined,
): boolean {
  return activeRequestId === expectedRequestId && responseRequestId === expectedRequestId;
}
