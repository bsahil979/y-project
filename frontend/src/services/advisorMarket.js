const reserved = new Set('A I AI THE IS FOR ON OF MY US IN INR USD ETF RSI HMM NEWS FORECAST PREDICT SHOW ME WHAT SENTIMENT PRICE STOCK TICKER OR AND ABOUT TODAY PLEASE FINBERT TIMESFM'.split(' '));

export function resolveChatSymbol(question, owned = []) {
  const aliases = new Map();
  for (const symbol of owned) {
    for (const alias of new Set([symbol, symbol.replace(/\.(NS|BO)$/i, '')])) {
      aliases.set(alias.toUpperCase(), [...(aliases.get(alias.toUpperCase()) || []), symbol]);
    }
  }
  const candidates = new Set();
  for (const token of question.match(/\$?[a-z][a-z\d]*(?:[.-][a-z\d]+)*/gi) || []) {
    const upper = token.replace(/^\$/, '').toUpperCase();
    if (aliases.has(upper)) {
      for (const symbol of aliases.get(upper)) candidates.add(symbol);
    } else if (!reserved.has(upper) && (token.startsWith('$') || /\.(ns|bo)$/i.test(token) || token === upper)) {
      candidates.add(upper);
    }
  }
  return candidates.size === 1 ? [...candidates][0] : null;
}

export function formatNewsSentiment(result, ticker) {
  if (!result.articles_analyzed) return `No scored news headlines are available for ${ticker}.`;
  const models = (result.models_used || []).join(', ');
  return `${ticker} news sentiment: ${result.overall_sentiment} (score ${result.overall_score}, based on ${result.articles_analyzed} headlines${models ? ', scored by ' + models : ''}).`;
}
