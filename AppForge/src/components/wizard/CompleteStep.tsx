import { ArrowLeft, Code2, Monitor, FileCode, Send, Bot, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

export function CompleteStep() {
  const { data, reset } = useWizardStore();
  const [activeTabIdx, setActiveTabIdx] = useState(0);
  const [fileContent, setFileContent] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([{ role: 'ai' as const, content: 'Project created. How can I help you refine it?' }]);
  const [chatLoading, setChatLoading] = useState(false);

  const deliverables = data.deliverables || [];
  const activeItem = deliverables[activeTabIdx];

  useEffect(() => {
    if (!activeItem || activeItem.type !== 'code' || !activeItem.file) return;
    setLoadingFile(true);
    api.getFile(data.name!, activeItem.file).then(setFileContent).catch(() => setFileContent('Error loading file.')).finally(() => setLoadingFile(false));
  }, [activeItem, data.name]);

  const sendMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMessage = chatInput;
    setChatHistory((prev) => [...prev, { role: 'user' as const, content: userMessage }]);
    setChatInput('');
    setChatLoading(true);
    try {
      const context = `Project: ${data.name}. Description: ${data.description || 'N/A'}`;
      const result = await api.aiChat(userMessage, context);
      setChatHistory((prev) => [...prev, { role: 'ai' as const, content: result.response }]);
    } catch (e) {
      setChatHistory((prev) => [...prev, { role: 'ai' as const, content: 'Error: ' + (e instanceof Error ? e.message : 'Failed') }]);
    } finally {
      setChatLoading(false);
    }
  };

  const previewBase = typeof window !== 'undefined' ? (window.location.origin.includes('localhost') ? 'http://localhost:3001' : window.location.origin) : '';

  return (
    <div className="h-full flex flex-col md:flex-row">
      <div className="flex-1 flex flex-col p-4 md:p-6 overflow-hidden">
        <div className="flex items-center justify-between mb-4 flex-shrink-0 flex-wrap gap-2">
          <div>
            <h2 className="text-xl font-bold text-slate-900">{data.name}</h2>
            <p className="text-slate-500 text-sm">Generated successfully</p>
          </div>
          <Link to="/" onClick={reset} className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-600 text-sm">
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
        </div>
        <div className="flex gap-2 border-b border-slate-200 mb-0 flex-shrink-0 overflow-x-auto pb-2">
          {deliverables.map((item, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTabIdx(idx)}
              className={clsx(
                'pb-2 text-sm font-medium whitespace-nowrap px-2',
                idx === activeTabIdx ? 'text-brand-600 border-b-2 border-brand-600' : 'text-slate-500 hover:text-slate-900'
              )}
            >
              <span className="flex items-center gap-2">
                {item.type === 'code' ? <Code2 className="h-4 w-4" /> : item.type === 'htmlpreview' ? <Monitor className="h-4 w-4" /> : item.type === 'link' ? <Globe className="h-4 w-4" /> : <FileCode className="h-4 w-4" />}
                {item.label}
              </span>
            </button>
          ))}
        </div>
        <div className="flex-1 bg-white border border-slate-200 rounded-b-xl rounded-tr-xl overflow-hidden flex flex-col min-h-0">
          <AnimatePresence mode="wait">
            {activeItem?.type === 'htmlpreview' && (
              <motion.div key="htmlpreview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col bg-slate-50 relative min-h-[300px]">
                <iframe
                  src={previewBase + (activeItem.url || '')}
                  className="flex-1 w-full border-none min-h-[300px]"
                  title="Preview"
                />
                <div className="absolute bottom-4 right-4">
                  <a href={previewBase + (activeItem.url || '')} target="_blank" rel="noreferrer" className="px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-full shadow-lg hover:bg-slate-800">
                    Open in new tab
                  </a>
                </div>
              </motion.div>
            )}
            {activeItem?.type === 'code' && (
              <motion.div key="code" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden bg-slate-900 text-slate-300 font-mono text-sm min-h-[200px]">
                {loadingFile ? (
                  <div className="flex-1 flex items-center justify-center text-slate-500">Loading...</div>
                ) : (
                  <>
                    <textarea
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      className="flex-1 w-full min-h-[300px] bg-slate-900 text-slate-300 p-4 focus:outline-none resize-none font-mono text-sm"
                      spellCheck={false}
                    />
                    <div className="p-2 border-t border-slate-700 flex justify-end">
                      <button
                        onClick={() => {
                          if (activeItem.file) api.saveFile(data.name!, activeItem.file, fileContent).then(() => alert('Saved')).catch(alert);
                        }}
                        className="px-4 py-2 bg-brand-600 text-white text-xs font-bold rounded-lg hover:bg-brand-500"
                      >
                        Save
                      </button>
                    </div>
                  </>
                )}
              </motion.div>
            )}
            {activeItem?.type === 'download' && (
              <motion.div key="download" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex items-center justify-center p-8 bg-slate-50">
                <div className="p-8 bg-white rounded-xl shadow-sm border border-slate-200 text-center">
                  <FileCode className="h-12 w-12 text-brand-600 mx-auto mb-4" />
                  <h3 className="text-lg font-bold text-slate-900 mb-2">{activeItem.label}</h3>
                  <a
                    href={`${previewBase}/api/download?project=${encodeURIComponent(data.name!)}&file=${activeItem.file || ''}`}
                    className="inline-block px-6 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800"
                  >
                    Download
                  </a>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      <div className="w-full md:w-80 border-t md:border-t-0 md:border-l border-slate-200 bg-slate-50 flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-white">
          <h3 className="font-bold text-slate-900 flex items-center gap-2">
            <Bot className="h-5 w-5 text-brand-600" /> AI Assistant
          </h3>
          <p className="text-xs text-slate-500 mt-1">Ask to modify your project</p>
        </div>
        <div className="flex-1 overflow-auto p-4 space-y-3 min-h-[200px]">
          {chatHistory.map((msg, i) => (
            <div key={i} className={clsx('flex gap-2', msg.role === 'user' ? 'flex-row-reverse' : '')}>
              <div className={clsx('h-7 w-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold', msg.role === 'ai' ? 'bg-brand-100 text-brand-600' : 'bg-slate-200 text-slate-600')}>
                {msg.role === 'ai' ? <Bot className="h-4 w-4" /> : 'U'}
              </div>
              <div className={clsx('p-3 rounded-xl text-sm max-w-[85%]', msg.role === 'ai' ? 'bg-white border border-slate-200 text-slate-700' : 'bg-brand-600 text-white')}>{msg.content}</div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex gap-2">
              <div className="h-7 w-7 rounded-full bg-brand-100 text-brand-600 flex items-center justify-center">
                <Bot className="h-4 w-4 animate-pulse" />
              </div>
              <div className="p-3 rounded-xl text-sm bg-white border border-slate-200 text-slate-400">Thinking...</div>
            </div>
          )}
        </div>
        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              placeholder="Ask AI..."
            />
            <button onClick={sendMessage} className="p-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition-colors">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
