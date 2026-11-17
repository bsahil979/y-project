import { createId } from './portfolioWorkspace.js';
import { validateTransactionLedger } from './portfolioLedger.js';

export function parseCSV(text) {
  const rows = [];
  let row = [], cell = '', quoted = false;
  const input = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    if (c === '"') {
      if (quoted && input[i + 1] === '"') { cell += '"'; i++; }
      else if (quoted || !cell) quoted = !quoted;
      else throw new Error('Unexpected quote in CSV.');
    } else if (!quoted && (c === ',' || c === '\n' || c === '\r')) {
      row.push(cell); cell = '';
      if (c !== ',') {
        if (row.some(value => value.trim())) rows.push(row);
        row = [];
        if (c === '\r' && input[i + 1] === '\n') i++;
      }
    } else cell += c;
  }
  if (quoted) throw new Error('Unclosed quoted CSV field.');
  row.push(cell);
  if (row.some(value => value.trim())) rows.push(row);
  if (rows.length < 2) throw new Error('Include column headings and at least one row.');
  const headers = rows.shift().map(h => h.trim().toLowerCase().replace(/[ -]+/g, '_'));
  if (new Set(headers).size !== headers.length) throw new Error('Duplicate column headings.');
  return rows.map((values, i) => {
    if (values.length !== headers.length) throw new Error('Column count mismatch at row ' + (i + 2));
    return Object.fromEntries(headers.map((h, j) => [h, values[j].trim()]));
  });
}

export function normalizeImport(rows, mode) {
  if (!rows.length) throw new Error('No holdings returned.');
  return rows.map((r, index) => {
    const fail = message => { throw new Error('Row ' + (index + 1) + ': ' + message); };
    let ticker = String(r.ticker || r.trading_symbol || r.tradingsymbol || r.symbol || '').trim().toUpperCase();
    const exchange = String(r.exchange || '').toUpperCase();
    if (exchange && !['NSE', 'BSE'].includes(exchange)) fail('Only NSE/BSE equities are supported for exchange imports.');
    if (r.instrument_token && !/^(NSE|BSE)_EQ\|/.test(r.instrument_token)) fail('Unsupported instrument type.');
    if (exchange && !ticker.endsWith('.NS') && !ticker.endsWith('.BO')) {
      if (exchange === 'BSE' && !/^\d+$/.test(ticker)) fail('Use the numeric BSE symbol in the ticker column.');
      ticker += exchange === 'NSE' ? '.NS' : '.BO';
    }
    if (!/^[A-Z0-9&^][A-Z0-9&.\-^]*$/.test(ticker)) fail('A valid ticker is required.');
    const currency = String(r.currency || (exchange || ticker.endsWith('.NS') || ticker.endsWith('.BO') ? 'INR' : '')).toUpperCase();
    if (!['INR', 'USD'].includes(currency)) fail('Specify INR or USD currency, or an NSE/BSE exchange.');
    if (/\.(NS|BO)$/.test(ticker) && currency !== 'INR') fail('Indian stocks must use INR.');
    const number = (value, label) => {
      if (value == null || String(value).trim() === '') fail(label + ' is required.');
      const result = Number(String(value).replaceAll(',', ''));
      if (!Number.isFinite(result) || result < 0) fail(label + ' must be a non-negative number.');
      return result;
    };
    const quantity = number(r.quantity || r.qty, 'Quantity');
    if (quantity <= 0) fail('Quantity must be positive.');
    const price = number(r.average_cost ?? r.average_price ?? r.avg_price ?? r.price, 'Price');
    const record = {ticker, currency, quantity, price};
    if (mode === 'trades') {
      record.transaction_type = String(r.transaction_type || r.type || '').toLowerCase();
      if (!['buy', 'sell'].includes(record.transaction_type)) fail('Trade type must be buy or sell.');
      record.transaction_date = r.transaction_date || r.date;
      const date = record.transaction_date;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '') || !Number.isFinite(Date.parse(date)) ||
          new Date(date).toISOString().slice(0, 10) !== date) fail('Use a valid YYYY-MM-DD trade date.');
      if (price <= 0) fail('Trade price must be positive.');
      record.fees = number(r.fees || 0, 'Fees');
    }
    return record;
  });
}

