import { Key, Save, Check } from 'lucide-react';
import { useState } from 'react';
import { useSettingsStore } from '../hooks/useSettingsStore';
import { api } from '../lib/api';

export function Settings() {
  const { apiUrl, apiKey, setApiUrl, setApiKey } = useSettingsStore();
  const [url, setUrl] = useState(apiUrl);
  const [key, setKey] = useState(apiKey);
  const [saved, setSaved] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ configured: boolean; provider: string } | null>(null);

  const handleSave = () => {
    setApiUrl(url);
    setApiKey(key);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const checkAi = () => {
    api.aiStatus().then(setAiStatus).catch(() => setAiStatus({ configured: false, provider: 'Error' }));
  };

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-display font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">Configure API for AI features</p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">API URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="http://localhost:3001"
            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          />
          <p className="text-xs text-slate-500 mt-1">Leave default when running server locally</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2 flex items-center gap-2">
            <Key className="h-4 w-4" /> API Key (OpenAI / Cerebras)
          </label>
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="sk-..."
            className="w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          />
          <p className="text-xs text-slate-500 mt-1">Stored locally. Set on server .env for backend AI.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-medium transition-colors"
          >
            {saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}
            {saved ? 'Saved' : 'Save'}
          </button>
          <button
            onClick={checkAi}
            className="px-5 py-2.5 border border-slate-200 rounded-xl font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Check AI status
          </button>
        </div>
        {aiStatus && (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm">
            AI: {aiStatus.configured ? `Configured (${aiStatus.provider})` : 'Not configured'}
          </div>
        )}
      </div>

      <div className="text-sm text-slate-500">
        <p>For EXE: run server separately or bundle it. For APK: use a deployed server URL.</p>
      </div>
    </div>
  );
}
