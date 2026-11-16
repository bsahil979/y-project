// Accounts created before the signup marker already have access to their dashboard.
export function needsOnboarding(user, storage = localStorage) {
  if (!user) return false;
  const local = storage.getItem(`onboarding_completed_${user.id}`);
  if (local === 'restart') return true;
  if (user.isDemo || user.isLocal) return local !== 'true';
  return user.user_metadata?.onboarding_status === 'pending';
}
