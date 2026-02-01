import { Bot, Check, MessageSquare, RefreshCw, Sparkles, ArrowRight, Wand2 } from 'lucide-react';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useLanguageStore } from '../../lib/i18n/store';
import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { motion } from 'framer-motion';

export function ProposalStep() {
  const { data, updateData, setStep } = useWizardStore();
  const { t } = useLanguageStore();
  const [analyzing, setAnalyzing] = useState(!data.description);
  const [description, setDescription] = useState(data.description || '');
  const [error, setError] = useState<string | null>(null);
  const [refinement, setRefinement] = useState('');

  useEffect(() => {
    if (!analyzing || !data.userRequest) return;
    
    let cancelled = false;
    
    const generateProposal = async () => {
      try {
        setError(null);
        const prompt = `You are AppForge AI - an automated coding agent.

YOUR CAPABILITIES:
- Create, edit, and delete any files and folders
- Generate code in ANY language: JavaScript, TypeScript, Python, C#, Swift, Kotlin, C++, Rust, Go, etc.
- Create ANY type of application: web apps, mobile apps, games (Unity, Unreal), desktop apps, CLI tools, APIs, etc.
- Run terminal commands (npm, pip, dotnet, gradle, cargo, etc.)
- Install dependencies and set up project structures

YOUR LIMITATIONS:
- You CANNOT see the screen or any visual output
- You CANNOT interact with GUI elements or click buttons
- You work ONLY through text: reading/writing files and running terminal commands
- You cannot verify visual appearance - you work blindly based on code

USER REQUEST:
"${data.userRequest}"

TASK:
Write a detailed proposal (3-5 sentences) explaining what you will build. Be specific about:
- Technologies and frameworks you'll use
- Key features you'll implement
- File structure you'll create

Also suggest a short project name (2-3 words).

Respond in JSON format:
{
  "proposal": "Your detailed proposal here...",
  "projectName": "Short Name"
}`;

        const response = await api.aiChat(prompt);
        if (cancelled) return;

        let proposal = '';
        let projectName = 'New App';
        
        try {
          const text = typeof response === 'string' ? response : response?.response || response?.message || '';
          const jsonMatch = text.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            proposal = parsed.proposal || text;
            projectName = parsed.projectName || 'New App';
          } else {
            proposal = text;
          }
        } catch {
          proposal = typeof response === 'string' ? response : response?.response || response?.message || 'I will create the application based on your requirements.';
        }

        setDescription(proposal);
        updateData({ description: proposal, name: projectName });
        setAnalyzing(false);
      } catch (err) {
        if (cancelled) return;
        console.error('AI proposal error:', err);
        setError(err instanceof Error ? err.message : 'Failed to generate proposal');
        const fallback = `I will create an application based on your request: "${data.userRequest}". The app will include all the features you described with a modern, user-friendly interface.`;
        setDescription(fallback);
        updateData({ description: fallback, name: 'New App' });
        setAnalyzing(false);
      }
    };

    generateProposal();
    return () => { cancelled = true; };
  }, [analyzing, data.userRequest, updateData]);

  const handleRefinement = () => {
    if (!refinement.trim()) return;
    updateData({ userRequest: data.userRequest + " . REFINEMENT: " + refinement });
    setRefinement('');
    setAnalyzing(true);
  };

  if (analyzing) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[50vh]">
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="relative mb-8"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-500 blur-2xl opacity-30 animate-pulse" />
          <div className="relative h-24 w-24 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-2xl shadow-blue-500/30">
            <Wand2 className="h-12 w-12 text-white animate-pulse" />
          </div>
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('wiz.prop.analyzing')}</h2>
        <p className="text-gray-500 mb-6">{t('wiz.prop.consulting')}</p>
        <div className="flex gap-1">
          {[0, 1, 2].map(i => (
            <motion.div
              key={i}
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
              className="h-3 w-3 rounded-full bg-blue-500"
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto min-h-[50vh]">
      {error && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm flex items-center gap-3"
        >
          <div className="h-8 w-8 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
            <span className="text-lg">⚠️</span>
          </div>
          <div>
            <p className="font-medium">AI Error</p>
            <p className="text-red-500">{error}</p>
          </div>
        </motion.div>
      )}
      
      <div className="space-y-6 flex-1 overflow-auto p-1">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex gap-4"
        >
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/20">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <div className="space-y-4 flex-1">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none p-6 relative shadow-lg">
              <div className="absolute -top-3 left-4 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                AI Proposal
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4 mt-2">{t('wiz.prop.title')}</h3>
              <div className="prose max-w-none text-gray-600 whitespace-pre-wrap leading-relaxed text-base">
                {description}
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <button 
                onClick={() => { setDescription(''); setAnalyzing(true); }} 
                className="flex items-center gap-2 px-4 py-2 hover:bg-gray-100 rounded-xl text-gray-500 text-sm transition-all border border-transparent hover:border-gray-200"
              >
                <RefreshCw className="h-4 w-4" />
                {t('wiz.prop.regenerate')}
              </button>
            </div>

            {/* Refinement Chat */}
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-4 border border-gray-200">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                <MessageSquare className="h-3.5 w-3.5" />
                Refine Proposal
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={refinement}
                  onChange={(e) => setRefinement(e.target.value)}
                  className="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  placeholder="Add dark mode, change framework, etc..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleRefinement();
                    }
                  }}
                />
                <button 
                  onClick={handleRefinement}
                  disabled={!refinement.trim()}
                  className="px-4 py-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-300 rounded-xl text-white transition-all disabled:cursor-not-allowed"
                >
                  <ArrowRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="mt-8 pt-6 border-t border-gray-200 flex justify-between">
        <button
          onClick={() => setStep('INPUT')}
          className="flex items-center gap-2 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-medium transition-all"
        >
          <RefreshCw className="h-4 w-4" />
          Change Plan
        </button>
        <button
          onClick={() => setStep('BUILDING')}
          className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white rounded-xl font-semibold transition-all shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:-translate-y-0.5"
        >
          <Check className="h-5 w-5" />
          {t('wiz.prop.approve')}
        </button>
      </div>
    </div>
  );
}
