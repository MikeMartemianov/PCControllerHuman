import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const DEFAULT_API_URL = import.meta.env.VITE_API_URL || '';

export const useSettingsStore = create<{
  apiUrl: string;
  apiKey: string;
  setApiUrl: (v: string) => void;
  setApiKey: (v: string) => void;
}>()(
  persist(
    (set) => ({
      apiUrl: DEFAULT_API_URL,
      apiKey: '',
      setApiUrl: (apiUrl) => set({ apiUrl }),
      setApiKey: (apiKey) => set({ apiKey }),
    }),
    { name: 'appforge-settings' }
  )
);
