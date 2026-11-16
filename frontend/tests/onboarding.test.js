import test from 'node:test';
import assert from 'node:assert/strict';
import { needsOnboarding } from '../src/services/onboarding.js';

test('fresh browsers skip setup for returning cloud users and resume unfinished registration', () => {
  const freshBrowser = { getItem: () => null };
  const user = { id: 'cloud' };
  assert.equal(needsOnboarding(user, freshBrowser), false);
  user.user_metadata = { onboarding_status: 'pending' };
  assert.equal(needsOnboarding(user, freshBrowser), true);
  user.user_metadata.onboarding_status = 'complete';
  assert.equal(needsOnboarding(user, freshBrowser), false);
  assert.equal(needsOnboarding(user, {getItem: () => 'restart'}), true);
});
