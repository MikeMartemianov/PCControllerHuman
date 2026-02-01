import { motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, FileCode, Terminal, Loader2, Sparkles, Cpu, Zap } from 'lucide-react';
import { useEffect, useState, useRef, useCallback } from 'react';
import { useWizardStore } from '../../hooks/useWizardStore';
import { useSettingsStore } from '../../hooks/useSettingsStore';

type LogEntry = {
  type: 'status' | 'output' | 'file' | 'log' | 'error';
  message: string;
  file?: string;
};

export function BuildingStep() {
  const { setStep, data } = useWizardStore();
  const [phase, setPhase] = useState<'init' | 'thinking' | 'building' | 'complete' | 'error'>('init');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filesCreated, setFilesCreated] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const hasStarted = useRef(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const errorCountRef = useRef(0);

  const handleComplete = useCallback((uniqueName: string, deliverables: unknown[]) => {
    useWizardStore.getState().updateData({
      name: uniqueName,
      deliverables
    });
    setTimeout(() => setStep('COMPLETE'), 1500);
  }, [setStep]);

  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    const base = (data.userRequest || 'my-app').split(' ').slice(0, 3).join('-').replace(/[^\w\-]/g, '') || 'app';
    const uniqueName = base + '-' + Date.now();
    const task = data.userRequest || data.description || `Create a web app called "${uniqueName}"`;

    setLogs([{ type: 'status', message: '🚀 Connecting to AI Agent...' }]);

    const hostname = window.location.hostname;
    const isFile = window.location.protocol.startsWith('file');
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]' || !hostname;
    const settingsApi = useSettingsStore.getState().apiUrl?.trim();
    const baseFromSettings = settingsApi && settingsApi !== '/api' ? settingsApi.replace(/\/+$/, '') : '';
    const originBase = (isFile || isLocal) ? 'http://localhost:3001' : window.location.origin;
    const apiBase = baseFromSettings || (originBase + '/api');
    const normalizeApiBase = (value: string) => value.replace(/\/+$/, '');
    const apiRoot = normalizeApiBase(apiBase);
    const isApiRoot = apiRoot.endsWith('/api');
    const streamPath = isApiRoot ? '/agent/stream/' : '/api/agent/stream/';
    const statusPath = isApiRoot ? '/ai/status' : '/api/ai/status';
    const streamUrl = `${apiRoot}${streamPath}${encodeURIComponent(uniqueName)}?task=${encodeURIComponent(task)}`;
    const statusUrl = `${apiRoot}${statusPath}`;

    setLogs(prev => [...prev, { type: 'log', message: `SSE: ${streamUrl}` }]);

    const statusTimeout = setTimeout(() => {
      setLogs(prev => [...prev, { type: 'log', message: 'Status check timed out.' }]);
    }, 5000);

    fetch(statusUrl)
      .then(async (res) => {
        clearTimeout(statusTimeout);
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data = await res.json();
        setLogs(prev => [...prev, { type: 'log', message: `AI status: ${data.ready ? 'ready' : 'not ready'} (${data.provider || 'unknown'})` }]);
      })
      .catch((err) => {
        clearTimeout(statusTimeout);
        setLogs(prev => [...prev, { type: 'log', message: `AI status check failed: ${err.message}` }]);
      });

    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    const connectTimeout = setTimeout(() => {
      setError('Cannot connect to AI Agent. Server may be unreachable.');
      setPhase('error');
      eventSource.close();
    }, 30000);

    eventSource.onopen = () => {
      clearTimeout(connectTimeout);
      errorCountRef.current = 0;
      setLogs(prev => [...prev, { type: 'status', message: 'Connected to AI Agent.' }]);
    };

    eventSource.addEventListener('status', (e) => {
      clearTimeout(connectTimeout);
      errorCountRef.current = 0;
      const eventData = JSON.parse(e.data);
      setLogs(prev => [...prev, { type: 'status', message: eventData.message }]);
      if (eventData.phase === 'thinking') setPhase('thinking');
    });

    eventSource.addEventListener('output', (e) => {
      clearTimeout(connectTimeout);
      errorCountRef.current = 0;
      const eventData = JSON.parse(e.data);
      setLogs(prev => [...prev, { type: 'output', message: eventData.message }]);
      setPhase('building');
    });

    eventSource.addEventListener('file', (e) => {
      clearTimeout(connectTimeout);
      errorCountRef.current = 0;
      const eventData = JSON.parse(e.data);
      setFilesCreated(prev => [...prev, eventData.file]);
      setLogs(prev => [...prev, { type: 'file', message: `✓ Created: ${eventData.file}`, file: eventData.file }]);
    });

    eventSource.addEventListener('log', (e) => {
      clearTimeout(connectTimeout);
      errorCountRef.current = 0;
      const eventData = JSON.parse(e.data);
      if (eventData.message && !eventData.message.includes('INFO') && !eventData.message.includes('DEBUG')) {
        setLogs(prev => [...prev, { type: 'log', message: eventData.message }]);
      }
    });

    eventSource.addEventListener('complete', (e) => {
      errorCountRef.current = 0;
      const result = JSON.parse(e.data);
      setPhase('complete');
      setLogs(prev => [...prev, { type: 'status', message: '🎉 Build complete!' }]);
      eventSource.close();
      handleComplete(uniqueName, result.deliverables);
    });

    eventSource.addEventListener('agent_error', (e) => {
      errorCountRef.current = 0;
      try {
        const eventData = JSON.parse((e as MessageEvent).data);
        setError(eventData.message);
      } catch {
        // SSE connection error
      }
      setPhase('error');
      eventSource.close();
    });

    eventSource.onerror = () => {
      clearTimeout(connectTimeout);
      errorCountRef.current += 1;
      setLogs(prev => [...prev, { type: 'log', message: `SSE error (attempt ${errorCountRef.current})` }]);
      setPhase(prev => {
        if (prev === 'complete') return prev;
        if (errorCountRef.current < 3) return prev;
        setError('Connection to AI Agent lost. Make sure the server is running.');
        return 'error';
      });
      if (errorCountRef.current >= 3) {
        eventSource.close();
      }
    };

    return () => {
      eventSource.close();
    };
  }, [data, handleComplete]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="h-20 w-20 rounded-2xl bg-red-100 flex items-center justify-center mb-6">
          <AlertTriangle className="h-10 w-10 text-red-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Build Failed</h2>
        <p className="text-gray-600 mb-8 max-w-md">{error}</p>
        <button
          onClick={() => setStep('INPUT')}
          className="px-6 py-3 bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded-xl text-gray-700 font-medium transition-all"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="flex gap-6 h-full max-h-[70vh]">
      {/* Left: Status & Files */}
      <div className="w-80 flex flex-col gap-4">
        {/* AI Status */}
        <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center gap-4 mb-4">
            <div className="relative">
              <motion.div
                animate={{ rotate: phase === 'complete' ? 0 : 360 }}
                transition={{ duration: 2, repeat: phase === 'complete' ? 0 : Infinity, ease: 'linear' }}
                className={`h-14 w-14 rounded-xl flex items-center justify-center ${
                  phase === 'complete'
                    ? 'bg-gradient-to-br from-emerald-400 to-teal-500'
                    : 'bg-gradient-to-br from-blue-500 to-indigo-600'
                } shadow-lg ${phase === 'complete' ? 'shadow-emerald-500/30' : 'shadow-blue-500/30'}`}
              >
                {phase === 'complete' ? (
                  <CheckCircle2 className="h-7 w-7 text-white" />
                ) : (
                  <Cpu className="h-7 w-7 text-white" />
                )}
              </motion.div>
              {phase !== 'complete' && (
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-amber-400 border-2 border-white"
                />
              )}
            </div>
            <div>
              <h3 className="text-gray-900 font-bold text-lg">
                {phase === 'init' && 'Initializing...'}
                {phase === 'thinking' && 'AI Thinking...'}
                {phase === 'building' && 'Building App...'}
                {phase === 'complete' && 'Complete!'}
              </h3>
              <p className="text-sm text-gray-500">
                {phase === 'init' && 'Connecting to AI Agent'}
                {phase === 'thinking' && 'Planning the application'}
                {phase === 'building' && `Created ${filesCreated.length} files`}
                {phase === 'complete' && 'All files generated'}
              </p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              className={`h-full ${phase === 'complete' ? 'bg-gradient-to-r from-emerald-400 to-teal-500' : 'bg-gradient-to-r from-blue-500 to-indigo-500'}`}
              initial={{ width: '0%' }}
              animate={{
                width: phase === 'init' ? '10%' : phase === 'thinking' ? '30%' : phase === 'building' ? '70%' : '100%'
              }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {/* Files Created */}
        <div className="flex-1 bg-white border border-gray-200 rounded-2xl p-5 overflow-hidden flex flex-col shadow-lg">
          <h4 className="text-sm font-bold text-gray-700 mb-4 flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-emerald-100 flex items-center justify-center">
              <FileCode className="h-4 w-4 text-emerald-600" />
            </div>
            <span>Files Created</span>
            <span className="ml-auto px-2 py-0.5 bg-gray-100 rounded-full text-xs font-medium text-gray-600">{filesCreated.length}</span>
          </h4>
          <div className="flex-1 overflow-auto space-y-2">
            {filesCreated.length === 0 ? (
              <div className="flex items-center gap-3 text-sm text-gray-400 p-3 bg-gray-50 rounded-xl">
                <Loader2 className="h-4 w-4 animate-spin" />
                Waiting for AI to create files...
              </div>
            ) : (
              filesCreated.map((file, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-2 text-sm p-2 bg-emerald-50 border border-emerald-100 rounded-lg"
                >
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                  <span className="text-gray-700 font-mono truncate text-xs">{file}</span>
                </motion.div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Right: Live Console */}
      <div className="flex-1 bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden flex flex-col shadow-2xl">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-3 bg-gray-900/80">
          <div className="flex gap-1.5">
            <div className="h-3 w-3 rounded-full bg-red-500" />
            <div className="h-3 w-3 rounded-full bg-amber-500" />
            <div className="h-3 w-3 rounded-full bg-emerald-500" />
          </div>
          <Terminal className="h-4 w-4 text-gray-500 ml-2" />
          <span className="text-sm font-medium text-gray-400">AI Agent Console</span>
          <span className="ml-auto text-xs text-gray-600 font-mono">{logs.length} logs</span>
        </div>
        <div ref={logContainerRef} className="flex-1 overflow-auto p-4 font-mono text-sm space-y-1.5">
          {logs.map((log, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex items-start gap-2 ${
                log.type === 'status' ? 'text-blue-400' :
                log.type === 'output' ? 'text-gray-300' :
                log.type === 'file' ? 'text-emerald-400' :
                log.type === 'error' ? 'text-red-400' :
                'text-gray-500'
              }`}
            >
              {log.type === 'output' && <Sparkles className="h-4 w-4 mt-0.5 flex-shrink-0" />}
              {log.type === 'file' && <Zap className="h-4 w-4 mt-0.5 flex-shrink-0" />}
              {log.type === 'status' && <span className="text-blue-500 flex-shrink-0">›</span>}
              <span className="break-all">{log.message}</span>
            </motion.div>
          ))}
          {phase !== 'complete' && phase !== 'error' && (
            <span className="inline-block w-2.5 h-5 bg-blue-400 animate-pulse rounded-sm" />
          )}
        </div>
      </div>
    </div>
  );
}
