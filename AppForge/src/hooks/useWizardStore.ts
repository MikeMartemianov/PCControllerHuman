import { create } from 'zustand';

export type WizardStep = 'INPUT' | 'PROPOSAL' | 'SPECS' | 'BUILDING' | 'COMPLETE';

export const useWizardStore = create<{
  step: WizardStep;
  data: { userRequest?: string; description?: string; name?: string; folderPath?: string; deliverables?: { type: string; label: string; file?: string; url?: string }[] };
  setStep: (s: WizardStep) => void;
  updateData: (d: Partial<{ userRequest: string; description: string; name: string; folderPath: string; deliverables: any[] }>) => void;
  reset: () => void;
}>((set) => ({
  step: 'INPUT',
  data: {},
  setStep: (step) => set({ step }),
  updateData: (d) => set((s) => ({ data: { ...s.data, ...d } })),
  reset: () => set({ step: 'INPUT', data: {} }),
}));
