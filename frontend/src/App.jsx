import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Database, Activity } from 'lucide-react';

// UWAGA: Zmień na swój URL Cloud Run po deploymencie
const API_URL = import.meta.env.VITE_API_URL || "";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [threadId, setThreadId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll do dołu przy nowej wiadomości
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setInput('');

    try {
      const response = await fetch(`${API_URL}/agent/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: input, 
          thread_id: threadId 
        }),
      });

      const data = await response.json();
      
      if (!threadId) setThreadId(data.thread_id);

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: data.response,
        metadata: data.metadata 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'error', 
        content: "Błąd połączenia z agentem. Sprawdź czy backend jest uruchomiony." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const resetChat = () => {
    setMessages([]);
    setThreadId(null);
    setInput('');
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex justify-between items-center shadow-sm">
        <div className="flex items-center gap-2">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Database className="text-white w-5 h-5" />
          </div>
          <h1 className="font-bold text-xl tracking-tight">EPIR Analyst ADK</h1>
        </div>
        <div className="flex items-center gap-4">
          {threadId && (
            <span className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-1 rounded">
              Session: {threadId.split('-')[0]}
            </span>
          )}
          {messages.length > 0 && (
            <button 
              onClick={resetChat}
              className="text-xs text-slate-400 hover:text-slate-600 px-3 py-1 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Nowa rozmowa
            </button>
          )}
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
            <Bot size={48} strokeWidth={1} />
            <p className="text-lg">Zadaj pytanie analityczne dotyczące BigQuery...</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-8 max-w-2xl">
              <button 
                onClick={() => setInput("Pokaż dostępne datasety")}
                className="text-left p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all text-sm"
              >
                📊 Pokaż dostępne datasety
              </button>
              <button 
                onClick={() => setInput("Ile rekordów jest w tabeli sprzedaży?")}
                className="text-left p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all text-sm"
              >
                🔢 Ile rekordów w tabeli?
              </button>
            </div>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl p-4 shadow-sm ${
              m.role === 'user' 
                ? 'bg-blue-600 text-white rounded-br-none' 
                : m.role === 'error' 
                  ? 'bg-red-50 text-red-600 border border-red-100' 
                  : 'bg-white border text-slate-800 rounded-bl-none'
            }`}>
              <div className="flex items-start gap-3">
                {m.role === 'assistant' && <Bot className="w-5 h-5 mt-1 text-blue-600 flex-shrink-0" />}
                <div className="space-y-2 min-w-0 flex-1">
                  <p className="leading-relaxed whitespace-pre-wrap break-words">{m.content}</p>
                  
                  {m.metadata && (
                    <div className="flex gap-4 pt-2 border-t border-slate-100 mt-2 text-[10px] items-center text-slate-400 font-medium">
                      <span className="flex items-center gap-1">
                        <Activity size={10}/> Kroki: {m.metadata.steps}
                      </span>
                      <span className="flex items-center gap-1">
                        <Database size={10}/> Narzędzia: {m.metadata.tool_calls}
                      </span>
                    </div>
                  )}
                </div>
                {m.role === 'user' && <User className="w-5 h-5 mt-1 text-blue-100 flex-shrink-0" />}
              </div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border rounded-2xl p-4 flex items-center gap-2 text-slate-400 shadow-sm">
              <Loader2 className="animate-spin w-4 h-4" />
              <span className="text-sm">Agent myśli...</span>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </main>

      {/* Input Area */}
      <footer className="p-4 md:p-6 bg-white border-t">
        <form onSubmit={sendMessage} className="max-w-4xl mx-auto relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Np. Ile produktów sprzedaliśmy w zeszłym miesiącu?"
            className="w-full bg-slate-100 border-none rounded-xl py-4 pl-4 pr-14 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-inner"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-2 top-2 bottom-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 transition-colors shadow-lg shadow-blue-200 disabled:shadow-none"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <p className="text-center text-[10px] text-slate-400 mt-4 uppercase tracking-widest font-bold">
          Powered by Vertex AI & LangGraph
        </p>
      </footer>
    </div>
  );
}
