import { Sparkles, Lightbulb, Zap, Code2, Gamepad2, Globe } from 'lucide-react';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useLanguageStore } from '../../lib/i18n/store';
import { useState } from 'react';

const suggestions = [
  { icon: Globe, text: 'A landing page for my startup', color: 'from-blue-500 to-cyan-500' },
  { icon: Gamepad2, text: 'A simple browser game', color: 'from-purple-500 to-pink-500' },
  { icon: Code2, text: 'A todo app with localStorage', color: 'from-emerald-500 to-teal-500' },
];

export function InputStep() {
  const { data, updateData, setStep } = useWizardStore();
  const { t } = useLanguageStore();
  const [value, setValue] = useState(data.userRequest || '');
  const [focused, setFocused] = useState(false);

  const handleNext = () => {
    if (!value.trim()) return;
    updateData({ userRequest: value.trim() });
    setStep('PROPOSAL');
  };

  return (
    <div className="flex flex-col h-full justify-center min-h-[60vh]">
      {/* Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm font-medium mb-4">
          <Zap className="h-4 w-4" />
          AI-Powered Development
        </div>
        <h2 className="text-4xl font-extrabold text-gray-900 mb-4 tracking-tight">{t('wiz.input.title')}</h2>
        <p className="text-gray-500 max-w-lg mx-auto text-lg">
          {t('wiz.input.subtitle')}
        </p>
      </div>

      {/* Input Area */}
      <div className={`relative max-w-2xl mx-auto w-full transition-all duration-300 ${focused ? 'scale-[1.02]' : ''}`}>
        <div className={`absolute -inset-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-3xl blur-lg transition-opacity duration-300 ${focused ? 'opacity-30' : 'opacity-0'}`} />
        <div className="relative">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={t('wiz.input.placeholder')}
            className="w-full h-52 bg-white border-2 border-gray-200 rounded-2xl p-6 text-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 resize-none transition-all shadow-lg"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.ctrlKey) handleNext();
            }}
          />
          <div className="absolute bottom-4 right-4 flex items-center gap-3">
            <span className="text-xs text-gray-400 hidden sm:inline">Ctrl + Enter</span>
            <button
              onClick={handleNext}
              disabled={!value.trim()}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-white rounded-xl font-semibold transition-all shadow-lg shadow-blue-500/25 disabled:shadow-none hover:shadow-blue-500/40 hover:-translate-y-0.5 disabled:hover:translate-y-0"
            >
              <Sparkles className="h-5 w-5" />
              {t('wiz.input.btn')}
            </button>
          </div>
        </div>
      </div>

      {/* Suggestions */}
      <div className="mt-8 max-w-2xl mx-auto w-full">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-3">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          <span>Try one of these ideas:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => setValue(s.text)}
              className="group flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:border-gray-300 rounded-xl text-sm text-gray-600 hover:text-gray-900 transition-all hover:shadow-md"
            >
              <div className={`h-6 w-6 rounded-lg bg-gradient-to-br ${s.color} flex items-center justify-center`}>
                <s.icon className="h-3.5 w-3.5 text-white" />
              </div>
              {s.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
