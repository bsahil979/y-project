import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { AuthService, supabase, getDemoUser } from '../services/supabaseClient';

const AuthContext = createContext({
  user: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
  register: async () => {},
  createDemoAccount: () => {},
  loginLocal: () => {},
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const authRevision = useRef(0);

  const syncUser = useCallback(async () => {
    const revision = ++authRevision.current;
    setLoading(true);
    try {
      const res = await AuthService.getCurrentUser();
      if (revision === authRevision.current) setUser(res?.data?.user || null);
    } catch {
      if (revision === authRevision.current) setUser(null);
    } finally {
      if (revision === authRevision.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    syncUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      // Do not call Supabase APIs inside its auth callback/lock.
      ++authRevision.current;
      setUser(getDemoUser() || AuthService.getLocalUser?.() || session?.user || null);
      setLoading(false);
    });

    const handleAuthChange = () => syncUser();
    window.addEventListener('auth-change', handleAuthChange);
    const handleStorageChange = (e) => {
      if (e.key === 'smart_portfolio_mock_user' || e.key === 'smart_portfolio_local_user') syncUser();
    };
    window.addEventListener('storage', handleStorageChange);

    return () => {
      ++authRevision.current;
      subscription.unsubscribe();
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [syncUser]);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const data = await AuthService.login(email, password);
      setUser(data?.user || null);
      return data;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await AuthService.logout();
    } catch (err) {
      console.warn('Logout warning:', err);
    } finally {
      setUser(null);
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email, password, fullName) => {
    setLoading(true);
    try {
      const data = await AuthService.register(email, password, fullName);
      setUser(data?.user || null);
      return data;
    } finally {
      setLoading(false);
    }
  }, []);

  const createDemoAccount = useCallback(() => {
    const result = AuthService.createDemoAccount();
    setUser(result?.data?.user || null);
    return result;
  }, []);

  const loginLocal = useCallback((email, fullName) => {
    setLoading(true);
    try {
      const result = AuthService.createLocalAccount(email, fullName);
      setUser(result?.data?.user || null);
      return result;
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, createDemoAccount, loginLocal }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
