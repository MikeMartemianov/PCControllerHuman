import { Bot, Settings as SettingsIcon, Key, Globe, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

export function Settings() {
  const [aiStatus, setAiStatus] = useState<{ configured: boolean; provider: string; message?: string; baseURL?: string } | null>(null);
  const [checking, setChecking] = useState(false);

  const checkAi = async () => {
    setChecking(true);
    try {
      const status = await api.aiStatus();
      setAiStatus(status);
    } catch (error) {
      setAiStatus({ configured: false, provider: 'Error', message: error instanceof Error ? error.message : 'Unable to reach AI server' });
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkAi();
  }, []);

  return (
    <div className="max-w-2xl space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center">
          <SettingsIcon className="h-6 w-6 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm">Configure AI provider and API keys</p>
        </div>
      </div>

      {/* AI Status Card */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${aiStatus?.configured ? 'bg-emerald-100' : 'bg-amber-100'}`}>
              <Bot className={`h-5 w-5 ${aiStatus?.configured ? 'text-emerald-600' : 'text-amber-600'}`} />
            </div>
            <div>
              <p className="text-sm text-gray-500">AI Provider</p>
              <p className="text-lg font-semibold text-gray-900">
                {aiStatus?.configured ? aiStatus.provider : 'Not Configured'}
              </p>
            </div>
          </div>
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${aiStatus?.configured ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600'}`}>
            {aiStatus?.configured ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        {aiStatus?.baseURL && (
          <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
            <Globe className="h-4 w-4 text-gray-400" />
            <span className="font-mono text-xs">{aiStatus.baseURL}</span>
          </div>
        )}

        {aiStatus?.message && (
          <p className="text-sm text-gray-500">{aiStatus.message}</p>
        )}

        <button
          onClick={checkAi}
          disabled={checking}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${checking ? 'animate-spin' : ''}`} />
          {checking ? 'Checking...' : 'Refresh Status'}
        </button>
      </div>

      {/* Configuration Instructions */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <Key className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-gray-900 font-semibold">API Configuration</p>
            <p className="text-sm text-gray-500">Add your API key to server/.env</p>
          </div>
        </div>

        <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm space-y-2">
          <p className="text-gray-400"># Option 1: OpenAI</p>
          <p className="text-emerald-400">OPENAI_API_KEY=sk-...</p>
          <p className="text-gray-600 mt-3"># Option 2: Cerebras</p>
          <p className="text-blue-400">CEREBRAS_API_KEY=csk-...</p>
          <p className="text-gray-400">OPENAI_BASE_URL=https://api.cerebras.ai/v1</p>
        </div>

        <p className="text-xs text-gray-500">
          After adding the key, restart the server for changes to take effect.
        </p>
      </div>
    </div>
  );
}
