import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
test('advisor renders GFM allocation tables, rounds display percentages and omits raw HTML',async()=>{
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},optimizeDeps:{noDiscovery:true,include:[]}});
 try {
  const {default:Markdown}=await server.ssrLoadModule('/src/components/AdvisorMarkdown.jsx');
  const text='Suggested allocation\n\n| Holding | Current | Target |\n| --- | --- | --- |\n| TCS.NS | 26.5937% | 13.3176436804% |\n\n<script>alert(1)</script>';
  const html=renderToStaticMarkup(React.createElement(Markdown,null,text));
  assert.match(html,/<table/);assert.match(html,/<th /);assert.match(html,/26.59%/);assert.match(html,/13.32%/);
  assert.doesNotMatch(html,/<script/);assert.match(html,/overflow-x-auto/);
  assert.match(text,/13.3176436804%/);
 } finally {await server.close();}
});
