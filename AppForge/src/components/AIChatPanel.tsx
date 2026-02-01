import { useState, useEffect, useRef } from 'react';
import { Bot, Send, X, Brain, AlertTriangle, Sparkles } from 'lucide-react';
import { api } from '../lib/api';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatMessage {
    role: 'user' | 'ai';
    content: string;
    blocked?: boolean;
}

interface AIChatPanelProps {
    isOpen: boolean;
    onClose: () => void;
    context?: string;
}

export function AIChatPanel({ isOpen, onClose, context }: AIChatPanelProps) {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([
        { role: 'ai', content: 'Hello! I\'m AppForge AI. I can create any app, run terminal commands, and manage files. How can I help you today?' }
    ]);
    const [loading, setLoading] = useState(false);
    const [aiStatus, setAiStatus] = useState<any>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (isOpen) {
            api.aiStatus().then(setAiStatus).catch(() => { });
        }
    }, [isOpen]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input;
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setInput('');
        setLoading(true);

        try {
            const result = await api.aiChat(userMessage, context);
            setMessages(prev => [...prev, {
                role: 'ai',
                content: result.response,
                blocked: result.blocked
            }]);
        } catch (e: any) {
            setMessages(prev => [...prev, {
                role: 'ai',
                content: `Error: ${e.message}`
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0, x: 300 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 300 }}
                    className="fixed right-0 top-0 bottom-0 w-96 bg-white shadow-2xl border-l border-gray-200 z-50 flex flex-col"
                >
                    {/* Header */}
                    <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-indigo-600">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-full bg-white/20 flex items-center justify-center">
                                    <Brain className="h-5 w-5 text-white" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-white">AI Assistant</h3>
                                    <p className="text-xs text-white/70">
                                        {aiStatus?.configured ? '🟢 Connected' : '🔴 Not configured'}
                                        {aiStatus?.provider ? ` • ${aiStatus.provider}` : ''}
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-lg hover:bg-white/20 transition-colors"
                            >
                                <X className="h-5 w-5 text-white" />
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-auto p-4 space-y-4 bg-gray-50">
                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                            >
                                <div className={`h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                                    msg.role === 'ai'
                                        ? msg.blocked
                                            ? 'bg-amber-100 text-amber-600'
                                            : 'bg-blue-100 text-blue-600'
                                        : 'bg-gray-200 text-gray-700'
                                }`}>
                                    {msg.role === 'ai'
                                        ? msg.blocked
                                            ? <AlertTriangle className="h-4 w-4" />
                                            : <Sparkles className="h-4 w-4" />
                                        : 'U'}
                                </div>
                                <div className={`p-3 rounded-2xl text-sm max-w-[80%] ${
                                    msg.role === 'ai'
                                        ? msg.blocked
                                            ? 'bg-amber-50 border border-amber-200 text-amber-700'
                                            : 'bg-white border border-gray-200 text-gray-700 shadow-sm'
                                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white'
                                }`}>
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="flex gap-3">
                                <div className="h-8 w-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                                    <Bot className="h-4 w-4 animate-pulse" />
                                </div>
                                <div className="p-3 rounded-2xl bg-white border border-gray-200 text-gray-500 text-sm shadow-sm">
                                    <span className="flex items-center gap-2">
                                        <span className="flex gap-1">
                                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </span>
                                        Thinking...
                                    </span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="p-4 border-t border-gray-200 bg-white">
                        <div className="flex gap-2">
                            <input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
                                className="flex-1 bg-gray-50 border border-gray-300 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
                                placeholder="Ask me anything..."
                            />
                            <button
                                onClick={sendMessage}
                                disabled={loading || !input.trim()}
                                className="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 transition-all"
                            >
                                <Send className="h-5 w-5" />
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
