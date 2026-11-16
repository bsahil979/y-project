import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);


// Initialize the live Supabase client connected to the user's provisioned instance
let supabase;
if (isSupabaseConfigured) {
  supabase = createClient(supabaseUrl, supabaseAnonKey);
} else {
  // Development fallback: avoid throwing at import time so the app can render
  console.warn('VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set — using local fallback.');
  supabase = {
    auth: {
      signUp: async () => ({ data: null, error: new Error('Supabase not configured') }),
      signInWithPassword: async () => ({ data: null, error: new Error('Supabase not configured') }),
      signOut: async () => ({}),
      getUser: async () => ({ data: { user: null } }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } })
    },
    from: () => ({
      select: () => {
        const eq = async () => ({ data: [], error: new Error('Supabase not configured') });
        eq.maybeSingle = async () => ({ data: null, error: new Error('Supabase not configured') });
        eq.in = async () => ({ data: [], error: new Error('Supabase not configured') });
        return { eq, maybeSingle: eq.maybeSingle };
      },
      delete: () => ({
        eq: () => ({ in: async () => ({ data: null, error: new Error('Supabase not configured') }) }),
      }),
      upsert: async () => ({ data: null, error: new Error('Supabase not configured') })
    })
  };
}

export { supabase, isSupabaseConfigured };

const DEMO_KEY = 'smart_portfolio_mock_user';
const LOCAL_USER_KEY = 'smart_portfolio_local_user';
const notifyAuthChange = () => window.dispatchEvent(new Event('auth-change'));

export function getDemoUser() {
  try {
    const user = JSON.parse(localStorage.getItem(DEMO_KEY) || 'null');
    return user?.isDemo === true && String(user.id).startsWith('demo_') ? user : null;
  } catch {
    return null;
  }
}

function getLocalUser() {
  try {
    const user = JSON.parse(localStorage.getItem(LOCAL_USER_KEY) || 'null');
    return user?.isLocal === true && String(user.id).startsWith('usr_') ? user : null;
  } catch {
    return null;
  }
}

function requireCloudAuth() {
  if (!isSupabaseConfigured) {
    throw new Error('Cloud sign-in is not configured. Use Try Demo or configure the Supabase connection.');
  }
}

function authError(error) {
  if (['user_already_exists', 'email_exists'].includes(error?.code) || /already registered|already exists/i.test(error?.message || '')) {
    return new Error('This email is already registered. Please sign in instead.');
  }
  if (error instanceof TypeError || /fetch|network|connection/i.test(error?.message || '')) {
    return new Error('Cannot connect to cloud sign-in. Check your internet connection and whether the Supabase project is active.');
  }
  return error;
}

// Cloud credentials never fall back to a password-free local account.
// Demo mode is entered only through the explicit Try Demo button.
export const AuthService = {
  getLocalUser,

  createDemoAccount() {
    const demoUser = {
      id: `demo_${crypto.randomUUID()}`,
      email: 'demo@smartadvisor.local',
      user_metadata: { full_name: 'Demo User' },
      isDemo: true,
    };
    localStorage.setItem(DEMO_KEY, JSON.stringify(demoUser));
    localStorage.removeItem(LOCAL_USER_KEY);
    notifyAuthChange();
    return { data: { user: demoUser } };
  },

  createLocalAccount(email, fullName = '') {
    const cleanEmail = String(email || '').trim().toLowerCase();
    if (!cleanEmail || !cleanEmail.includes('@')) {
      throw new Error('Please enter a valid email address.');
    }
    const name = fullName?.trim() || cleanEmail.split('@')[0];
    const user = {
      id: `usr_${cleanEmail.replace(/[^a-zA-Z0-9]/g, '_')}`,
      email: cleanEmail,
      user_metadata: { full_name: name },
      isLocal: true,
    };
    localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(user));
    localStorage.removeItem(DEMO_KEY);
    notifyAuthChange();
    return { data: { user } };
  },

  async register(email, password, fullName) {
    requireCloudAuth();
    if (typeof password !== 'string' || password.length < 6) {
      throw new Error('Password must be at least 6 characters.');
    }
    try {
      const { data, error } = await supabase.auth.signUp({
        email: email.trim().toLowerCase(), password,
        options: {
          data: { full_name: fullName.trim(), onboarding_status: 'pending' },
          emailRedirectTo: `${window.location.origin}/auth`,
        },
      });
      if (error) throw error;
      // Confirmed duplicate signups can be obfuscated by Supabase instead
      // of returning an error. No new identity is created in that response.
      if (!data?.session && Array.isArray(data?.user?.identities) && data.user.identities.length === 0) {
        throw new Error('This email is already registered. Please sign in instead.');
      }
      localStorage.removeItem(DEMO_KEY);
      localStorage.removeItem(LOCAL_USER_KEY);
      notifyAuthChange();
      return { ...data, user: data?.session?.user || null };
    } catch (error) { throw authError(error); }
  },

  async login(email, password) {
    requireCloudAuth();
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email: email.trim().toLowerCase(), password });
      if (error) throw error;
      if (!data?.session || !data?.user) throw new Error('Cloud sign-in did not create a session. Please try again.');
      localStorage.removeItem(DEMO_KEY);
      localStorage.removeItem(LOCAL_USER_KEY);
      notifyAuthChange();
      return data;
    } catch (error) { throw authError(error); }
  },

  async logout() {
    // Local scope signs out this browser without logging out other devices.
    try {
      if (isSupabaseConfigured) {
        await supabase.auth.signOut({ scope: 'local' });
      }
    } catch (err) {
      console.warn('Remote sign out failed, clearing local session:', err);
    } finally {
      localStorage.removeItem(DEMO_KEY);
      localStorage.removeItem(LOCAL_USER_KEY);
      try {
        if (typeof localStorage.key === 'function' && typeof localStorage.length === 'number') {
          for (let i = localStorage.length - 1; i >= 0; i--) {
            const k = localStorage.key(i);
            if (k && (k.startsWith('sb-') || k.includes('auth-token'))) {
              localStorage.removeItem(k);
            }
          }
        }
      } catch {}
      notifyAuthChange();
    }
  },

  async getCurrentUser() {
    const demoUser = getDemoUser();
    if (demoUser) return { data: { user: demoUser } };
    const localUser = getLocalUser();
    if (localUser) return { data: { user: localUser } };
    if (!isSupabaseConfigured) return { data: { user: null } };
    // Cached session restores the app shell; cloud tables still enforce RLS.
    // Supabase handles persisted tokens, refresh and confirmation redirects.
    try {
      const { data, error } = await supabase.auth.getSession();
      if (error) throw authError(error);
      return { data: { user: data?.session?.user || null } };
    } catch (err) {
      if (/network|fetch|connection/i.test(err?.message || '')) {
        return { data: { user: null } };
      }
      throw err;
    }
  },
};
