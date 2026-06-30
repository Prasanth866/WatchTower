import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { SystemHealth } from '../types';
import { Activity, Server, Database, Flame, CheckCircle, ChevronDown, RefreshCw } from 'lucide-react';

export const HealthBanner: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [latency, setLatency] = useState<number | null>(null);

  const fetchHealth = async () => {
    setIsRefreshing(true);
    const start = performance.now();
    try {
      const data = await api.getHealth();
      const end = performance.now();
      setLatency(Math.round(end - start));
      setHealth(data);
    } catch {
      const end = performance.now();
      setLatency(Math.round(end - start));
      setHealth({
        api: 'down',
        redis: 'down',
        postgres: 'down',
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // 30s polling
    return () => clearInterval(interval);
  }, []);

  if (!health) {
    return (
      <div id="health-banner-loading" className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500">
        <Activity size={12} className="animate-pulse text-indigo-400" />
        <span>SYS CHECK...</span>
      </div>
    );
  }

  // Determine global color
  let statusColor = 'text-emerald-400';
  let statusBg = 'bg-emerald-500/10 border-emerald-500/20';
  let dotPulse = 'bg-emerald-400';
  let statusText = 'SYSTEMS OPERATIONAL';

  const workersOk = health.workers?.overall === 'ok' || health.workers?.overall === undefined ? 'ok' : 'error';

  const services = [
    { name: 'Core API',     status: health.api,      icon: Server   },
    { name: 'Redis Cache',  status: health.redis,    icon: Flame    },
    { name: 'Postgres DB',  status: health.postgres, icon: Database },
    { name: 'Alert Workers', status: workersOk,      icon: Activity },
  ];

  const downCount = services.filter((s) => s.status !== 'ok').length;

  if (downCount === services.length) {
    statusColor = 'text-rose-400';
    statusBg = 'bg-rose-500/10 border-rose-500/20';
    dotPulse = 'bg-rose-500';
    statusText = 'ALL SYSTEMS DOWN';
  } else if (downCount > 0) {
    statusColor = 'text-amber-400';
    statusBg = 'bg-amber-500/10 border-amber-500/20';
    dotPulse = 'bg-amber-400';
    statusText = 'DEGRADED PERFORMANCE';
  }

  return (
    <div id="health-banner-container" className="relative">
      <button
        id="health-banner-button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-left cursor-pointer transition-all duration-300 ${statusBg}`}
      >
        <span className="relative flex h-2.5 w-2.5">
          {health.status === 'ok' && (
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotPulse}`}></span>
          )}
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${dotPulse}`}></span>
        </span>

        <span className={`text-[11px] font-mono font-bold tracking-wider ${statusColor} hidden md:inline`}>
          {statusText}
        </span>

        <span className={`text-[11px] font-mono font-bold tracking-wider ${statusColor} md:hidden`}>
          {health.api === 'ok' && health.redis === 'ok' && health.postgres === 'ok' ? 'SYS OK' : 'SYS FAIL'}
        </span>

        <ChevronDown size={12} className={`text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Health Detail Dropdown */}
      {isOpen && (
        <>
          <div
            id="health-banner-overlay"
            className="fixed inset-0 z-20"
            onClick={() => setIsOpen(false)}
          />
          <div
            id="health-banner-dropdown"
            className="absolute right-0 mt-2 w-64 bg-zinc-950 border border-zinc-800 rounded-xl p-4 shadow-2xl z-30 backdrop-blur-md"
          >
            <div className="flex items-center justify-between border-b border-zinc-900 pb-3 mb-3">
              <span className="text-xs font-bold font-mono text-zinc-400 tracking-wider">INFRASTRUCTURE INTEGRITY</span>
              <button
                id="refresh-health-btn"
                onClick={fetchHealth}
                disabled={isRefreshing}
                className="p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900 transition-colors"
              >
                <RefreshCw size={12} className={isRefreshing ? 'animate-spin text-indigo-400' : ''} />
              </button>
            </div>

            <div className="flex flex-col gap-2.5">
              {services.map((service) => {
                const isServiceOk = service.status === 'ok';
                const IconComponent = service.icon;

                return (
                  <div key={service.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-mono text-zinc-300">
                      <IconComponent size={14} className={isServiceOk ? 'text-zinc-500' : 'text-rose-400'} />
                      <span>{service.name}</span>
                    </div>

                    <div className="flex items-center gap-1.5 font-mono text-[10px]">
                      <span className={isServiceOk ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                        {isServiceOk ? 'OK' : 'OFFLINE'}
                      </span>
                      <CheckCircle
                        size={12}
                        className={isServiceOk ? 'text-emerald-400' : 'text-rose-500'}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="border-t border-zinc-900 pt-3 mt-3 flex justify-between items-center text-[10px] text-zinc-500 font-mono">
              <span>LATENCY: {latency !== null ? `~${latency}ms` : '--'}</span>
              <span>CACHE TTL: 15s</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
