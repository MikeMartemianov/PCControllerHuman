import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const DEFAULT_API_URL = import.meta.env.VITE_API_URL || '';

export const useSettingsStore = create<{
  apiUrl: string;
  apiKey: string;
  baseURL: string;
  model: string;
  setApiUrl: (v: string) => void;
  setApiKey: (v: string) => void;
  setBaseURL: (v: string) => void;
  setModel: (v: string) => void;
}>()(
  persist(
    (set) => ({
      apiUrl: DEFAULT_API_URL,
      apiKey: '',
      baseURL: '',
      model: 'llama-3.3-70b',
      setApiUrl: (apiUrl) => set({ apiUrl }),
      setApiKey: (apiKey) => set({ apiKey }),
      setBaseURL: (baseURL) => set({ baseURL }),
      setModel: (model) => set({ model }),
    }),
    { name: 'appforge-settings' }
  )
);
