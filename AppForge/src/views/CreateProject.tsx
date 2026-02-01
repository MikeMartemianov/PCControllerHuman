import { useWizardStore } from '../hooks/useWizardStore';
import { AnimatePresence, motion } from 'framer-motion';
import { Sparkles, ArrowLeft } from 'lucide-react';
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
    if (id) {
      api.getProjects().then((projects) => {
        const p = projects.find((x) => x.name === id);
        if (p) {
          updateData({ name: p.name, description: p.description, deliverables: p.deliverables || [] });
          setStep('COMPLETE');
        }
      });
    }
  }, [id, setStep, updateData]);

  const steps = [
    { key: 'INPUT', label: 'Describe', num: 1 },
    { key: 'PROPOSAL', label: 'Review', num: 2 },
    { key: 'BUILDING', label: 'Build', num: 3 },
    { key: 'COMPLETE', label: 'Done', num: 4 },
  ];

  const currentStepIndex = steps.findIndex(s => s.key === step);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Top Bar */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-white/80 backdrop-blur-xl border-b border-gray-200/80 z-50 flex items-center px-6 shadow-sm">
        <Link to="/" onClick={reset} className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors group">
          <ArrowLeft className="h-5 w-5 group-hover:-translate-x-1 transition-transform" />
          <span className="font-medium">Back</span>
        </Link>
        
        {/* Progress Steps */}
        <div className="flex-1 flex justify-center">
          <div className="flex items-center gap-2">
            {steps.map((s, i) => (
              <div key={s.key} className="flex items-center">
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-all ${
                  i < currentStepIndex ? 'bg-emerald-100 text-emerald-700' :
                  i === currentStepIndex ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  <div className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    i < currentStepIndex ? 'bg-emerald-500 text-white' :
                    i === currentStepIndex ? 'bg-blue-500 text-white' :
                    'bg-gray-300 text-white'
                  }`}>
                    {i < currentStepIndex ? '✓' : s.num}
                  </div>
                  <span className="text-sm font-medium hidden sm:inline">{s.label}</span>
                </div>
                {i < steps.length - 1 && (
                  <div className={`w-8 h-0.5 mx-1 ${i < currentStepIndex ? 'bg-emerald-300' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-bold text-gray-900 hidden sm:inline">AI Builder</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 pb-8 px-4 sm:px-8 min-h-screen">
        <div className="h-full max-w-5xl mx-auto">
          <div className="bg-white/80 backdrop-blur-sm border border-gray-200/80 rounded-3xl overflow-hidden shadow-2xl shadow-gray-200/50 min-h-[75vh] relative">
            {/* Decorative elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-blue-100/50 to-purple-100/50 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-gradient-to-tr from-emerald-100/50 to-cyan-100/50 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

            {/* Grid Pattern */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(0,0,0,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.015)_1px,transparent_1px)] bg-[size:24px_24px]" />

            <div className="relative h-full overflow-auto">
              <AnimatePresence mode="wait">
                {step === 'INPUT' && (
                  <motion.div key="input" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.3 }} className="h-full p-6 sm:p-8">
                    <InputStep />
                  </motion.div>
                )}
                {step === 'PROPOSAL' && (
                  <motion.div key="proposal" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.3 }} className="h-full p-6 sm:p-8">
                    <ProposalStep />
                  </motion.div>
                )}
                {step === 'BUILDING' && (
                  <motion.div key="building" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }} className="h-full p-6 sm:p-8">
                    <BuildingStep />
                  </motion.div>
                )}
                {step === 'COMPLETE' && (
                  <motion.div key="complete" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }} className="h-full">
                    <CompleteStep />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
