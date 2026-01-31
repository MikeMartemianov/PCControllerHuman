import { Sparkles } from 'lucide-react';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useState } from 'react';

export function InputStep() {
  const { data, updateData, setStep } = useWizardStore();
  const [value, setValue] = useState(data.userRequest || '');
  const handleNext = () => { if (!value.trim()) return; updateData({ userRequest: value.trim() }); setStep('PROPOSAL'); };
  return (
    <div className="flex flex-col min-h-[60vh] justify-center">
      <div className="text-center mb-8">
        <h2 className="text-2xl md:text-3xl font-display font-bold text-slate-900 mb-3">What app do you want?</h2>
        <p className="text-slate-500 max-w-lg mx-auto">Describe your idea. AI will design and build it.</p>
      </div>
      <div className="relative max-w-2xl mx-auto w-full">
        <textarea value={value} onChange={(e) => setValue(e.target.value)} placeholder="Example: A todo app with categories and due dates..." className="w-full h-44 md:h-52 bg-white border border-slate-200 rounded-2xl p-5 md:p-6 text-base text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 resize-none shadow-sm" />
        <div className="absolute bottom-4 right-4">
          <button onClick={handleNext} disabled={!value.trim()} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-brand-600 to-accent-600 hover:from-brand-500 hover:to-accent-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium shadow-lg shadow-brand-500/25">
            <Sparkles className="h-5 w-5" /> Continue
          </button>
        </div>
      </div>
    </div>
  );
}
