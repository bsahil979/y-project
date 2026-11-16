import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { readChatHistory, writeChatHistory } from '../src/services/advisorHistory.js';

test('SSE correction and grounding metadata survive split chunks and chat persistence', async () => {
  const server = await createServer({ server:{middlewareMode:true}, appType:'custom', logLevel:'silent' });
  const originalFetch = globalThis.fetch;
  const report = {status:'mismatch_detected',mismatches:[{correction:'Sharpe ratio: 1.23'}]};
  const payload = {content:'Sharpe ratio: 9.8.\n\nQuant engine corrections: 1.23',
    done:true,grounding_check:report,advisor_provenance:{analysis_id:'test'}};
  const bytes = new TextEncoder().encode('data: '+JSON.stringify(payload)+'\n\n');
  globalThis.fetch = async () => ({ok:true,body:new ReadableStream({start(controller) {
    controller.enqueue(bytes.slice(0,17));controller.enqueue(bytes.slice(17));controller.close();
  }})});
  try {
    const { ChatService } = await server.ssrLoadModule('/src/services/api.js');
    let text='',metadata;
    await ChatService.sendMessageStream({query:'risk'}, (chunk, meta) => {text+=chunk||'';if(meta)metadata=meta;});
    assert.equal(text,payload.content);
    assert.deepEqual(metadata.grounding_check,report);
    const data = new Map();
    const storage = {getItem:key=>data.get(key),setItem:(key,value)=>data.set(key,value)};
    writeChatHistory('chat',[{role:'assistant',text,grounding_check:metadata.grounding_check}],storage);
    assert.deepEqual(readChatHistory('chat',storage)[0].grounding_check,report);
  } finally {globalThis.fetch=originalFetch;await server.close();}
});
