import React, { useState } from 'react';
import { supabase } from '../services/supabaseClient';
import { PortfolioDataService } from '../services/portfolioData';
import { 
  Calendar, CheckSquare, CalendarDays, Shield, TrendingUp, Umbrella, 
  Sparkles, Calculator, PieChart, Search, MessageCirclePlus, Gauge, 
  Map, Globe, ArrowLeft, ArrowRight, HelpCircle, Lock, Loader2, Coins
} from 'lucide-react';

const OnboardingWizard = ({ onComplete, userId, user }) => {
  const [step, setStep] = useState(1);
  const [frequency, setFrequency] = useState('');
  const [goals, setGoals] = useState([]);
  const [risk, setRisk] = useState('');
  const [country, setCountry] = useState('');
  const [customCountry, setCustomCountry] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [saveError, setSaveError] = useState('');

  const totalSteps = 4;

  // Step 1 Options: Frequency
  const frequencyOptions = [
    { id: 'daily', label: 'Daily', icon: 'daily' },
    { id: 'weekly', label: 'Weekly', icon: 'weekly' },
    { id: 'monthly', label: 'Monthly', icon: 'monthly' },
    { id: 'quarterly', label: 'Quarterly', icon: 'quarterly' },
    { id: 'yearly', label: 'Yearly', icon: 'yearly' },
  ];

  // Step 2 Options: Goals
  const goalOptions = [
    { id: 'confidence', label: 'Build confidence in financial strategy', icon: Shield },
    { id: 'returns', label: 'Increase risk-adjusted returns', icon: TrendingUp },
    { id: 'protection', label: 'Boost downside protection', icon: Umbrella },
    { id: 'recommendations', label: 'Get personalized recommendations', icon: Sparkles },
    { id: 'taxes', label: 'Optimize taxes & fees', icon: Calculator },
    { id: 'networth', label: 'Track my net worth', icon: PieChart },
    { id: 'insights', label: 'Get AI investing insights', icon: Search },
    { id: 'other', label: 'Something else', icon: MessageCirclePlus },
  ];

  // Step 3 Options: Risk
  const riskOptions = [
    { id: 'conservative', label: 'Conservative', sublabel: 'Prioritize lower volatility', angle: -60 },
    { id: 'moderate', label: 'Moderate', sublabel: 'Balance return and risk', angle: 0 },
    { id: 'aggressive', label: 'Aggressive', sublabel: 'Target higher historical returns', angle: 60 },
  ];

  // Step 4 Options: Country
  const countryOptions = [
    { id: 'US', label: 'United States', type: 'map', mapType: 'us' },
     { id: 'IN', label: 'India', type: 'map', mapType: 'in' },
    { id: 'Other', label: 'Other', type: 'globe' },
  ];

  const handleGoalToggle = (id) => {
    if (goals.includes(id)) {
      setGoals(goals.filter(g => g !== id));
    } else {
      setGoals([...goals, id]);
    }
  };

  const handleSelectAllGoals = () => {
    if (goals.length === goalOptions.length) {
      setGoals([]);
    } else {
      setGoals(goalOptions.map(o => o.id));
    }
  };

  const handleNext = () => {
    if (step < totalSteps) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    
    setSaveError('');
    try {
      const finalCountry = country === 'Other' ? (customCountry || 'Other') : country;
      
      const onboardingData = {
        frequency,
        goals,
        risk,
        country: finalCountry,
        completedAt: new Date().toISOString()
      };

      // Set preferred currency based on country
      let prefCurrency = 'USD';
      if (finalCountry.toLowerCase().includes('india') || finalCountry.toLowerCase() === 'in') {
        prefCurrency = 'INR';
      } else if (finalCountry.toLowerCase() === 'ca') {
        prefCurrency = 'USD'; // default
      } else if (['uk', 'united kingdom', 'gb'].includes(finalCountry.toLowerCase())) {
        prefCurrency = 'GBp';
      } else if (['europe', 'eu', 'germany', 'france', 'italy'].includes(finalCountry.toLowerCase())) {
        prefCurrency = 'EUR';
      } else if (['japan', 'jp'].includes(finalCountry.toLowerCase())) {
        prefCurrency = 'JPY';
      }

      if (!user.isDemo && !user.isLocal) {
        const { error } = await supabase.auth.updateUser({ data: { onboarding_status: 'complete' } });
        if (error) throw error;
      }
      localStorage.setItem(`onboarding_completed_${userId}`, 'true');
      PortfolioDataService.saveInvestorProfile(userId, { ...onboardingData, risk_preference: risk });
      localStorage.setItem('aura_pref_currency', prefCurrency);
      
      setIsSubmitting(false);
      if (onComplete) {
        onComplete(onboardingData);
      }
    } catch {
      setIsSubmitting(false);
      setSaveError('Setup could not be saved. Please try again.');
    }
  };

  // Render Custom Speedometer SVG
  const Speedometer = ({ angle }) => (
    <svg viewBox="0 0 100 60" className="w-16 h-16 mx-auto text-indigo-500">
      <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" className="opacity-20" />
      <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeDasharray="125" strokeDashoffset="0" className="text-indigo-500" />
      {/* Tick Marks */}
      <line x1="14" y1="40" x2="18" y2="38" stroke="currentColor" strokeWidth="1.5" />
      <line x1="26" y1="26" x2="29" y2="28" stroke="currentColor" strokeWidth="1.5" />
      <line x1="50" y1="10" x2="50" y2="15" stroke="currentColor" strokeWidth="1.5" />
      <line x1="74" y1="26" x2="71" y2="28" stroke="currentColor" strokeWidth="1.5" />
      <line x1="86" y1="40" x2="82" y2="38" stroke="currentColor" strokeWidth="1.5" />
      {/* Needle */}
      <g transform={`translate(50, 50) rotate(${angle})`}>
        <line x1="0" y1="0" x2="0" y2="-38" stroke="#3b82f6" strokeWidth="3" strokeLinecap="round" />
        <circle cx="0" cy="0" r="4" fill="#3b82f6" />
      </g>
    </svg>
  );

  // Render Custom Calendar SVGs for Step 1
  const renderCalendarIcon = (type) => {
    switch (type) {
      case 'daily':
        return (
          <svg viewBox="0 0 448 512" className="w-12 h-12 text-indigo-500 mx-auto">
            <path fill="currentColor" d="M128 0c17.7 0 32 14.3 32 32V64H288V32c0-17.7 14.3-32 32-32s32 14.3 32 32V64h48c26.5 0 48 21.5 48 48v48H0V112C0 85.5 21.5 64 48 64H96V32c0-17.7 14.3-32 32-32zM0 192H448V464c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V192zm241 121c9.4-9.4 9.4-24.6 0-33.9s-24.6-9.4-33.9 0l-79 79-39-39c-9.4-9.4-24.6-9.4-33.9 0s-9.4 24.6 0 33.9l56 56c9.4 9.4 24.6 9.4 33.9 0l96-96z" />
          </svg>
        );
      case 'weekly':
        return (
          <svg viewBox="0 0 448 512" className="w-12 h-12 text-indigo-500 mx-auto">
            <path fill="currentColor" d="M128 0c17.7 0 32 14.3 32 32V64H288V32c0-17.7 14.3-32 32-32s32 14.3 32 32V64h48c26.5 0 48 21.5 48 48v48H0V112C0 85.5 21.5 64 48 64H96V32c0-17.7 14.3-32 32-32zM0 192H448V464c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V192zm64 80v32c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16V272c0-8.8-7.2-16-16-16H80c-8.8 0-16 7.2-16 16zm128 0v32c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16V272c0-8.8-7.2-16-16-16H208c-8.8 0-16 7.2-16 16zm128 0v32c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16V272c0-8.8-7.2-16-16-16H336c-8.8 0-16 7.2-16 16zm-256 96v32c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16V368c0-8.8-7.2-16-16-16H80c-8.8 0-16 7.2-16 16zm128 0v32c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16V368c0-8.8-7.2-16-16-16H208c-8.8 0-16 7.2-16 16zm128 0v32c0 8.8 7.2 16 16 16h32c8.8 0 16-7.2 16-16V368c0-8.8-7.2-16-16-16H336c-8.8 0-16 7.2-16 16z" />
          </svg>
        );
      case 'monthly':
        return (
          <svg viewBox="0 0 448 512" className="w-12 h-12 text-indigo-500 mx-auto">
            <path fill="currentColor" d="M128 0c17.7 0 32 14.3 32 32V64H288V32c0-17.7 14.3-32 32-32s32 14.3 32 32V64h48c26.5 0 48 21.5 48 48v48H0V112C0 85.5 21.5 64 48 64H96V32c0-17.7 14.3-32 32-32zM0 192H448V464c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V192zm64 80h80V352H64V272zm120 0h80V352H184V272zm120 0h80V352H304V272zm-240 112h80v80H64V384zm120 0h80v80H184V384zm120 0h80v80H304V384z" />
          </svg>
        );
      case 'quarterly':
        return (
          <svg viewBox="0 0 448 512" className="w-12 h-12 text-indigo-500 mx-auto">
            <path fill="currentColor" d="M152 64H296V32c0-17.7 14.3-32 32-32s32 14.3 32 32V64h38c27.6 0 50 22.4 50 50v46H0V114c0-27.6 22.4-50 50-50H88V32c0-17.7 14.3-32 32-32s32 14.3 32 32V64zM0 192H448V462c0 27.6-22.4 50-50 50H50c-27.6 0-50-22.4-50-50V192zm64 96v96c0 17.7 14.3 32 32 32H192c17.7 0 32-14.3 32-32V288c0-17.7-14.3-32-32-32H96c-17.7 0-32 14.3-32 32z" />
          </svg>
        );
      case 'yearly':
        return (
          <svg viewBox="0 0 448 512" className="w-12 h-12 text-indigo-500 mx-auto">
            <path fill="currentColor" d="M128 0c17.7 0 32 14.3 32 32V64H288V32c0-17.7 14.3-32 32-32s32 14.3 32 32V64h48c26.5 0 48 21.5 48 48v48H0V112C0 85.5 21.5 64 48 64H96V32c0-17.7 14.3-32 32-32zM0 192H448V464c0 26.5-21.5 48-48 48H48c-26.5 0-48-21.5-48-48V192zm64 80h80v64H64V272zm120 0h80v64H184V272zm120 0h80v64H304V272zm-240 96h80v64H64V368zm120 0h80v64H184V368zm120 0h80v64H304V368z" />
          </svg>
        );
      default:
        return <Calendar className="w-12 h-12 text-indigo-500 mx-auto" />;
    }
  };

  const isNextDisabled = () => {
    if (step === 1) return !frequency;
    if (step === 2) return goals.length === 0;
    if (step === 3) return !risk;
    if (step === 4) return !country || (country === 'Other' && !customCountry.trim());
    return false;
  };

  if (isSubmitting) {
    return (
      <div className="min-h-screen bg-[#07080d] flex items-center justify-center text-white px-6">
        <div className="text-center space-y-6 max-w-md p-8 bg-[#11131a]/80 border border-gray-800 rounded-3xl shadow-2xl backdrop-blur-md">
          <Loader2 className="w-14 h-14 text-indigo-500 animate-spin mx-auto" />
          <h2 className="text-2xl font-black tracking-tight">Personalizing SmartPortfolio</h2>
          <div className="space-y-2 text-sm text-gray-400">
            <p className="animate-pulse">Saving your preferences...</p>
            <p className="text-xs text-gray-500">Preparing your portfolio workspace.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-white flex flex-col justify-between selection:bg-indigo-500/30 font-sans bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.18),_transparent_24%),radial-gradient(circle_at_bottom,_rgba(167,139,250,0.08),_transparent_28%)]">
      
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0a0d17]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 shadow-lg shadow-indigo-500/20">
              <TrendingUp className="h-4 w-4 text-white" />
            </div>
            <span className="text-[18px] font-black tracking-tight text-white">
              SmartPortfolio
            </span>
          </div>

          <div className="flex items-center gap-5 text-xs font-semibold text-slate-300">
            <div className="flex items-center gap-1.5 transition-colors hover:text-white">
              <Lock className="h-3.5 w-3.5" />
              <span>Secure Session</span>
            </div>
            <div className="flex items-center gap-1.5 transition-colors hover:text-white">
              <HelpCircle className="h-3.5 w-3.5" />
              <span>Help</span>
            </div>
            <div className="flex h-7 w-7 items-center justify-center rounded-full border border-indigo-500/40 bg-indigo-500/10 text-xs font-black text-indigo-200">
              {userId?.[0]?.toUpperCase() || 'U'}
            </div>
          </div>
        </div>

        <div className="h-1.5 w-full bg-slate-800/40">
          <div 
            className="h-full bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-400 transition-all duration-500 ease-out" 
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col items-center justify-center px-6 py-12">
        
        {/* Step 1: Frequency */}
        {step === 1 && (
          <div className="w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 text-center">
            <div className="space-y-2">
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">
                How often do you check your portfolio?
              </h1>
              <p className="text-sm text-gray-500">You can always change this later</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 max-w-4xl mx-auto pt-6">
              {frequencyOptions.map((opt) => {
                const isSelected = frequency === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setFrequency(opt.id)}
                    className={`flex min-h-[170px] flex-col items-center justify-between overflow-hidden rounded-[24px] border p-6 text-center transition-all duration-300 relative group ${
                      isSelected 
                        ? 'border-indigo-400/80 bg-[linear-gradient(180deg,rgba(79,70,229,0.20),rgba(17,24,39,0.82))] text-white shadow-[0_0_0_1px_rgba(99,102,241,0.35),0_18px_40px_rgba(79,70,229,0.12)]' 
                        : 'border-white/10 bg-slate-900/60 text-slate-400 hover:border-indigo-500/40 hover:bg-slate-900 hover:text-white'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-2 right-2 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center">
                        <CheckSquare className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}
                    <div className="my-auto">
                      {renderCalendarIcon(opt.icon)}
                    </div>
                    <span className="text-sm font-bold tracking-tight mt-4">{opt.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="inline-flex items-center gap-2 px-4 py-2 border border-gray-800 bg-[#11131a]/50 text-xs text-gray-500 rounded-xl max-w-md mx-auto justify-center mt-6">
              <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>So we can size recommendations to how often you check in.</span>
            </div>
          </div>
        )}

        {/* Step 2: Goals */}
        {step === 2 && (
          <div className="w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 text-center">
            <div className="space-y-2">
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">
                How can SmartPortfolio help you?
              </h1>
              <p className="text-sm text-gray-500">Select all that apply. Your choices help us personalize your experience.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 max-w-5xl mx-auto pt-4">
              {goalOptions.map((opt) => {
                const isSelected = goals.includes(opt.id);
                return (
                  <button
                    key={opt.id}
                    onClick={() => handleGoalToggle(opt.id)}
                    className={`relative flex min-h-[140px] flex-col items-center justify-center rounded-[24px] border p-6 text-center transition-all duration-300 ${
                      isSelected 
                        ? 'border-indigo-400/80 bg-[linear-gradient(180deg,rgba(79,70,229,0.20),rgba(17,24,39,0.82))] text-white shadow-[0_0_0_1px_rgba(99,102,241,0.35),0_18px_40px_rgba(79,70,229,0.12)]' 
                        : 'border-white/10 bg-slate-900/60 text-slate-400 hover:border-indigo-500/40 hover:bg-slate-900 hover:text-white'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-2.5 right-2.5 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center">
                        <CheckSquare className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}
                    <opt.icon className={`w-8 h-8 mb-3 ${isSelected ? 'text-indigo-400' : 'text-gray-500 group-hover:text-indigo-400 transition-colors'}`} />
                    <span className="text-xs font-bold leading-snug">{opt.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="pt-2">
              <button
                onClick={handleSelectAllGoals}
                className="px-6 py-2.5 rounded-xl border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-xs font-bold transition-all inline-flex items-center gap-2 active:scale-95"
              >
                <input 
                  type="checkbox" 
                  checked={goals.length === goalOptions.length}
                  readOnly
                  className="rounded text-indigo-600 focus:ring-indigo-500 border-gray-700 w-3.5 h-3.5 bg-gray-900"
                />
                <span>Select all</span>
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Risk Preference */}
        {step === 3 && (
          <div className="w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 text-center">
            <div className="space-y-2">
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">
                What is your risk preference?
              </h1>
              <p className="text-sm text-gray-500">You can always change this later</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 max-w-5xl mx-auto pt-6">
              {riskOptions.map((opt) => {
                const isSelected = risk === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setRisk(opt.id)}
                    className={`relative flex min-h-[170px] flex-col items-center justify-between rounded-[24px] border p-6 text-center transition-all duration-300 ${
                      isSelected 
                        ? 'border-indigo-400/80 bg-[linear-gradient(180deg,rgba(79,70,229,0.20),rgba(17,24,39,0.82))] text-white shadow-[0_0_0_1px_rgba(99,102,241,0.35),0_18px_40px_rgba(79,70,229,0.12)]' 
                        : 'border-white/10 bg-slate-900/60 text-slate-400 hover:border-indigo-500/40 hover:bg-slate-900 hover:text-white'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-2.5 right-2.5 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center">
                        <CheckSquare className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}
                    <div className="my-auto py-2">
                      <Speedometer angle={opt.angle} />
                    </div>
                    <div className="space-y-1">
                      <span className="text-sm font-bold tracking-tight block">{opt.label}</span>
                      <span className="text-[10px] text-gray-500 font-medium block">{opt.sublabel}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="inline-flex items-center gap-2 px-4 py-2 border border-gray-800 bg-[#11131a]/50 text-xs text-gray-500 rounded-xl max-w-xl mx-auto justify-center mt-6">
              <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>Your risk preference is critical to your portfolio analysis, scoring, and recommendations.</span>
            </div>
          </div>
        )}

        {/* Step 4: Country of Residence */}
        {step === 4 && (
          <div className="w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 text-center">
            <div className="space-y-2">
              <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight">
                What is your country of residence?
              </h1>
              <p className="text-sm text-gray-500">For tax purposes</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto pt-6">
              {countryOptions.map((opt) => {
                const isSelected = country === opt.id;
                return (
                  <div
                    key={opt.id}
                    onClick={() => {
                      setCountry(opt.id);
                      if (opt.id !== 'Other') setCustomCountry('');
                    }}
                    className={`relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-[28px] border p-8 text-center transition-all duration-300 ${
                      isSelected 
                        ? 'border-indigo-400/80 bg-[linear-gradient(180deg,rgba(79,70,229,0.20),rgba(17,24,39,0.82))] text-white shadow-[0_0_0_1px_rgba(99,102,241,0.35),0_18px_40px_rgba(79,70,229,0.12)]' 
                        : 'border-white/10 bg-slate-900/60 text-slate-400 hover:border-indigo-500/40 hover:bg-slate-900 hover:text-white'
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-3 right-3 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center">
                        <CheckSquare className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}
                    
                    {opt.type === 'map' && opt.mapType === 'us' && (
                      <svg viewBox="0 0 640 512" className="w-16 h-16 text-indigo-500 mb-4">
                        <path fill="currentColor" d="M192 128l0 128L0 256l0-128 192 0zm320 0l128 0 0 128-128 0 0-128zm-256 0l192 0 0 128-192 0 0-128zM0 320l192 0 0 128L0 448l0-128zm384 128l-128 0 0-128 128 0 0 128zm64-128l192 0 0 128-192 0 0-128z" className="opacity-20" />
                        <path fill="currentColor" d="M570.69 236.27c6.5-9.4 4.51-22.3-4.43-29.35l-20.91-16.51a56 56 0 0 1 0-87.92l20.91-16.51c8.94-7.05 10.93-19.95 4.43-29.35C538.77 11.23 487.31 0 432 0S325.23 11.23 293.31 56.63c-6.5 9.4-4.51 22.3 4.43 29.35l20.91 16.51a56 56 0 0 1 0 87.92L317.74 207c-8.94 7.05-10.93 19.95-4.43 29.35C345.23 281.77 396.69 293 452 293s106.77-11.23 138.69-56.73z" className="text-indigo-400" />
                      </svg>
                    )}
                     {opt.type === 'map' && opt.mapType === 'in' && (
                       <svg viewBox="0 0 640 512" className="w-16 h-16 text-indigo-500 mb-4">
                         <path fill="#ff9933" d="M320 0h320l-120 256 120 256H0L120 256 0 0h200z" />
                         <circle cx="320" cy="256" r="80" fill="#000080" />
                         <path fill="#ffffff" d="M240 170l30 86 86 2-68 46 16 86-70-48-70 48 16-86-68-46 86-2z" />
                       </svg>
                     )}
                    {opt.type === 'globe' && (
                      <Globe className="w-16 h-16 text-indigo-500 mb-4 group-hover:rotate-12 transition-transform duration-500" />
                    )}

                    <span className="text-sm font-bold tracking-tight">{opt.label}</span>
                    
                    {opt.id === 'Other' && isSelected && (
                      <div className="mt-4 w-full px-2 animate-in fade-in duration-300" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          placeholder="Type country name..."
                          value={customCountry}
                          onChange={(e) => setCustomCountry(e.target.value)}
                          className="w-full bg-[#161822] border border-indigo-500/50 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && customCountry.trim()) {
                              handleNext();
                            }
                          }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="inline-flex items-center gap-2 px-4 py-2 border border-gray-800 bg-[#11131a]/50 text-xs text-gray-500 rounded-xl max-w-xl mx-auto justify-center mt-6">
              <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>The country you reside in affects your currency preference and securities we suggest.</span>
            </div>
          </div>
        )}

      </main>

      {/* Bottom Sticky Action Buttons */}
      {saveError && <p role="alert" className="text-center text-red-300">{saveError}</p>}
      <footer className="border-t border-white/10 bg-[#0b101b]/80 px-6 py-4 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            {step > 1 && (
              <button
                onClick={handleBack}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-6 py-2.5 text-xs font-bold text-slate-300 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Back</span>
              </button>
            )}
          </div>

          <button
            onClick={handleNext}
            disabled={isNextDisabled()}
            className={`flex items-center gap-2 rounded-xl px-8 py-2.5 text-xs font-bold text-white transition-all active:scale-95 ${
              isNextDisabled()
                ? 'cursor-not-allowed border border-indigo-500/30 bg-indigo-600/15 text-indigo-300/60 opacity-55'
                : 'border border-indigo-500/40 bg-gradient-to-r from-indigo-600 to-violet-600 shadow-lg shadow-indigo-600/25 hover:from-indigo-500 hover:to-violet-500'
            }`}
          >
            <span>{step === totalSteps ? 'Finish' : 'Next'}</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </footer>
    </div>
  );
};

export default OnboardingWizard;
