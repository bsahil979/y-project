import React from 'react';
import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Globe,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Wallet
} from 'lucide-react';
import { Link } from 'react-router-dom';

const features = [
  {
    icon: <BarChart3 className="w-6 h-6 text-cyan-400" />,
    title: 'Portfolio clarity',
    description: 'See your exposures, diversification, and risk in plain language before making your next move.'
  },
  {
    icon: <BrainCircuit className="w-6 h-6 text-violet-400" />,
    title: 'AI that explains itself',
    description: 'Compare allocations with and without learned market states, with assumptions shown alongside the results.'
  },
  {
    icon: <ShieldCheck className="w-6 h-6 text-emerald-400" />,
    title: 'Trust first',
    description: 'Transparent portfolio data, no hidden sales pressure, and advice designed for self-directed investors.'
  },
  {
    icon: <Globe className="w-6 h-6 text-amber-400" />,
    title: 'Built for global markets',
    description: 'Track US and Indian equities side by side with currency-aware planning and market context.'
  }
];

const steps = [
  {
    number: '01',
    title: 'Record your holdings',
    description: 'Enter opening positions and record transactions to build a view of your current allocation.'
  },
  {
    number: '02',
    title: 'Understand portfolio risk',
    description: 'Inspect concentration, historical volatility, benchmark comparisons and stress scenarios.'
  },
  {
    number: '03',
    title: 'Compare allocations',
    description: 'Compare possible allocations and review the risks and assumptions behind each result.'
  }
];

const benefits = [
  'No commission-driven recommendations',
  'Clear summaries for portfolio risk and goals',
  'Built for long-term investing, not hype',
  'Fast decision support for everyday investors'
];