export function applyPortfolioImport(workspace, rows, mode, name, options = {}) {
  // A dedicated snapshot portfolio prevents current holdings being counted again as historical buys.
  const portfolioName = name.trim();
  const institution = String(options.institution || '').trim();
  const accountName = String(options.accountName || portfolioName).trim();
  const target = options.portfolioId ? workspace.portfolios.find(p => p.id === options.portfolioId) : null;
  if (options.portfolioId && !target) throw new Error('Select an existing portfolio.');
  if (!accountName) throw new Error('Enter an account label.');
  if (!rows.length) throw new Error('No records to import.');
  if (institution && workspace.accounts.some(a => a.institution === institution && a.name.toLowerCase() === accountName.toLowerCase())) throw new Error('This broker account label already exists. Use a distinct label for another account.');
  if (!portfolioName) throw new Error('Enter a portfolio name.');
  if (!target && workspace.portfolios.some(p => p.name.toLowerCase() === portfolioName.toLowerCase())) {
    throw new Error('That portfolio already exists. Use a different name for a new snapshot.');
  }
  const signature = records => JSON.stringify(records.map(r => JSON.stringify([
    r.ticker, Number(r.quantity), Number(r.price ?? r.average_cost), r.currency,
    r.transaction_type || '', r.transaction_date || '', Number(r.fees || 0),
  ])).sort());
  const incoming = signature(rows);
  for (const portfolio of workspace.portfolios) {
    const existing = (mode === 'holdings' ? workspace.holdings : workspace.transactions).filter(r => r.portfolio_id === portfolio.id);
    if (!institution && signature(existing) === incoming) throw new Error('These records already exist in ' + portfolio.name + '.');
  }
  const portfolioId = target?.id || createId(), accountId = createId();
  const base = {portfolio_id: portfolioId, account_id: accountId};
  const holdings = mode === 'holdings' ? rows.map(r => ({
    ...base, id:createId(), ticker:r.ticker, currency:r.currency, quantity:r.quantity, average_cost:r.price,
    ...(r.asset_type === 'mutual_fund' ? {asset_type:r.asset_type, asset_name:r.asset_name, manual_value:r.manual_value, valuation_date:r.valuation_date, valuation_source:r.valuation_source} : {}),
  })) : [];
  const transactions = mode === 'trades' ? rows.map(r => ({
    ...base, ...r, id:createId(), created_at:new Date().toISOString(),
  })) : [];
  const error = validateTransactionLedger(transactions, holdings);
  if (error) throw new Error(error.message + ' Import complete trade history starting with purchases.');
  return {...workspace, selectedPortfolioId:portfolioId,
    portfolios:target ? workspace.portfolios : [...workspace.portfolios, {id:portfolioId, name:portfolioName, base_currency:rows[0]?.currency || 'INR'}],
    accounts:[...workspace.accounts, {id:accountId, name:accountName, ...(institution ? {institution} : {}), account_type:'brokerage', currency:rows[0]?.currency || 'INR'}],
    holdings:[...workspace.holdings, ...holdings], transactions:[...workspace.transactions, ...transactions]};
}


export function normalizeBrokerPortfolio(snapshot) {
  const rows = [], warnings = [], funds = new Map(), seen = new Set();
  const sections = snapshot.sections || {};
  for (const r of sections.equities?.data || []) {
    try {rows.push(...normalizeImport([r], 'holdings'));}
    catch (e) {warnings.push(`Equity ${r.trading_symbol || r.instrument_token || 'unknown'}: ${e.message}`);}
  }
  for (const r of sections.mutual_funds?.data || []) {
    try {
      const isin = String(r.instrument_key || '').trim().toUpperCase();
      const number = (v, name, positive = false) => {
        if (v == null || String(v).trim() === '' || !Number.isFinite(Number(v)) || (positive ? Number(v) <= 0 : Number(v) < 0)) throw new Error(`${name} unavailable or invalid`);
        return Number(v);
      };
      if (!/^IN[A-Z0-9]{10}$/.test(isin)) throw new Error('Valid fund ISIN required');
      const quantity = number(r.quantity, 'Units', true), price = number(r.average_price, 'Average cost');
      const nav = number(r.last_price, 'NAV', true), date = r.last_price_date;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '') || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0,10) !== date) throw new Error('NAV date unavailable or invalid');
      const key = JSON.stringify([isin, r.folio || '']);
      if (seen.has(key)) throw new Error('Duplicate fund/folio row excluded');
      seen.add(key);
      const existing = funds.get(isin);
      if (existing) {
        existing.price = (existing.price * existing.quantity + price * quantity) / (existing.quantity + quantity);
        existing.quantity += quantity;
        if (date > existing.valuation_date) {existing.manual_value = nav; existing.valuation_date = date;}
      } else funds.set(isin, {ticker:'MF:' + isin, asset_type:'mutual_fund', asset_name:String(r.fund || isin), quantity, price,
        currency:'INR', manual_value:nav, valuation_date:date, valuation_source:'Upstox NAV'});
    } catch(e) {warnings.push(`Mutual fund ${r.fund || r.instrument_key || 'unknown'}: ${e.message}`);}
  }
  return {rows:[...rows, ...funds.values()], warnings};
}
