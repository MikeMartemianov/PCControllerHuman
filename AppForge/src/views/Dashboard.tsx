import { Plus, Search, Globe, Trash2, Bot } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { api, type Project } from '../lib/api';

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProjects().then(setProjects).catch(() => setProjects([])).finally(() => setLoading(false));
  }, []);

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8">
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-display font-bold text-slate-900 tracking-tight">My Projects</h1>
          <p className="text-slate-500 mt-1">Create apps with AI, no code required</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-64 pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          />
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <Link
          to="/create"
          className="group flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed border-slate-200 hover:border-brand-400 hover:bg-brand-50/50 transition-all min-h-[220px] bg-white"
        >
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform text-white shadow-lg shadow-brand-500/30">
            <Plus className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900">New App</h3>
          <p className="text-sm text-slate-500 text-center mt-2 max-w-[200px]">Describe your app, AI builds it</p>
        </Link>

        {filtered.map((project, i) => (
          <Link to={`/project/${project.name}`} key={project.id} className="block h-full">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-white border border-slate-200 rounded-2xl p-6 hover:border-brand-200 hover:shadow-lg transition-all min-h-[220px] flex flex-col group relative"
            >
              <button
                onClick={(e) => {
                  e.preventDefault();
                  if (confirm('Delete this project?')) {
                    api.deleteProject(project.name).then(() => setProjects(projects.filter((p) => p.id !== project.id))).catch(alert);
                  }
                }}
                className="absolute top-3 right-3 p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                title="Delete"
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <div className="h-10 w-10 rounded-xl bg-slate-100 flex items-center justify-center mb-4">
                <Globe className="h-5 w-5 text-slate-600" />
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2 pr-8">{project.name}</h3>
              <p className="text-sm text-slate-500 line-clamp-2 flex-1">{project.description}</p>
              <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{project.status}</span>
                <span className="text-xs text-slate-400">{project.lastEdited}</span>
              </div>
            </motion.div>
          </Link>
        ))}

        {!loading && projects.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-12 text-slate-400">
            <Bot className="h-12 w-12 mb-4 opacity-50" />
            <p>No projects yet. Create your first app with AI.</p>
          </div>
        )}
      </div>
    </div>
  );
}
