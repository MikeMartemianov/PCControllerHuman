import { Bot, Settings as SettingsIcon, Key, Globe, RefreshCw, Save, Trash2, Plus, Edit } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useSettingsStore } from '../hooks/useSettingsStore';

export function Settings() {
  const { apiKey, baseURL, model, setApiKey, setBaseURL, setModel } = useSettingsStore();
  const [systemPrompt, setSystemPrompt] = useState('');
  const [memories, setMemories] = useState<string[]>([]);
  const [newMemory, setNewMemory] = useState('');
  const [editingPrompt, setEditingPrompt] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ configured: boolean; provider: string; message?: string; baseURL?: string } | null>(null);
  const [checking, setChecking] = useState(false);

  const saveSystemPrompt = async () => {
    try {
      await api.setAiSystemPrompt(systemPrompt);
      setEditingPrompt(false);
    } catch (error) {
      alert('Failed to save system prompt');
    }
  };

  const addMemory = async () => {
    if (!newMemory.trim()) return;
    try {
      await api.addAiMemory(newMemory.trim());
      setMemories([...memories, newMemory.trim()]);
      setNewMemory('');
    } catch (error) {
      alert('Failed to add memory');
    }
  };

  const deleteMemory = async (index: number) => {
    try {
      await api.deleteAiMemory(index);
      setMemories(memories.filter((_, i) => i !== index));
    } catch (error) {
      alert('Failed to delete memory');
    }
  };

  const clearMemories = async () => {
    if (!confirm('Clear all memories?')) return;
    try {
      await api.clearAiMemories();
      setMemories([]);
    } catch (error) {
      alert('Failed to clear memories');
    }
  };

  const checkAi = async () => {
    setChecking(true);
    try {
      const res = await api.aiStatus();
      setAiStatus(res);
    } catch (error) {
      setAiStatus({ configured: false, provider: 'Error', message: 'Failed to check AI status' });
    } finally {
      setChecking(false);
    }
  };

  const saveConfig = async () => {
    try {
      await api.configureAi({ apiKey, baseURL, model });
      await checkAi();
    } catch (error) {
      alert('Failed to save configuration');
    }
  };

  useEffect(() => {
    checkAi();
    loadSystemPrompt();
    loadMemories();
  }, []);

  const loadSystemPrompt = async () => {
    try {
      const res = await api.aiSystemPrompt();
      setSystemPrompt(res.prompt);
    } catch (error) {
      console.error('Failed to load system prompt:', error);
    }
  };

  const loadMemories = async () => {
    try {
      const res = await api.aiMemories();
      setMemories(res);
    } catch (error) {
      console.error('Failed to load memories:', error);
    }
  };

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

      {/* AI Configuration */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <Key className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-gray-900 font-semibold">AI Configuration</p>
            <p className="text-sm text-gray-500">Configure your AI provider settings</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-... or csk-..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base URL (optional)</label>
            <input
              type="text"
              value={baseURL}
              onChange={(e) => setBaseURL(e.target.value)}
              placeholder="https://api.openai.com/v1 or https://api.cerebras.ai/v1"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="llama-3.3-70b or gpt-4o-mini"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <button
          onClick={saveConfig}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
        >
          Save Configuration
        </button>
      </div>

      {/* AI Memory Management */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-purple-100 flex items-center justify-center">
            <Bot className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <p className="text-gray-900 font-semibold">AI Memory</p>
            <p className="text-sm text-gray-500">Manage AI system prompt and memories</p>
          </div>
        </div>

        {/* System Prompt */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">System Prompt</label>
            <button
              onClick={() => setEditingPrompt(!editingPrompt)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {editingPrompt ? 'Cancel' : 'Edit'}
            </button>
          </div>
          {editingPrompt ? (
            <div className="space-y-2">
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={saveSystemPrompt}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
              >
                <Save className="h-4 w-4" />
                Save
              </button>
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
              {systemPrompt || 'Loading...'}
            </div>
          )}
        </div>

        {/* Memories */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Memories ({memories.length})</label>
            <button
              onClick={clearMemories}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Clear All
            </button>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {memories.map((memory, index) => (
              <div key={index} className="flex items-center gap-2 bg-gray-50 rounded-lg p-3">
                <span className="flex-1 text-sm text-gray-700">{memory}</span>
                <button
                  onClick={() => deleteMemory(index)}
                  className="text-red-500 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-2">
            <input
              type="text"
              value={newMemory}
              onChange={(e) => setNewMemory(e.target.value)}
              placeholder="Add new memory..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onKeyDown={(e) => e.key === 'Enter' && addMemory()}
            />
            <button
              onClick={addMemory}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