const trustBadges = [
  { label: 'INR + USD', detail: 'Separate currency totals' },
  { label: 'HMM', detail: 'Market-state comparison' },
  { label: 'Clear methods', detail: 'Assumptions shown with results' }
];

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-[#070b14] text-white selection:bg-indigo-500/30">
      <nav className="fixed top-0 z-50 w-full border-b border-white/10 bg-[#070b14]/75 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 shadow-lg shadow-indigo-500/30">
             <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight uppercase">SmartPortfolio</span>
          </div>

          <div className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
            <a href="#features" className="transition-colors hover:text-white">Features</a>
            <a href="#how-it-works" className="transition-colors hover:text-white">How it works</a>
            <a href="#why-us" className="transition-colors hover:text-white">Why us</a>
          </div>

          <Link
            to="/auth"
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500"
          >
            Launch Dashboard
          </Link>
        </div>
      </nav>

      <main>
        <section className="relative overflow-hidden px-6 pb-24 pt-36 md:pt-40">
          <div className="absolute inset-x-0 top-0 -z-10 h-[32rem] bg-[radial-gradient(circle_at_center,_rgba(99,102,241,0.28),_transparent_55%)]" />

          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-4xl text-center">
             <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-indigo-200">
               <Sparkles className="h-3.5 w-3.5" />
               Portfolio analysis for everyday investors
             </div>

             <h1 className="text-5xl font-black tracking-[-0.06em] text-white md:text-7xl">
               Take control of your portfolio with better decisions.
             </h1>

             <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300 md:text-xl">
               Track your holdings, understand historical risk, and explore whether learned market conditions help portfolio allocation.
             </p>

             <div className="mt-10 flex flex-col items-center justify-center gap-4 md:flex-row">
               <Link
                 to="/auth"
                 className="inline-flex items-center gap-2 rounded-2xl bg-indigo-600 px-8 py-4 text-base font-bold text-white shadow-2xl shadow-indigo-600/30 transition hover:bg-indigo-500"
               >
                 Get started free
                 <ArrowRight className="h-4 w-4" />
               </Link>
               <a
                 href="#features"
                 className="rounded-2xl border border-white/10 bg-white/5 px-8 py-4 text-base font-bold text-white transition hover:border-indigo-400/40 hover:bg-white/10"
               >
                 Explore features
               </a>
             </div>

             <div className="mt-14 grid gap-4 text-left sm:grid-cols-3">
               <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                 <div className="text-3xl font-black text-white">Holdings</div>
                 <div className="mt-2 text-sm text-slate-400">Quantities, costs and available quotes</div>
               </div>
               <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                 <div className="text-3xl font-black text-white">Risk</div>
                 <div className="mt-2 text-sm text-slate-400">Concentration and historical scenarios</div>
               </div>
               <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5">
                 <div className="text-3xl font-black text-white">Planning</div>
                 <div className="mt-2 text-sm text-slate-400">Compare allocations and goals</div>
               </div>
             </div>

             <div className="mt-10 grid gap-3 sm:grid-cols-3">
               {trustBadges.map((badge) => (
                 <div key={badge.label} className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 backdrop-blur-sm">
                   <span className="font-bold text-white">{badge.label}</span>
                   <span className="ml-2 text-slate-400">{badge.detail}</span>
                 </div>
               ))}
             </div>
            </div>
          </div>
        </section>

        <section id="features" className="px-6 py-24">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-2xl text-center">
             <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-300">What you can explore</p>
             <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
               Clear insight. Smarter decisions.
             </h2>
            </div>

            <div className="mt-14 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
             {features.map((feature) => (
               <div key={feature.title} className="rounded-3xl border border-white/10 bg-slate-900/60 p-7 transition hover:-translate-y-1 hover:border-indigo-500/40 hover:bg-slate-900">
                 <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800">
                   {feature.icon}
                 </div>
                 <h3 className="text-xl font-bold text-white">{feature.title}</h3>
                 <p className="mt-3 text-sm leading-7 text-slate-400">{feature.description}</p>
               </div>
             ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-y border-white/10 bg-slate-950/60 px-6 py-24">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-2xl text-center">
             <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-300">How it works</p>
             <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
               Three simple steps to better investing.
             </h2>
            </div>

            <div className="mt-14 grid gap-6 lg:grid-cols-3">
             {steps.map((step) => (
               <div key={step.number} className="rounded-3xl border border-white/10 bg-[#0d1322] p-8">
                 <div className="mb-5 text-sm font-semibold tracking-[0.2em] text-indigo-300">{step.number}</div>
                 <h3 className="text-2xl font-bold text-white">{step.title}</h3>
                 <p className="mt-4 text-base leading-7 text-slate-400">{step.description}</p>
               </div>
             ))}
            </div>
          </div>
        </section>

        <section id="why-us" className="px-6 py-24">
          <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
             <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-300">A smarter way to invest</p>
             <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
               Advice should feel clear, not complicated.
             </h2>
             <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
               Follow the calculation from holdings to current-value weights, historical risk and model-based allocations.
             </p>

             <div className="mt-8 space-y-4">
               {benefits.map((benefit) => (
                 <div key={benefit} className="flex items-start gap-3 text-slate-200">
                   <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-400" />
                   <span>{benefit}</span>
                 </div>
               ))}
             </div>
            </div>

            <div className="rounded-[32px] border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-slate-900 to-slate-950 p-8 shadow-2xl shadow-indigo-900/20">
             <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
               <div className="flex items-center justify-between">
                 <div className="flex items-center gap-3">
                   <div className="rounded-xl bg-indigo-500/15 p-2 text-indigo-300">
                     <Wallet className="h-5 w-5" />
                   </div>
                   <div>
                     <div className="text-sm text-slate-400">Illustrative preview</div>
                     <div className="text-xl font-bold text-white">Example portfolio</div>
                   </div>
                 </div>
                 <div className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-bold text-emerald-300">Sample data</div>
               </div>

               <div className="mt-8 space-y-5">
                 <div>
                   <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                     <span>Risk score</span>
                     <span>72 / 100</span>
                   </div>
                   <div className="h-2.5 rounded-full bg-slate-800">
                     <div className="h-2.5 w-[72%] rounded-full bg-gradient-to-r from-emerald-400 to-cyan-400" />
                   </div>
                 </div>

                 <div>
                   <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                     <span>Market regime</span>
                     <span>Bullish</span>
                   </div>
                   <div className="h-2.5 rounded-full bg-slate-800">
                     <div className="h-2.5 w-[68%] rounded-full bg-gradient-to-r from-indigo-500 to-violet-400" />
                   </div>
                 </div>

                 <div>
                   <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                     <span>Sentiment</span>
                     <span>Positive</span>
                   </div>
                   <div className="h-2.5 rounded-full bg-slate-800">
                     <div className="h-2.5 w-[80%] rounded-full bg-gradient-to-r from-amber-400 to-orange-500" />
                   </div>
                 </div>
               </div>
             </div>
            </div>
          </div>
        </section>

        <section className="px-6 py-24">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-2xl text-center">
             <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-300">Built on trust</p>
             <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
               Understand the data, assumptions and limitations.
             </h2>
            </div>

            <div className="mt-14 grid gap-6 lg:grid-cols-3">
             <div className="rounded-[28px] border border-white/10 bg-slate-900/70 p-6">
               <div className="mb-4 inline-flex rounded-xl bg-emerald-500/10 p-2 text-emerald-300">
                 <ShieldCheck className="h-5 w-5" />
               </div>
               <h3 className="text-xl font-bold text-white">Transparent by default</h3>
               <p className="mt-3 text-sm leading-7 text-slate-400">Portfolio risk, exposure, and signal quality are shown in plain language — no hidden sales language or confusing dashboard jargon.</p>
             </div>

             <div className="rounded-[28px] border border-white/10 bg-slate-900/70 p-6">
               <div className="mb-4 inline-flex rounded-xl bg-indigo-500/10 p-2 text-indigo-300">
                 <Target className="h-5 w-5" />
               </div>
               <h3 className="text-xl font-bold text-white">Actionable without overwhelm</h3>
               <p className="mt-3 text-sm leading-7 text-slate-400">The system helps people decide what matters next, instead of dumping technical data and expecting them to connect the dots themselves.</p>
             </div>

             <div className="rounded-[28px] border border-white/10 bg-slate-900/70 p-6">
               <div className="mb-4 inline-flex rounded-xl bg-violet-500/10 p-2 text-violet-300">
                 <TrendingUp className="h-5 w-5" />
               </div>
               <h3 className="text-xl font-bold text-white">Built for long-term conviction</h3>
               <p className="mt-3 text-sm leading-7 text-slate-400">The product is designed for self-directed investors who want calm decision support, not hype-driven trading drama.</p>
             </div>
            </div>
          </div>
        </section>

        <section className="px-6 pb-24">
          <div className="mx-auto max-w-6xl rounded-[32px] border border-indigo-500/20 bg-gradient-to-r from-indigo-600 to-violet-600 p-8 text-center shadow-2xl shadow-indigo-900/30 md:p-12">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-100">Ready to grow?</p>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-white md:text-5xl">
             Build a portfolio you understand and trust.
            </h2>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 md:flex-row">
             <Link
               to="/auth"
               className="inline-flex items-center gap-2 rounded-2xl bg-white px-8 py-4 text-base font-bold text-indigo-700 transition hover:bg-slate-100"
             >
               Launch dashboard
               <ArrowRight className="h-4 w-4" />
             </Link>
             <a
               href="#features"
               className="rounded-2xl border border-white/30 bg-transparent px-8 py-4 text-base font-bold text-white transition hover:bg-white/10"
             >
               See all features
             </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 px-6 py-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 text-sm text-slate-400 md:flex-row">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-300">
             <Target className="h-4 w-4" />
            </div>
            <span className="font-semibold uppercase tracking-tight text-slate-200">SmartPortfolio</span>
          </div>

          <div className="flex gap-8">
            <a href="#features" className="transition hover:text-white">Features</a>
            <a href="#how-it-works" className="transition hover:text-white">How it works</a>
            <a href="#why-us" className="transition hover:text-white">Why us</a>
          </div>

          <div>© 2026 SmartPortfolio AI</div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
