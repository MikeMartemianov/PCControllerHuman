import { ArrowLeft, Code2, Monitor, FileCode, Send, Bot, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import { motion, AnimatePresence } from 'framer-motion';

type ChatMessage = {
  role: 'ai' | 'user';
  content: string;
};

export function CompleteStep() {
  const { data, reset } = useWizardStore();
  const [activeTabIdx, setActiveTabIdx] = useState(0);
  const [fileContent, setFileContent] = useState('');
  const [loadingFile, setLoadingFile] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([{ role: 'ai', content: 'Project created! How can I help you refine it?' }]);
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
    setChatHistory((prev) => [...prev, { role: 'user', content: userMessage }]);
    setChatInput('');
    setChatLoading(true);
    try {
      const context = `Project: ${data.name}. Description: ${data.description || 'N/A'}`;
      const result = await api.aiChat(userMessage, context);
      setChatHistory((prev) => [...prev, { role: 'ai', content: result.response }]);
    } catch (e) {
      setChatHistory((prev) => [...prev, { role: 'ai', content: 'Error: ' + (e instanceof Error ? e.message : 'Failed') }]);
    } finally {
      setChatLoading(false);
    }
  };

  const previewBase = typeof window !== 'undefined'
    ? ((() => {
        const hostname = window.location.hostname;
        const isFile = window.location.protocol.startsWith('file');
        const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]' || !hostname;
        return isFile || isLocal ? 'http://localhost:3001' : window.location.origin;
      })())
    : '';

  return (
    <div className="h-full flex">
      <div className="flex-1 flex flex-col p-6 overflow-hidden">
        <div className="flex items-center justify-between mb-4 flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{data.name}</h2>
            <p className="text-gray-500 text-sm">Successfully generated</p>
          </div>
          <Link to="/" onClick={reset} className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 text-sm transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>

        <div className="flex items-center gap-4 border-b border-gray-200 mb-0 flex-shrink-0 overflow-x-auto">
          {deliverables.map((item, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTabIdx(idx)}
              className={`pb-3 text-sm font-medium transition-all relative whitespace-nowrap ${idx === activeTabIdx ? 'text-blue-600' : 'text-gray-400 hover:text-gray-900'}`}
            >
              <span className="flex items-center gap-2">
                {item.type === 'code' ? <Code2 className="h-4 w-4" /> :
                  item.type === 'htmlpreview' ? <Monitor className="h-4 w-4" /> :
                    item.type === 'link' ? <Globe className="h-4 w-4" /> :
                      <FileCode className="h-4 w-4" />}
                {item.label}
              </span>
              {idx === activeTabIdx && <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />}
            </button>
          ))}
        </div>

        <div className="flex-1 bg-white border border-gray-200 rounded-b-xl rounded-tr-xl overflow-hidden flex flex-col relative shadow-sm">
          <AnimatePresence mode="wait">
            {activeItem?.type === 'htmlpreview' && (
              <motion.div key="htmlpreview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col bg-gray-50 relative">
                <iframe
                  src={previewBase + (activeItem.url || '')}
                  className="flex-1 w-full border-none"
                  title="HTML Preview"
                />
                <div className="absolute bottom-4 right-4">
                  <a
                    href={previewBase + (activeItem.url || '')}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-gray-900 text-white text-xs font-bold rounded-full shadow-lg hover:bg-gray-800"
                  >
                    Open in New Tab
                  </a>
                </div>
              </motion.div>
            )}

            {activeItem?.type === 'link' && (
              <motion.div key="link" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col bg-gray-50 relative">
                <iframe src={activeItem.url} className="flex-1 w-full border-none" title="External Link" sandbox="allow-scripts allow-same-origin" />
              </motion.div>
            )}

            {activeItem?.type === 'code' && (
              <motion.div key="code" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden bg-gray-900 text-gray-100 font-mono text-sm relative">
                {loadingFile ? (
                  <div className="flex-1 flex items-center justify-center text-gray-400">Loading...</div>
                ) : (
                  <>
                    <textarea
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      className="flex-1 w-full h-full bg-gray-900 text-gray-100 p-6 focus:outline-none resize-none font-mono text-sm leading-relaxed"
                      spellCheck={false}
                    />
                    <div className="absolute top-4 right-4">
                      <button
                        onClick={() => {
                          if (activeItem.file) {
                            api.saveFile(data.name!, activeItem.file, fileContent)
                              .then(() => alert('Saved!'))
                              .catch(e => alert(e.message));
                          }
                        }}
                        className="px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-lg shadow-lg hover:bg-blue-700"
                      >
                        Save
                      </button>
                    </div>
                  </>
                )}
              </motion.div>
            )}

            {activeItem?.type === 'download' && (
              <motion.div key="download" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50">
                <div className="p-8 bg-white rounded-xl shadow-sm border border-gray-200 text-center">
                  <FileCode className="h-12 w-12 text-blue-600 mx-auto mb-4" />
                  <h3 className="text-lg font-bold text-gray-900 mb-2">{activeItem.label}</h3>
                  <a
                    href={`${previewBase}/api/download?project=${encodeURIComponent(data.name!)}&file=${activeItem.file}`}
                    className="inline-block px-6 py-2 bg-gray-100 text-gray-900 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Download
                  </a>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="w-80 border-l border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600">
          <h3 className="font-bold text-white flex items-center gap-2">
            <Bot className="h-5 w-5" />
            AI Assistant
          </h3>
          <p className="text-xs text-white/80 mt-1">Ask me to modify your project</p>
        </div>

        <div className="flex-1 overflow-auto p-4 space-y-3 bg-gray-50">
          {chatHistory.map((msg, i) => (
            <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`h-7 w-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${msg.role === 'ai' ? 'bg-blue-100 text-blue-600' : 'bg-gray-200 text-gray-700'}`}>
                {msg.role === 'ai' ? <Bot className="h-4 w-4" /> : 'U'}
              </div>
              <div className={`p-3 rounded-xl text-sm max-w-[85%] ${msg.role === 'ai' ? 'bg-white border border-gray-200 text-gray-700' : 'bg-blue-600 text-white'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex gap-2">
              <div className="h-7 w-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                <Bot className="h-4 w-4 animate-pulse" />
              </div>
              <div className="p-3 rounded-xl text-sm bg-white border border-gray-200 text-gray-500">
                Thinking...
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex gap-2">
            <input
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') sendMessage(); }}
              className="flex-1 bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
              placeholder="Ask AI..."
            />
            <button
              onClick={sendMessage}
              disabled={chatLoading || !chatInput.trim()}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
