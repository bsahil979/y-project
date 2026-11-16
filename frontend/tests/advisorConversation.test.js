import assert from 'node:assert/strict';
import { it } from 'node:test';
import { conversationReply } from '../src/services/advisorConversation.js';

it('answers whole-message small talk immediately', () => {
  for (const message of ['hi', 'Hello!', ' hey there ', 'Good morning', 'How are you?', 'Thank you!', 'bye', 'okay']) {
    assert.equal(typeof conversationReply(message), 'string');
  }
});

it('preserves analytics routing for financial questions even with a greeting', () => {
  for (const message of ['hi, tell me about Reliance', 'hello what is my portfolio risk?', 'How are my stocks doing?', 'thanks, should I rebalance?', 'Tell me about AAPL', 'What is my allocation?']) {
    assert.equal(conversationReply(message), null);
  }
});
