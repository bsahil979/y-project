import assert from 'node:assert/strict';
import { it } from 'node:test';
import { chatHistoryKey, readChatHistory, writeChatHistory, createChatSession, readChatSessions, sessionHistoryKey } from '../src/services/advisorHistory.js';

it('restores history after navigation and isolates users, portfolios and currencies', () => {
  const data = new Map();
  const storage = { getItem: (key) => data.get(key), setItem: (key, value) => data.set(key, value) };
  const key = chatHistoryKey('user1', 'portfolio1', 'INR');
  const messages = [{ role: 'user', text: 'Tell me about Reliance' }, { role: 'assistant', text: '**Reliance**: 12 shares.' }];
  writeChatHistory(key, messages, storage);
  assert.deepEqual(readChatHistory(key, storage), messages);
  for (const other of [chatHistoryKey('user2', 'portfolio1', 'INR'), chatHistoryKey('user1', 'portfolio2', 'INR'), chatHistoryKey('user1', 'portfolio1', 'USD')]) assert.deepEqual(readChatHistory(other, storage), []);
  assert.equal(chatHistoryKey(null, 'portfolio1', 'INR'), null);
});

it('handles corrupt and unavailable storage without crashing chat', () => {
  assert.deepEqual(readChatHistory('key', { getItem: () => '{bad' }), []);
  writeChatHistory('key', [], { setItem: () => { throw new Error('full'); } });
});

it('new chats start empty and preserve previous conversations for reopening', () => {
  const data = new Map();
  const storage = { getItem: (key) => data.get(key), setItem: (key, value) => data.set(key, value) };
  const key = chatHistoryKey('user', 'portfolio', 'INR');
  writeChatHistory(key, [{ role: 'user', text: 'My old question' }], storage);
  const next = createChatSession(key, storage);
  assert.equal(readChatSessions(key, storage).length, 2);
  assert.deepEqual(readChatHistory(sessionHistoryKey(key, next.session.id), storage), []);
  assert.equal(readChatHistory(sessionHistoryKey(key, 'original'), storage)[0].text, 'My old question');
  assert.equal(readChatSessions(chatHistoryKey('other', 'portfolio', 'INR'), storage).length, 1);
});
