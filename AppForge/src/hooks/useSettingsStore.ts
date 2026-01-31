import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useSettingsStore = create<{
  apiUrl: string;
  apiKey: string;
  setApiUrl: (v: string) => void;
  setApiKey: (v: string) => void;
}>()(
  persist(
    (set) => ({
      apiUrl: '',
      apiKey: '',
      setApiUrl: (apiUrl) => set({ apiUrl }),
      setApiKey: (apiKey) => set({ apiKey }),
    }),
    { name: 'appforge-settings' }
  )
);
