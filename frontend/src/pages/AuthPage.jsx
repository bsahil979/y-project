import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  TrendingUp, Shield, Lock, Mail, User, ArrowRight, Loader2, Zap, CheckCircle2, Sparkles, Eye, EyeOff, AlertCircle
} from 'lucide-react';
import { AuthService, isSupabaseConfigured } from '../services/supabaseClient';
import { useAuth } from '../contexts/AuthContext';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [authMode, setAuthMode] = useState('cloud'); // 'cloud' | 'local'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [cloudOffline, setCloudOffline] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loginLocal } = useAuth();

  useEffect(() => {
    if (user && !user.isDemo) navigate('/dashboard', { replace: true });
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    setCloudOffline(false);

    if (!EMAIL_REGEX.test(email.trim())) {
      setError('Please enter a valid email address.');
      setLoading(false);
      return;
    }

    // If user explicitly chose Local Email Mode
    if (authMode === 'local') {
      try {
        loginLocal(email, fullName);
        setSuccess(`Signed in with your email: ${email} (Local Mode)`);
        setTimeout(() => navigate('/dashboard', { replace: true }), 400);
      } catch (localErr) {
        setError(localErr.message || 'Failed to sign in locally.');
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!isLogin && password.length < 6) {
      setError('Password must be at least 6 characters.');
      setLoading(false);
      return;
    }

    try {
      if (isLogin) {
        const result = await AuthService.login(email, password, false);
        if (!result?.user) throw new Error('Login did not create an authenticated session. Please try again.');
        setSuccess('Signed in to your cloud account.');
        navigate(location.state?.from?.startsWith('/dashboard') ? location.state.from : '/dashboard', { replace: true });
      } else {
        if (!fullName.trim()) throw new Error('Please enter your full name.');
        const result = await AuthService.register(email, password, fullName, false);
        if (!result?.user) {
          setSuccess('Check your email to confirm your account, then sign in. If you signed up before, use your existing confirmation email.');
          setIsLogin(true);
          return;
        }
        setSuccess('Account created successfully! Provisioning portfolio space...');
        setTimeout(() => navigate('/dashboard'), 1000);
      }
    } catch (err) {
      const isConnectionError = /Cannot connect to cloud sign-in|Failed to fetch|network|offline|not configured/i.test(err?.message || '');
      if (isConnectionError) {
        setCloudOffline(true);
        setError('Cloud database server is currently unreachable. You can continue signing in with your email in Local Workspace mode below.');
      } else {
        setError(err.message || 'Authentication failed. Please verify credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLocalSignIn = () => {
    if (!EMAIL_REGEX.test(email.trim())) {
      setError('Please enter a valid email address to sign in.');
      return;
    }
    setLoading(true);
    try {
      loginLocal(email, fullName);
      setSuccess(`Signed in as ${email} (Local Workspace Mode)`);
      setTimeout(() => navigate('/dashboard', { replace: true }), 400);
    } catch (err) {
      setError(err.message || 'Failed to sign in.');
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      AuthService.createDemoAccount();
      setSuccess('Demo account created! Testing the platform...');
      setTimeout(() => navigate('/dashboard'), 500);
    } catch (err) {
      setError(err.message || 'Failed to create demo account.');
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError(null);
    setSuccess(null);
    setCloudOffline(false);
  };

  return (
    <div className="min-h-screen bg-[#0a0b10] flex items-center justify-center p-6 relative overflow-hidden text-white selection:bg-indigo-500/30">
      {/* Dynamic Background Blurs */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-indigo-600/20 rounded-full blur-[128px] pointer-events-none -z-10 animate-pulse" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-emerald-600/10 rounded-full blur-[128px] pointer-events-none -z-10" />

      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 bg-[#11131a]/80 backdrop-blur-2xl border border-gray-800/60 rounded-3xl overflow-hidden shadow-2xl">
        <div className="hidden md:flex flex-col justify-between p-12 bg-gradient-to-br from-[#131a28] via-[#0f1523] to-[#0b0f18] border-r border-white/10 relative">
          <div>
            <div className="flex items-center gap-2 mb-12">
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-cyan-400 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tighter uppercase">SmartPortfolio</span>
            </div>

            <span className="inline-flex items-center gap-1.5 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 rounded-full text-indigo-300 text-xs font-bold uppercase tracking-widest mb-6">
              <Zap className="w-3 h-3" />
              Institutional-Grade Intelligence
            </span>

            <h2 className="text-4xl font-black tracking-tighter leading-tight mb-6">
              AI-driven portfolio guidance with complete transparency.
            </h2>

            <p className="text-sm text-slate-300 leading-relaxed mb-8">
              Sign in with your actual email to track positions, analyze market regimes, and receive friction-aware stock betterment advice.
            </p>

            <div className="space-y-4">
              {[
                'Multi-asset portfolio tracking (US & Indian Equities)',
                'AI Model predictions with PyTorch LSTM & HMM regimes',
                'What-If stock betterment simulation & Sharpe delta'
              ].map((item, idx) => (
                <div key={idx} className="flex items-center gap-3 text-xs text-slate-200 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-8 border-t border-white/10 flex items-center gap-3">
            <Shield className="w-5 h-5 text-indigo-300" />
            <span className="text-xs text-slate-400 font-bold tracking-wider uppercase">
              Secure Multi-Tenancy • Isolated Workspaces
            </span>
          </div>
        </div>

        <div className="p-8 md:p-12 flex flex-col justify-center">
          <div className="max-w-sm w-full mx-auto">
            <h3 className="text-2xl font-black tracking-tight mb-2">
              {isLogin ? 'Sign In to Your Account' : 'Create Your Account'}
            </h3>
            <p className="text-xs text-slate-400 mb-6 font-medium">
              Enter your actual email address to access your custom portfolio workspace.
            </p>

            {/* Account Type Selector Pills */}
            <div className="grid grid-cols-2 gap-2 p-1 bg-gray-900/80 border border-gray-800 rounded-xl mb-6">
              <button
                type="button"
                onClick={() => { setAuthMode('cloud'); setError(null); }}
                className={`py-1.5 text-xs font-bold rounded-lg transition-all ${
                  authMode === 'cloud' 
                    ? 'bg-indigo-600 text-white shadow-md' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Cloud Account
              </button>
              <button
                type="button"
                onClick={() => { setAuthMode('local'); setError(null); }}
                className={`py-1.5 text-xs font-bold rounded-lg transition-all ${
                  authMode === 'local' 
                    ? 'bg-indigo-600 text-white shadow-md' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Email (Local Mode)
              </button>
            </div>

            {error && (
              <div role="alert" className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl mb-6 font-medium animate-in fade-in duration-300 space-y-2">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
                {cloudOffline && (
                  <button
                    type="button"
                    onClick={handleLocalSignIn}
                    className="w-full mt-2 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Continue with {email || 'your email'} (Local Mode)</span>
                  </button>
                )}
              </div>
            )}

            {success && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl mb-6 font-medium animate-in fade-in duration-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                {success}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div>
                  <label className="block text-xs text-gray-500 font-bold uppercase tracking-wider mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      type="text"
                      required={!isLogin}
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g. Sahil Belchada"
                      className="w-full bg-[#161822] border border-gray-800 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs text-gray-500 font-bold uppercase tracking-wider mb-1.5">
                  Your Actual Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    autoComplete="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="w-full bg-[#161822] border border-gray-800 rounded-xl pl-10 pr-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {authMode === 'cloud' && (
                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="block text-xs text-gray-500 font-bold uppercase tracking-wider">
                      Password
                    </label>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <Lock className="w-4 h-4" />
                    </div>
                     <input
                       autoComplete={isLogin ? 'current-password' : 'new-password'}
                       minLength={isLogin ? undefined : 6}
                       type={showPassword ? 'text' : 'password'}
                       required
                       value={password}
                       onChange={(e) => setPassword(e.target.value)}
                       placeholder="••••••••••••"
                       className="w-full bg-[#161822] border border-gray-800 rounded-xl pl-10 pr-12 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/50 focus:border-indigo-600/50 transition-all"
                     />
                     <button
                       type="button"
                       tabIndex={-1}
                       onClick={() => setShowPassword((v) => !v)}
                       className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-400"
                     >
                       {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                     </button>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing In...</span>
                  </>
                ) : (
                  <>
                    <span>{authMode === 'local' ? `Sign In with Email (${email || 'Local'})` : isLogin ? 'Sign In' : 'Create Account'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 space-y-4">
              {authMode === 'cloud' && (
                <div className="text-center pt-4 border-t border-gray-800/50">
                  <span className="text-xs text-gray-500 font-medium">
                    {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
                  </span>
                  <button
                    onClick={toggleMode}
                    className="text-xs text-indigo-400 hover:underline font-bold"
                  >
                    {isLogin ? 'Sign Up' : 'Sign In'}
                  </button>
                </div>
              )}

              <div className="pt-4 border-t border-gray-800/50">
                <button
                  type="button"
                  onClick={handleDemoLogin}
                  disabled={loading}
                  className="w-full py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-purple-600/20 flex items-center justify-center gap-2"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Try Demo (Temporary Account)</span>
                </button>
                <p className="text-[10px] text-gray-500 text-center mt-1.5">
                  Quick exploratory mode with zero setup required.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
