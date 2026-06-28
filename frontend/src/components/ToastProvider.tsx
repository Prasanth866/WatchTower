import React, { createContext, useContext, useState } from 'react';
import { ToastMessage } from '../types';
import { Bell, X, CheckCircle, AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

interface ToastContextType {
  toasts: ToastMessage[];
  addToast: (type: ToastMessage['type'], title: string, message: string) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: ToastMessage['type'], title: string, message: string) => {
    const id = `toast_${Math.random().toString(36).substr(2, 9)}`;
    const newToast: ToastMessage = {
      id,
      type,
      title,
      message,
      timestamp: new Date().toLocaleTimeString(),
    };
    setToasts((prev) => [newToast, ...prev]);

    // Auto-dismiss after 6 seconds
    setTimeout(() => {
      dismissToast(id);
    }, 6000);
  };

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };


  return (
    <ToastContext.Provider value={{ toasts, addToast, dismissToast }}>
      {children}
      
      {/* Toast Overlay Container */}
      <div id="toast-container" className="fixed top-6 right-6 z-50 flex flex-col gap-3 w-full max-w-sm pointer-events-none">
        <AnimatePresence mode="popLayout">
          {toasts.map((toast) => {
            // Determine styling based on type
            let bgStyle = 'bg-slate-900/95 border-slate-800 text-slate-100';
            let iconColor = 'text-sky-400';
            let Icon = Info;
            let accentGlow = 'rgba(14, 165, 233, 0.15)';

            if (toast.type === 'success') {
              bgStyle = 'bg-zinc-950/95 border-emerald-500/40 text-emerald-50';
              iconColor = 'text-emerald-400';
              Icon = CheckCircle;
              accentGlow = 'rgba(16, 185, 129, 0.2)';
            } else if (toast.type === 'error') {
              bgStyle = 'bg-zinc-950/95 border-rose-500/40 text-rose-50';
              iconColor = 'text-rose-400';
              Icon = AlertTriangle;
              accentGlow = 'rgba(244, 63, 94, 0.2)';
            } else if (toast.type === 'alert') {
              bgStyle = 'bg-zinc-950/95 border-amber-500/50 text-amber-50 shadow-[0_0_15px_rgba(245,158,11,0.1)]';
              iconColor = 'text-amber-400 animate-pulse';
              Icon = ShieldAlert;
              accentGlow = 'rgba(245, 158, 11, 0.25)';
            }

            return (
              <motion.div
                key={toast.id}
                layout
                initial={{ opacity: 0, y: -20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                style={{ boxShadow: `0 4px 20px -2px ${accentGlow}` }}
                className={`flex items-start gap-3 p-4 rounded-xl border backdrop-blur-md pointer-events-auto ${bgStyle}`}
              >
                <div className={`mt-0.5 p-1.5 rounded-lg bg-white/5 ${iconColor}`}>
                  <Icon size={18} />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-sm tracking-wide">{toast.title}</span>
                    <span className="text-[10px] text-zinc-500 font-mono">{toast.timestamp}</span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{toast.message}</p>
                </div>

                <button
                  id={`dismiss-${toast.id}`}
                  onClick={() => dismissToast(toast.id)}
                  className="p-1 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-colors"
                >
                  <X size={14} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
