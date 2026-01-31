import { Bot, Check, RefreshCw } from 'lucide-react';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useEffect, useState } from 'react';

export function ProposalStep() {
  const { data, updateData, setStep } = useWizardStore();
  const [analyzing, setAnalyzing] = useState(!data.description);
  const [description, setDescription] = useState(data.description || '');
  useEffect(() => {
    if (analyzing && data.userRequest) {
      const t = setTimeout(() => {
        const req = data.userRequest.toLowerCase();
        const isMobile = req.includes('phone') || req.includes('mobile') || req.includes('android');
        const generated = isMobile ? 'I will create a mobile-friendly app with touch-optimized UI and responsive layout.' : 'I will create a modern web app with a clean UI and the features you described.';
        setDescription(generated);
        updateData({ description: generated, name: isMobile ? 'Mobile App' : 'Web App' });
        setAnalyzing(false);
      }, 1500);
      return () => clearTimeout(t);
    }
  }, [analyzing, data.userRequest, updateData]);
  if (analyzing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <div className="relative mb-8"><div className="absolute inset-0 bg-brand-500 blur-xl opacity-20 animate-pulse rounded-full" /><Bot className="h-16 w-16 text-brand-600 animate-float relative" /></div>
        <h2 className="text-xl font-display font-bold text-slate-900 mb-2">Analyzing your idea...</h2>
        <p className="text-slate-500">Preparing a proposal</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col max-w-2xl mx-auto min-h-[50vh]">
      <div className="flex gap-4 mb-6">
        <div className="h-10 w-10 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0"><Bot className="h-6 w-6 text-brand-600" /></div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-900 mb-3">Proposal</h3>
          <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none p-5 shadow-sm"><p className="text-slate-600 whitespace-pre-wrap leading-relaxed">{description}</p></div>
          <button onClick={() => setAnalyzing(true)} className="mt-3 flex items-center gap-2 px-4 py-2 hover:bg-slate-100 rounded-lg text-slate-500 text-sm"><RefreshCw className="h-4 w-4" /> Regenerate</button>
        </div>
      </div>
      <div className="mt-auto pt-8 border-t border-slate-200 flex flex-wrap gap-3 justify-between">
        <button onClick={() => setStep('INPUT')} className="flex items-center gap-2 px-5 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-medium"><RefreshCw className="h-4 w-4" /> Back</button>
        <button onClick={() => setStep('BUILDING')} className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-brand-600 to-accent-600 hover:from-brand-500 hover:to-accent-500 text-white rounded-xl font-medium shadow-lg shadow-brand-500/25"><Check className="h-5 w-5" /> Build app</button>
      </div>
    </div>
  );
}
