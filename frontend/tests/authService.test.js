import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { it } from 'node:test';

function loadAuth(env = {}, auth = {}) {
  const values = new Map();
  const events = [];
  const source = readFileSync(new URL('../src/services/supabaseClient.js', import.meta.url), 'utf8')
    .replace("import { createClient } from '@supabase/supabase-js';", '')
    .replaceAll('import.meta.env', 'env')
    .replace('export { supabase, isSupabaseConfigured };', '')
    .replace('export function getDemoUser', 'function getDemoUser')
    .replace('export const AuthService =', 'globalThis.AuthService =');
  const context = vm.createContext({ env, createClient: () => ({ auth }),
    console: { warn() {} }, Event, setTimeout, crypto,
    localStorage: { getItem: key => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) },
    window: { location: { origin: 'http://localhost:5173' }, dispatchEvent: event => events.push(event.type) } });
  vm.runInContext(source, context);
  return { service: context.AuthService, events, values };
}

it('missing cloud configuration rejects credentials but explicit demo still works', async () => {
  const { service } = loadAuth();
  await assert.rejects(service.login('test@example.com', 'Example123'), /not configured/);
  await assert.rejects(service.register('test@example.com', 'Example123', 'Test'), /not configured/);
  const demo = service.createDemoAccount().data.user;
  assert.equal(demo.isDemo, true);
  assert.equal((await service.getCurrentUser()).data.user.id, demo.id);
  await service.logout();
  assert.equal((await service.getCurrentUser()).data.user, null);
});

it('cloud signup requiring email confirmation does not report an authenticated user', async () => {
  const { service } = loadAuth({ VITE_SUPABASE_URL: 'configured', VITE_SUPABASE_ANON_KEY: 'configured' }, {
    signUp: async () => ({ data: { user: { id: 'pending' }, session: null }, error: null }),
  });
  assert.equal((await service.register('test@example.com', 'Example123', 'Test')).user, null);
});

it('cloud signup with a session returns its user and notifies the auth context', async () => {
  const { service, events } = loadAuth({ VITE_SUPABASE_URL: 'configured', VITE_SUPABASE_ANON_KEY: 'configured' }, {
    signUp: async () => ({ data: { user: { id: 'signed-in' }, session: { user: { id: 'signed-in' } } }, error: null }),
  });
  assert.equal((await service.register('test@example.com', 'Example123', 'Test')).user.id, 'signed-in');
  assert.ok(events.includes('auth-change'));
});

const configured = { VITE_SUPABASE_URL: 'configured', VITE_SUPABASE_ANON_KEY: 'configured' };

it('successful cloud login replaces a demo session and survives session restore', async () => {
  const user = { id: 'cloud-user' };
  const { service, values } = loadAuth(configured, {
    signInWithPassword: async () => ({ data: { user, session: { user } }, error: null }),
    getSession: async () => ({ data: { session: { user } }, error: null }),
  });
  service.createDemoAccount();
  assert.equal((await service.login('test@example.com', 'Example123')).user.id, user.id);
  assert.equal(values.has('smart_portfolio_mock_user'), false);
  assert.equal((await service.getCurrentUser()).data.user.id, user.id);
});

it('invalid cloud credentials never create a local login even with the legacy fallback flag', async () => {
  const { service, values } = loadAuth({ ...configured, VITE_ENABLE_LOCAL_AUTH_FALLBACK: 'true' }, {
    signInWithPassword: async () => ({ data: {}, error: new Error('Invalid login credentials') }),
  });
  await assert.rejects(service.login('test@example.com', 'wrong'), /Invalid login credentials/);
  assert.equal(values.size, 0);
});

it('legacy mock accounts cannot masquerade as cloud sessions', async () => {
  const { service, values } = loadAuth(configured, {
    getSession: async () => ({ data: { session: null }, error: null }),
  });
  values.set('smart_portfolio_mock_user', JSON.stringify({id:'cloud-shaped-id',isDemo:false}));
  assert.equal((await service.getCurrentUser()).data.user, null);
});

it('signup specifies the app callback and leaves confirmation-required users signed out', async () => {
  let request;
  const { service, values } = loadAuth(configured, {
    signUp: async (input) => { request = input; return {data:{session:null,user:{id:'pending'}}}; },
  });
  service.createDemoAccount();
  assert.equal((await service.register(' test@example.com ', 'Example123', ' Test ')).user, null);
  assert.equal(request.email, 'test@example.com');
  assert.equal(request.options.emailRedirectTo, 'http://localhost:5173/auth');
  assert.equal(values.has('smart_portfolio_mock_user'), false);
});

it('cloud logout uses local scope and clears demo state after success', async () => {
  let scope;
  const { service, values } = loadAuth(configured, {
    signOut: async (options) => { scope = options.scope; return {error:null}; },
  });
  service.createDemoAccount();
  await service.logout();
  assert.equal(scope, 'local');
  assert.equal(values.has('smart_portfolio_mock_user'), false);
});

it('network failures produce a useful cloud connection error', async () => {
  const { service } = loadAuth(configured, {
    signInWithPassword: async () => { throw new Error('Failed to fetch'); },
  });
  await assert.rejects(service.login('test@example.com', 'Example123'), /Cannot connect to cloud sign-in/);
});


it('signup rejects passwords below six characters before calling Supabase', async () => {
  let calls = 0;
  const { service } = loadAuth(configured, { signUp: async () => { calls++; } });
  for (const password of ['', 'abcde']) {
    await assert.rejects(service.register('test@example.com', password, 'Test'), /at least 6 characters/);
  }
  assert.equal(calls, 0);
});

it('signup accepts a six-character password and normalizes the email', async () => {
  let request;
  const { service } = loadAuth(configured, {
    signUp: async input => { request = input; return { data: { user: { id: 'new', identities: [{id:'identity'}] }, session: null } }; },
  });
  await service.register(' TEST@Example.com ', 'abcdef', 'Test');
  assert.equal(request.email, 'test@example.com');
  assert.equal(request.password, 'abcdef');
});

it('obfuscated duplicate signup shows an error and preserves the current demo', async () => {
  const { service, values, events } = loadAuth(configured, {
    signUp: async () => ({ data: {user: {id:'obfuscated', identities:[]}, session:null}, error:null }),
  });
  service.createDemoAccount();
  const demo = values.get('smart_portfolio_mock_user');
  const eventCount = events.length;
  await assert.rejects(service.register('test@example.com', 'abcdef', 'Test'), /email is already registered/);
  assert.equal(values.get('smart_portfolio_mock_user'), demo);
  assert.equal(events.length, eventCount);
});

it('explicit Supabase duplicate errors have the same friendly message', async () => {
  for (const error of [{code:'user_already_exists'}, {code:'email_exists'}, {message:'User already registered'}]) {
    const { service } = loadAuth(configured, { signUp: async () => ({data:null,error}) });
    await assert.rejects(service.register('test@example.com', 'abcdef', 'Test'), /email is already registered/);
  }
});
