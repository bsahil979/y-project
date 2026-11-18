/** Only whole-message small talk bypasses financial context. */
export function conversationReply(message) {
  const text = message.toLowerCase().trim().replace(/[!?.,]+/g, '').replace(/\s+/g, ' ');
  if (/^(hi|hello|hey|hiya|good morning|good afternoon|good evening)( there| advisor)?$/.test(text)) return 'Hello! How can I help you today?';
  if (/^(how are you|how are you doing|how is it going|hows it going)$/.test(text)) return "I'm here and ready to help. How are you?";
  if (/^(thanks|thank you|thank you very much|thanks a lot)$/.test(text)) return "You're welcome!";
  if (/^(bye|goodbye|see you|see you later)$/.test(text)) return 'Goodbye! Have a great day.';
  if (/^(ok|okay|got it|great|cool)$/.test(text)) return 'Got it!';
  return null;
}

/** App guidance uses actual SmartPortfolio routes and supported actions. */
export function appHelpReply(message) {
  if (/\bgoals?\b/i.test(message) && /\b(section|page|tab|feature|app|how|explain|tell me about)\b/i.test(message)) {
    return '**Goals** helps you plan toward a target amount by a chosen date.\n\nOpen [Plan → Goals](/dashboard/planning/goals) and enter a name, target amount, current savings, monthly contribution, target date and currency.\n\nThe page runs a Monte Carlo simulation to estimate possible outcomes and the chance of reaching your target. These estimates depend on the simulation assumptions and market history. You can review different goals from the same page.';
  }
  if (!/\b(how|where|help|connect|add)\b/i.test(message)) return null;
  if (/\b(add|record|track)\b.*\breal estate\b/i.test(message)) {
    return 'Open [Add real estate](/dashboard/portfolio?addAsset=real_estate), enter the property name, currency, value and valuation date, then save. Record any outstanding mortgage separately under Liabilities.';
  }
  if (/\b(connect|add|import)\b.*\b(broker|brokerage|account|upstox|zerodha)\b/i.test(message)) {
    return 'Open [Manage holdings](/dashboard/portfolio) and choose **Add account / Import portfolio**. Select your broker, complete authorization, fetch your holdings and review the import before saving. You can also import a CSV statement there.';
  }
  return null;
}
