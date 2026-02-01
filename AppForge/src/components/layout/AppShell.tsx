import { Outlet, Link, useLocation } from 'react-router-dom';
import { Home, Settings, Sparkles, Layout, Bot, MessageCircle, X, Zap, Code2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { AIChatPanel } from '../../components/AIChatPanel';
import { api } from '../../lib/api';

export function AppShell() {
  const location = useLocation();
  const [chatOpen, setChatOpen] = useState(false);
  const [aiStatus, setAiStatus] = useState<{configured: boolean} | null>(null);

  useEffect(() => {
    api.aiStatus().then(setAiStatus).catch(() => setAiStatus({ configured: false }));
  }, []);

  const navItems = [
    { icon: Home, label: 'Dashboard', path: '/', description: 'Your projects' },
    { icon: Layout, label: 'Templates', path: '/templates', description: 'Starter templates' },
    { icon: Settings, label: 'Settings', path: '/settings', description: 'Configuration' },
  ];

  return (
    <div className="h-screen w-full bg-gradient-to-br from-slate-50 via-white to-blue-50 flex overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-72 bg-white/80 backdrop-blur-xl text-gray-900 flex flex-col flex-shrink-0 relative z-20 border-r border-gray-200/80 shadow-xl shadow-gray-200/20">
        {/* Logo */}
        <div className="p-6 flex items-center gap-4 select-none">
          <div className="h-12 w-12 bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/30 relative">
            <Sparkles className="h-6 w-6 text-white" />
            <div className="absolute -top-1 -right-1 h-4 w-4 bg-emerald-400 rounded-full border-2 border-white flex items-center justify-center">
              <Zap className="h-2 w-2 text-white" />
            </div>
          </div>
          <div>
            <h1 className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">AppForge</h1>
            <p className="text-gray-400 text-xs font-medium">AI-Powered Builder</p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="mx-4 mb-4 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
          <div className="flex items-center gap-2 text-xs">
            <div className={`h-2 w-2 rounded-full ${aiStatus?.configured ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            <span className="text-gray-600 font-medium">{aiStatus?.configured ? 'AI Connected' : 'AI Disconnected'}</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="px-3 flex-1 overflow-y-auto py-2 space-y-1">
          <div className="px-3 text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Navigation</div>
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group ${
                location.pathname === item.path
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg shadow-blue-500/25'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100/80'
              }`}
            >
              <item.icon className={`h-5 w-5 transition-transform group-hover:scale-110 ${location.pathname === item.path ? 'text-white' : 'text-gray-400 group-hover:text-blue-500'}`} />
              <div className="flex-1">
                <span className="block">{item.label}</span>
                {location.pathname === item.path && (
                  <span className="text-[10px] text-blue-100 opacity-80">{item.description}</span>
                )}
              </div>
              {location.pathname === item.path && (
                <div className="h-2 w-2 rounded-full bg-white/50" />
              )}
            </Link>
          ))}
        </div>

        {/* Create New Button */}
        <div className="px-4 py-3">
          <Link
            to="/create"
            className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white rounded-xl font-semibold transition-all shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:-translate-y-0.5"
          >
            <Code2 className="h-5 w-5" />
            Create New App
          </Link>
        </div>

        {/* AI Assistant Button */}
        <div className="p-4 border-t border-gray-100/80">
          <button
            onClick={() => setChatOpen(!chatOpen)}
            className="w-full flex items-center gap-3 px-4 py-4 rounded-xl bg-gradient-to-r from-violet-500 via-purple-500 to-fuchsia-500 text-white hover:from-violet-600 hover:via-purple-600 hover:to-fuchsia-600 transition-all shadow-lg shadow-purple-500/30 hover:shadow-purple-500/50 hover:-translate-y-0.5"
          >
            <div className="h-10 w-10 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-sm">
              <MessageCircle className="h-5 w-5" />
            </div>
            <div className="flex-1 text-left">
              <p className="text-sm font-bold">AI Assistant</p>
              <p className="text-xs text-purple-200">Ask anything</p>
            </div>
            <div className="h-3 w-3 rounded-full bg-white/30 animate-pulse" />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto relative">
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-blue-100/40 to-purple-100/40 rounded-full blur-3xl -z-10" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-emerald-100/30 to-cyan-100/30 rounded-full blur-3xl -z-10" />
        
        <div className="max-w-7xl mx-auto p-8 h-full">
          <Outlet />
        </div>
      </main>

      {/* Floating AI Button (Mobile) */}
      <button
        onClick={() => setChatOpen(!chatOpen)}
        className={`fixed bottom-6 right-6 h-14 w-14 rounded-2xl shadow-xl flex items-center justify-center transition-all z-40 hover:scale-105 md:hidden ${
          chatOpen 
            ? 'bg-gray-900 text-white rotate-90' 
            : 'bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white shadow-purple-500/30'
        }`}
        title="AI Assistant"
      >
        {chatOpen ? <X className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
      </button>

      {/* AI Chat Panel */}
      <AIChatPanel
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        context="User is in AppForge workspace."
      />
    </div>
  );
}
