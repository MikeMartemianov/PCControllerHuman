import { motion } from 'framer-motion';
import { CheckCircle2, Box, Cpu, FileJson, Layout, AlertTriangle } from 'lucide-react';
import { useEffect, useState, useRef } from 'react';
import { useWizardStore } from '../../hooks/useWizardStore';
import { api } from '../../lib/api';

const TASKS = [
  { icon: FileJson, label: 'Initialize project' },
  { icon: Box, label: 'Install dependencies' },
  { icon: Layout, label: 'Create UI' },
  { icon: Cpu, label: 'Generate logic' },
  { icon: CheckCircle2, label: 'Finalize' },
];

export function BuildingStep() {
  const { setStep, data } = useWizardStore();
  const [activeTask, setActiveTask] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const hasStarted = useRef(false);
  const createdName = useRef<string | null>(null);

  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    const run = async () => {
      try {
        const base = (data.userRequest || 'my-app').split(' ').slice(0, 3).join('-').replace(/[^\w\-]/g, '') || 'app';
        const uniqueName = base + '-' + Date.now();
        if (createdName.current) return;
        const result = await api.createProject({
          name: uniqueName,
          description: data.description || data.userRequest || 'Generated app',
          type: 'web',
        });
        createdName.current = uniqueName;
        useWizardStore.getState().updateData({ name: uniqueName, deliverables: result.deliverables });
        for (let i = 0; i < TASKS.length; i++) {
          setActiveTask(i);
          await new Promise((r) => setTimeout(r, 400));
        }
        setStep('COMPLETE');
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Build failed');
      }
    };
    run();
  }, [data, setStep]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
        <AlertTriangle className="h-16 w-16 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-slate-900">Build failed</h2>
        <p className="text-slate-500 mt-2 mb-6">{error}</p>
        <button
          onClick={() => setStep('INPUT')}
          className="px-6 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-900 transition-colors"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] max-w-md mx-auto">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        className="mb-10 h-24 w-24 rounded-full border-4 border-dashed border-brand-300"
      />
      <div className="mb-8 flex items-center justify-center">
        <Box className="h-12 w-12 text-brand-600 animate-pulse" />
      </div>
      <h2 className="text-xl font-display font-bold text-slate-900 mb-8">Building your app...</h2>
      <div className="w-full space-y-3">
        {TASKS.map((task, i) => (
          <div key={i} className="flex items-center gap-4">
            <div
              className={`h-8 w-8 rounded-full flex items-center justify-center border transition-all ${
                i < activeTask ? 'bg-emerald-100 border-emerald-500 text-emerald-600' : i === activeTask ? 'bg-brand-100 border-brand-500 text-brand-600' : 'bg-slate-100 border-slate-200 text-slate-400'
              }`}
            >
              {i < activeTask ? <CheckCircle2 className="h-5 w-5" /> : <task.icon className="h-4 w-4" />}
            </div>
            <span className={`text-sm font-medium ${i <= activeTask ? 'text-slate-900' : 'text-slate-400'}`}>{task.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
