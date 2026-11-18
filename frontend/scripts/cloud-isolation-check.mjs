import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';

const names = [
  'CLOUD_SMOKE_URL', 'CLOUD_SMOKE_PUBLIC_KEY', 'CLOUD_SMOKE_USER_A',
  'CLOUD_SMOKE_PASSWORD_A', 'CLOUD_SMOKE_USER_B', 'CLOUD_SMOKE_PASSWORD_B',
];

function requireSuccess(result, operation) {
  if (result.error) throw new Error(`${operation} failed (${result.error.code || result.error.status || 'API error'}).`);
  return result.data;
}

async function checkIsolation() {
  for (const name of names) {
    if (!process.env[name]) throw new Error(`Missing ${name}. Use confirmed staging accounts.`);
  }
  const { CLOUD_SMOKE_URL: url, CLOUD_SMOKE_PUBLIC_KEY: key } = process.env;
  const destination = new URL(url);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(destination.hostname);
  if (destination.username || destination.password ||
      (destination.protocol !== 'https:' && !(destination.protocol === 'http:' && local))) {
    throw new Error('Use HTTPS for staging or a loopback URL for a local Supabase instance.');
  }
  if (!key.startsWith('sb_publishable_')) {
    const payload = key.split('.')[1];
    const role = payload ? JSON.parse(Buffer.from(payload, 'base64url').toString()).role : null;
    if (role !== 'anon') throw new Error('Use the staging project’s publishable or anon key.');
  }
  const client = () => createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
  });
  const login = async (session, suffix) => {
    const { user } = requireSuccess(await session.auth.signInWithPassword({
      email: process.env[`CLOUD_SMOKE_USER_${suffix}`],
      password: process.env[`CLOUD_SMOKE_PASSWORD_${suffix}`],
    }), `Sign-in ${suffix}`);
    return user.id;
  };
  let a = client();
  const b = client();
  const userA = await login(a, 'A');
  const userB = await login(b, 'B');
  assert.notEqual(userA, userB, 'Provide two distinct staging accounts.');

  const portfolioId = randomUUID();
  const accounts = [randomUUID(), randomUUID()];
  const holdings = [randomUUID(), randomUUID()];
  const transactionId = randomUUID();
  const marker = `Cloud isolation check ${portfolioId.slice(0, 8)}`;
  const position = (id, accountId, ticker, owner = userA) => ({
    id, user_id: owner, portfolio_id: portfolioId, account_id: accountId,
    ticker, quantity: 1, average_cost: 100, currency: 'INR',
  });

  try {
    requireSuccess(await a.from('portfolios').insert({
      id: portfolioId, user_id: userA, name: marker, base_currency: 'INR',
    }), 'Save test portfolio');
    for (const [index, broker] of ['Zerodha fixture', 'Upstox fixture'].entries()) {
      requireSuccess(await a.from('accounts').insert({
        id: accounts[index], user_id: userA, name: marker, institution: broker, currency: 'INR',
      }), `Save ${broker} account`);
      requireSuccess(await a.from('holdings').insert(
        position(holdings[index], accounts[index], ['RELIANCE.NS', 'TCS.NS'][index]),
      ), `Save ${broker} holding`);
    }
    requireSuccess(await a.from('transactions').insert({
      id: transactionId, user_id: userA, portfolio_id: portfolioId, ticker: 'INFY.NS',
      transaction_type: 'buy', quantity: 1, price: 100, currency: 'INR',
    }), 'Save manual buy');

    requireSuccess(await a.auth.signOut({ scope: 'local' }), 'Sign out A');
    a = client();
    assert.equal(await login(a, 'A'), userA);
    const ownHoldings = requireSuccess(
      await a.from('holdings').select('id,account_id').eq('portfolio_id', portfolioId), 'Reload holdings',
    );
    assert.deepEqual(ownHoldings.map(row => row.account_id).sort(), [...accounts].sort());
    assert.equal(requireSuccess(await a.from('transactions').select('id').eq('id', transactionId), 'Reload manual buy').length, 1);

    for (const [table, ids] of [['portfolios', [portfolioId]], ['accounts', accounts],
      ['holdings', holdings], ['transactions', [transactionId]]]) {
      const visible = requireSuccess(await b.from(table).select('id').in('id', ids), `Check isolation on ${table}`);
      assert.equal(visible.length, 0, `Account B could read ${table} rows owned by A.`);
    }
    const changed = requireSuccess(
      await b.from('holdings').update({ quantity: 99 }).eq('id', holdings[0]).select('id'), 'Check holding update',
    );
    assert.equal(changed.length, 0, 'Account B could change a holding owned by A.');
    const denied = await b.from('holdings').insert(position(randomUUID(), null, 'INFY.NS', userB));
    assert.equal(denied.error?.code, '42501', 'An owned row must not reference another account’s portfolio.');
  } finally {
    // Deleting our temporary portfolio also deletes its holding and transaction fixtures.
    const portfolio = await a.from('portfolios').delete().eq('id', portfolioId).eq('user_id', userA);
    const account = await a.from('accounts').delete().in('id', accounts).eq('user_id', userA);
    if (portfolio.error || account.error) {
      console.error(`Fixture cleanup needs attention: ${marker}`);
      process.exitCode = 1;
    }
    await Promise.allSettled([a.auth.signOut({ scope: 'local' }), b.auth.signOut({ scope: 'local' })]);
  }
  if (!process.exitCode) console.log('Cloud isolation check passed for two independent staging sessions.');
}

checkIsolation().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
