import { Outlet, Link, useLocation } from 'react-router-dom';
import { Home, Settings, Sparkles } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { icon: Home, label: 'Dashboard', path: '/' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

export function AppShell() {
  const location = useLocation();
  return (
    <div className="min-h-screen flex bg-slate-50">
      <aside className="w-64 flex-shrink-0 bg-slate-900 text-white flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center shadow-lg">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="font-display font-bold text-lg tracking-tight">AppForge</h1>
            <p className="text-slate-400 text-xs">Build apps with AI</p>
          </div>
        </div>
        <nav className="px-3 flex-1 py-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                location.pathname === item.path ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto p-6 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
