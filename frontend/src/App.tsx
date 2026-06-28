import React, { useState, useEffect } from 'react';
import { api, connectPriceFeed, disconnectPriceFeed } from './api';
import { CoinId, UserProfile } from './types';
import { ToastProvider, useToast } from './components/ToastProvider';
import { TickerRibbon } from './components/TickerRibbon';
import { HealthBanner } from './components/HealthBanner';
import { AuthLayout } from './components/AuthLayout';
import { CoinAnalysis } from './components/CoinAnalysis';
import { TriggerEngine } from './components/TriggerEngine';
import { TradingTerminal } from './components/TradingTerminal';
import { SettingsPanel } from './components/SettingsPanel';
import { Shield, Coins, Bell, Briefcase, Settings, LogOut, Menu, X, ArrowUpRight } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

type ViewMode = 'coins' | 'triggers' | 'trading' | 'settings';

function AppContent() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(true);
  const [activeView, setActiveView] = useState<ViewMode>('coins');
  const [selectedCoinId, setSelectedCoinId] = useState<CoinId>('btc');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { addToast } = useToast();

  // 1. Verify Authentication Token on Mount
  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const currentUser = await api.getCurrentUser();
        if (currentUser) {
          setUser(currentUser);
        }
      } catch {
        // Clear token
        localStorage.removeItem('watchtower_token');
      } finally {
        setIsAuthenticating(false);
      }
    };
    verifyAuth();
  }, []);

  // 2. WebSocket price feed — reconnects when selected coin changes
  useEffect(() => {
    if (!user) return;

    connectPriceFeed(selectedCoinId, (alertPayload: object) => {
      const p = alertPayload as { topic?: string; value?: number; threshold_direction?: string; threshold_value?: number };
      addToast(
        'alert',
        'Price Alert Triggered',
        `${(p.topic ?? '').toUpperCase()} is ${p.threshold_direction ?? ''} $${p.threshold_value?.toLocaleString() ?? ''} — current: $${p.value?.toLocaleString() ?? ''}`,
      );
    });

    return () => disconnectPriceFeed();
  }, [selectedCoinId, user]);

  const handleAuthSuccess = (authenticatedUser: UserProfile) => {
    setUser(authenticatedUser);
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    addToast('info', 'Disconnected', 'Ingress credential token removed. Session terminated.');
  };

  if (isAuthenticating) {
    return (
      <div id="app-loading-screen" className="min-h-screen bg-[#06080F] flex flex-col items-center justify-center gap-4 text-zinc-100 select-none">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-mono tracking-widest text-indigo-400">CONNECTING TO CLEARING DESK...</span>
      </div>
    );
  }

  if (!user) {
    return <AuthLayout onAuthSuccess={handleAuthSuccess} />;
  }

  // Sidebar navigation menu options
  const navItems = [
    { id: 'coins', label: 'Coins Deep Dive', icon: Coins },
    { id: 'triggers', label: 'Trigger Engine', icon: Bell },
    { id: 'trading', label: 'Paper Trading', icon: Briefcase },
    { id: 'settings', label: 'User Settings', icon: Settings },
  ] as const;

  return (
    <div id="app-workspace-layout" className="min-h-screen bg-[#06080F] text-zinc-100 flex flex-col font-sans select-none overflow-x-hidden">
      
      {/* GLOBAL SCROLLING TICKER RIBBON AT TOP */}
      <TickerRibbon
        selectedCoinId={selectedCoinId}
        onSelectCoin={(id) => {
          setSelectedCoinId(id);
          setActiveView('coins'); // auto-switch to coin analysis view if ticker clicked!
        }}
      />

      {/* CORE FRAMEWORK WORKSPACE */}
      <div className="flex-1 flex relative">
        
        {/* DESKTOP SIDEBAR NAVIGATION */}
        <aside id="desktop-sidebar" className="hidden lg:flex flex-col justify-between w-64 bg-zinc-950 border-r border-zinc-900/80 p-5 shrink-0 z-20">
          <div className="space-y-6">
            
            {/* Logo/Identity */}
            <div className="flex items-center gap-2 px-1">
              <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Shield size={18} />
              </div>
              <div>
                <span className="text-sm font-extrabold tracking-tight text-white flex items-center">
                  WATCH<span className="text-indigo-400">TOWER</span>
                </span>
                <span className="text-[8px] text-zinc-500 font-mono block mt-0.5 font-bold uppercase tracking-widest">
                  OPERATOR WORKSPACE
                </span>
              </div>
            </div>

            {/* Menu Links */}
            <nav className="flex flex-col gap-1.5 pt-4">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;
                return (
                  <button
                    key={item.id}
                    id={`sidebar-link-${item.id}`}
                    onClick={() => setActiveView(item.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-xs font-bold font-mono tracking-wide uppercase text-left transition-all cursor-pointer ${
                      isActive
                        ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400 shadow-[0_4px_12px_rgba(99,102,241,0.06)]'
                        : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/30'
                    }`}
                  >
                    <Icon size={14} className={isActive ? 'text-indigo-400' : 'text-zinc-500'} />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* User Signout segment */}
          <div className="border-t border-zinc-900/80 pt-4 mt-6">
            <div className="flex items-center gap-3 px-2 mb-4">
              <div className="w-8 h-8 rounded-full bg-indigo-500/5 border border-indigo-500/20 text-indigo-400 font-mono text-xs font-bold flex items-center justify-center">
                {user.email.substring(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <span className="block text-xs font-black text-zinc-200 truncate leading-none">{user.email}</span>
                <span className="text-[9px] text-zinc-500 font-mono tracking-wider truncate mt-1 block">LVL: SUPER_OPERATOR</span>
              </div>
            </div>

            <button
              id="desktop-logout-btn"
              onClick={handleLogout}
              className="w-full h-10 border border-zinc-900 bg-zinc-950 hover:bg-rose-950/10 hover:border-rose-900/20 text-xs font-mono font-bold tracking-widest uppercase text-zinc-500 hover:text-rose-400 rounded-xl transition-all cursor-pointer flex items-center justify-center gap-2"
            >
              <LogOut size={13} />
              LOGOUT TERMINAL
            </button>
          </div>
        </aside>

        {/* MOBILE SIDEBAR PANEL OVERLAY */}
        <AnimatePresence>
          {isSidebarOpen && (
            <>
              {/* Overlay shadow */}
              <motion.div
                id="mobile-sidebar-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.7 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsSidebarOpen(false)}
                className="fixed inset-0 bg-black z-30 lg:hidden"
              />
              <motion.aside
                id="mobile-sidebar"
                initial={{ x: -280 }}
                animate={{ x: 0 }}
                exit={{ x: -280 }}
                transition={{ type: 'spring', damping: 25, stiffness: 220 }}
                className="fixed left-0 top-0 bottom-0 w-64 bg-zinc-950 border-r border-zinc-900 p-5 flex flex-col justify-between z-40 lg:hidden"
              >
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 px-1">
                      <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                        <Shield size={16} />
                      </div>
                      <span className="text-sm font-extrabold tracking-tight text-white flex items-center">
                        WATCH<span className="text-indigo-400">TOWER</span>
                      </span>
                    </div>
                    <button
                      id="close-mobile-sidebar"
                      onClick={() => setIsSidebarOpen(false)}
                      className="p-1.5 text-zinc-500 hover:text-zinc-300 rounded-lg hover:bg-zinc-900"
                    >
                      <X size={16} />
                    </button>
                  </div>

                  <nav className="flex flex-col gap-1.5 pt-4">
                    {navItems.map((item) => {
                      const Icon = item.icon;
                      const isActive = activeView === item.id;
                      return (
                        <button
                          key={item.id}
                          id={`mobile-sidebar-link-${item.id}`}
                          onClick={() => {
                            setActiveView(item.id);
                            setIsSidebarOpen(false);
                          }}
                          className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-xs font-bold font-mono tracking-wide uppercase text-left cursor-pointer transition-all ${
                            isActive
                              ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                              : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/30'
                          }`}
                        >
                          <Icon size={14} className={isActive ? 'text-indigo-400' : 'text-zinc-500'} />
                          {item.label}
                        </button>
                      );
                    })}
                  </nav>
                </div>

                <div className="border-t border-zinc-900 pt-4 mt-6">
                  <button
                    id="mobile-logout-btn"
                    onClick={handleLogout}
                    className="w-full h-10 bg-zinc-900 text-zinc-500 hover:text-rose-400 text-xs font-mono font-bold tracking-widest uppercase rounded-xl transition-colors cursor-pointer flex items-center justify-center gap-2"
                  >
                    <LogOut size={13} />
                    LOGOUT
                  </button>
                </div>
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        {/* WORKSPACE WORKFLOW CANVAS (Right / Main) */}
        <main id="workspace-main" className="flex-1 min-w-0 p-4 md:p-6 lg:p-8 flex flex-col gap-6 overflow-y-auto">
          
          {/* Header toolbar banner */}
          <div className="flex items-center justify-between gap-4 border-b border-zinc-900 pb-4">
            <div className="flex items-center gap-3">
              <button
                id="toggle-mobile-sidebar"
                onClick={() => setIsSidebarOpen(true)}
                className="p-2 bg-zinc-950 border border-zinc-900 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 lg:hidden cursor-pointer"
              >
                <Menu size={16} />
              </button>
              <div>
                <h1 className="text-lg md:text-xl font-extrabold tracking-tight text-zinc-100 font-sans uppercase">
                  {activeView === 'coins' && 'Asset Intel Dashboard'}
                  {activeView === 'triggers' && 'Smart Alarm Control'}
                  {activeView === 'trading' && 'Paper Clearing Terminal'}
                  {activeView === 'settings' && 'Workspace Preferences'}
                </h1>
                <span className="text-[10px] text-zinc-500 font-mono tracking-wider font-semibold">
                  WATCHTOWER SECURE NODE PROTOCOL v3.2.14-RELEASE
                </span>
              </div>
            </div>

            {/* Global System Health dropdown */}
            <HealthBanner />
          </div>

          {/* VIEW RENDER ROUTER CANVAS */}
          <div className="flex-1">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeView}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.15 }}
                className="h-full"
              >
                {activeView === 'coins' && (
                  <CoinAnalysis
                    selectedCoinId={selectedCoinId}
                    onSelectCoin={setSelectedCoinId}
                  />
                )}
                {activeView === 'triggers' && <TriggerEngine />}
                {activeView === 'trading' && <TradingTerminal />}
                {activeView === 'settings' && (
                  <SettingsPanel user={user} onUpdateUser={setUser} />
                )}
              </motion.div>
            </AnimatePresence>
          </div>

        </main>

      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}
