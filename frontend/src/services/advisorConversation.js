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
