export function chatHistoryKey(userId, portfolioId, currency) {
  return userId && portfolioId && currency ? `spa_chat_v1:${JSON.stringify([userId, portfolioId, currency])}` : null;
}

export function readChatHistory(key, storage = globalThis.localStorage) {
  try {
    const rows = JSON.parse(storage?.getItem(key) || '[]');
    return Array.isArray(rows) ? rows.filter((row) => ['user', 'assistant'].includes(row.role) && typeof row.text === 'string') : [];
  } catch { return []; }
}

export function writeChatHistory(key, messages, storage = globalThis.localStorage) {
  if (!key) return;
  try { storage?.setItem(key, JSON.stringify(messages)); } catch { /* Storage may be disabled or full. */ }
}

export function readChatSessions(key, storage = globalThis.localStorage) {
  if (!key) return [{ id: 'original', title: 'Original chat' }];
  try {
    const saved = JSON.parse(storage?.getItem(`${key}:sessions`) || 'null');
    if (Array.isArray(saved) && saved.length) return saved.filter((row) => typeof row.id === 'string' && typeof row.title === 'string');
  } catch { /* Restore legacy history as the original conversation. */ }
  return [{ id: 'original', title: 'Original chat' }];
}

export function sessionHistoryKey(key, id) {
  return !key ? null : id === 'original' ? key : `${key}:session:${id}`;
}

export function createChatSession(key, storage = globalThis.localStorage) {
  const sessions = readChatSessions(key, storage);
  const session = { id: crypto.randomUUID(), title: `Chat ${sessions.length + 1}` };
  const next = [...sessions, session];
  try { if (key) storage?.setItem(`${key}:sessions`, JSON.stringify(next)); } catch { /* Keep usable in memory. */ }
  return { session, sessions: next };
}
