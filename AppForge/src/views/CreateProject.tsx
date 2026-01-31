import { useWizardStore } from '../hooks/useWizardStore';
import { AnimatePresence, motion } from 'framer-motion';
import { Bot, Home } from 'lucide-react';
import { Link } from 'react-router-dom';
import { InputStep } from '../components/wizard/InputStep';
import { ProposalStep } from '../components/wizard/ProposalStep';
import { BuildingStep } from '../components/wizard/BuildingStep';
import { CompleteStep } from '../components/wizard/CompleteStep';
import { useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { useEffect } from 'react';

export function CreateProject() {
  const { step, reset, updateData, setStep } = useWizardStore();
  const { id } = useParams();
  useEffect(() => {
    if (id) api.getProjects().then((projects) => {
      const p = projects.find((x) => x.name === id);
      if (p) { updateData({ name: p.name, description: p.description, deliverables: p.deliverables || [] }); setStep('COMPLETE'); }
    });
  }, [id, setStep, updateData]);
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="fixed top-0 left-0 right-0 h-16 bg-white/80 backdrop-blur-lg border-b border-slate-200 z-50 flex items-center px-4 md:px-6">
        <Link to="/" onClick={reset} className="flex items-center gap-3 text-slate-600 hover:text-slate-900"><Home className="h-5 w-5" /><span className="font-medium hidden sm:inline">Dashboard</span></Link>
        <div className="flex-1 flex justify-center"><div className="flex items-center gap-2"><Bot className="h-6 w-6 text-brand-600" /><span className="text-lg font-display font-bold text-slate-900">AppForge</span></div></div>
        <div className="w-24 sm:w-32" />
      </header>
      <main className="pt-24 pb-8 px-4 md:px-8 min-h-screen">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xl min-h-[70vh]">
            <AnimatePresence mode="wait">
              {step === 'INPUT' && <motion.div key="input" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="p-6 md:p-8"><InputStep /></motion.div>}
              {step === 'PROPOSAL' && <motion.div key="proposal" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="p-6 md:p-8"><ProposalStep /></motion.div>}
              {step === 'BUILDING' && <motion.div key="building" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="p-6 md:p-8"><BuildingStep /></motion.div>}
              {step === 'COMPLETE' && <motion.div key="complete" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><CompleteStep /></motion.div>}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  );
}
