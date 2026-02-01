import { Plus, Search, Globe, Trash2, Bot, Smartphone, ExternalLink, Sparkles, Folder, Clock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { api, type Project } from '../lib/api';

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [hoveredProject, setHoveredProject] = useState<string | null>(null);

  const loadProjects = () => {
    setLoading(true);
    api.getProjects()
      .then((data) => { setProjects(data); setApiError(false); })
      .catch(() => { setProjects([]); setApiError(true); })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleDelete = async (e: React.MouseEvent, project: Project) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm(`Delete project "${project.name}"?\n\nThis will permanently delete all files.`)) {
      return;
    }

    setDeleting(project.id);
    try {
      await api.deleteProject(project.name);
      setProjects(prev => prev.filter(p => p.id !== project.id));
    } catch (err) {
      alert('Failed to delete: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setDeleting(null);
    }
  };

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getProjectGradient = (index: number) => {
    const gradients = [
      'from-blue-500 to-cyan-500',
      'from-violet-500 to-purple-500',
      'from-emerald-500 to-teal-500',
      'from-orange-500 to-amber-500',
      'from-pink-500 to-rose-500',
      'from-indigo-500 to-blue-500',
    ];
    return gradients[index % gradients.length];
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Folder className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">My Projects</h1>
          </div>
          <p className="text-gray-500 ml-13">Create, manage and deploy AI-powered applications</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 transition-colors group-focus-within:text-blue-500" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-72 pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm hover:shadow-md"
            />
          </div>
        </div>
      </header>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center">
            <Folder className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{projects.length}</p>
            <p className="text-sm text-gray-500">Total Projects</p>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-emerald-100 flex items-center justify-center">
            <Sparkles className="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{projects.filter(p => p.status === 'Complete').length}</p>
            <p className="text-sm text-gray-500">Completed</p>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-amber-100 flex items-center justify-center">
            <Clock className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{projects.filter(p => p.status === 'Building').length}</p>
            <p className="text-sm text-gray-500">In Progress</p>
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {/* Create New Card */}
        <Link
          to="/create"
          className="group relative flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed border-gray-200 hover:border-blue-400 hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 transition-all cursor-pointer h-72 card-hover"
        >
          <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-5 group-hover:scale-110 transition-all duration-300 shadow-lg shadow-blue-500/30 group-hover:shadow-blue-500/50">
            <Plus className="h-8 w-8 text-white" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Create New App</h3>
          <p className="text-sm text-gray-500 text-center max-w-[200px]">Start a new AI-powered coding session</p>
          <div className="absolute bottom-4 left-0 right-0 flex justify-center">
            <span className="text-xs text-blue-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity">Click to start →</span>
          </div>
        </Link>

        {/* Project Cards */}
        <AnimatePresence mode="popLayout">
          {filtered.map((project, i) => (
            <motion.div
              key={project.id}
              layout
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: -20 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              onMouseEnter={() => setHoveredProject(project.id)}
              onMouseLeave={() => setHoveredProject(null)}
            >
              <Link to={`/project/${project.name}`} className="block h-full">
                <div className={`bg-white border border-gray-200 rounded-2xl overflow-hidden hover:border-blue-300 transition-all group relative flex flex-col h-72 cursor-pointer card-hover ${deleting === project.id ? 'opacity-50 pointer-events-none' : ''}`}>
                  {/* Gradient Header */}
                  <div className={`h-24 bg-gradient-to-br ${getProjectGradient(i)} relative overflow-hidden`}>
                    <div className="absolute inset-0 bg-black/10" />
                    <div className="absolute -bottom-6 -right-6 h-24 w-24 bg-white/10 rounded-full blur-xl" />
                    <div className="absolute -top-6 -left-6 h-24 w-24 bg-white/10 rounded-full blur-xl" />
                    
                    {/* Delete Button */}
                    <button
                      onClick={(e) => handleDelete(e, project)}
                      disabled={deleting === project.id}
                      className="absolute top-3 right-3 p-2 bg-white/90 backdrop-blur border border-white/50 rounded-lg text-gray-500 hover:text-red-500 hover:bg-red-50 shadow-sm transition-all opacity-0 group-hover:opacity-100 z-10"
                      title="Delete Project"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>

                    {/* Icon */}
                    <div className="absolute bottom-0 left-5 translate-y-1/2 h-14 w-14 rounded-xl bg-white shadow-lg flex items-center justify-center border border-gray-100">
                      {project.type === 'web' ? <Globe className="h-6 w-6 text-gray-700" /> : <Smartphone className="h-6 w-6 text-gray-700" />}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 p-5 pt-10 flex flex-col">
                    <h3 className="text-lg font-bold text-gray-900 mb-1 truncate pr-4">{project.name}</h3>
                    <p className="text-sm text-gray-500 line-clamp-2 flex-1">{project.description}</p>

                    {/* Footer */}
                    <div className="mt-auto pt-4 border-t border-gray-100 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`h-2.5 w-2.5 rounded-full ${project.status === 'Building' ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
                        <span className="text-xs font-semibold text-gray-500">{project.status}</span>
                      </div>
                      <div className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${hoveredProject === project.id ? 'text-blue-600' : 'text-gray-400'}`}>
                        <ExternalLink className="h-3.5 w-3.5" />
                        Open
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading State */}
        {loading && (
          <div className="col-span-full flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-4">
              <div className="h-12 w-12 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-gray-500 font-medium">Loading projects...</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && projects.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
            <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center mb-5">
              <Bot className="h-10 w-10 text-gray-400" />
            </div>
            <p className="text-xl font-bold text-gray-900 mb-2">No projects yet</p>
            <p className="text-gray-500 mb-6 max-w-sm">Create your first AI-powered application and watch the magic happen!</p>
            <Link
              to="/create"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:-translate-y-0.5 transition-all"
            >
              <Plus className="h-5 w-5" />
              Create First App
            </Link>
            {apiError && (
              <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700 max-w-md">
                <p className="font-medium">Could not connect to server</p>
                <p className="mt-1">Run <code className="bg-amber-100 px-1.5 py-0.5 rounded text-xs font-mono">npm run dev:all</code> to start</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
