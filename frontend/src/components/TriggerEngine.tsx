import React, { useState, useEffect } from 'react';
import { api, SUPPORTED_COINS } from '../api';
import { CoinId, Trigger } from '../types';
import { useToast } from './ToastProvider';
import { AlertCircle, Plus, Trash2, Shield, ShieldOff, Calendar, Clock, Sliders, Check, BellRing } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export const TriggerEngine: React.FC = () => {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();

  // Wizard States
  const [step, setStep] = useState(1);
  const [wizardCoin, setWizardCoin] = useState<CoinId>('btc');
  const [wizardDirection, setWizardDirection] = useState<'above' | 'below'>('above');
  const [wizardThreshold, setWizardThreshold] = useState('');
  const [wizardCooldown, setWizardCooldown] = useState(60); // 60 minutes default
  const [wizardExpiration, setWizardExpiration] = useState('');

  const loadTriggers = async () => {
    setIsLoading(true);
    try {
      const data = await api.getTriggers();
      setTriggers(data);
    } catch {
      addToast('error', 'Retrieval Error', 'Could not sync price triggers with node.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTriggers();
  }, []);

  const handleToggleActive = async (id: string) => {
    try {
      const updated = await api.toggleTriggerActive(id);
      setTriggers((prev) => prev.map((t) => (t.id === id ? updated : t)));
      addToast(
        'success',
        'Trigger Updated',
        `Price trigger is now ${updated.is_active ? 'ACTIVE' : 'MUTED'}.`
      );
    } catch {
      addToast('error', 'Update Failed', 'Failed to change trigger activation state.');
    }
  };

  const handleDeleteTrigger = async (id: string) => {
    try {
      await api.deleteTrigger(id);
      setTriggers((prev) => prev.filter((t) => t.id !== id));
      addToast('success', 'Trigger Deleted', 'Alert threshold was permanently unmapped.');
    } catch {
      addToast('error', 'Deletion Failed', 'Failed to remove active trigger.');
    }
  };

  const handleCreateTrigger = async (e: React.FormEvent) => {
    e.preventDefault();
    const thresholdNum = parseFloat(wizardThreshold);
    if (isNaN(thresholdNum) || thresholdNum <= 0) {
      addToast('error', 'Validation Error', 'Please input a valid price threshold.');
      return;
    }

    try {
      await api.createTrigger({
        coinId: wizardCoin,
        direction: wizardDirection,
        threshold: thresholdNum,
        cooldown: wizardCooldown * 60, // convert minutes → seconds for api.ts mapping
        expiration: wizardExpiration ? new Date(wizardExpiration).toISOString() : null,
      });

      addToast('success', 'Trigger Provisioned', `Monitoring ${wizardCoin.toUpperCase()} for thresholds ${wizardDirection} $${thresholdNum.toLocaleString()}.`);
      
      // Reset & Close
      setIsWizardOpen(false);
      setStep(1);
      setWizardThreshold('');
      setWizardCooldown(60);
      setWizardExpiration('');
      loadTriggers();
    } catch (err: any) {
      addToast('error', 'Provision Error', err.message || 'Could not instantiate trigger.');
    }
  };

  const progressPercent = (step / 3) * 100;

  return (
    <div id="trigger-engine-container" className="flex flex-col gap-6">
      
      {/* Action Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-extrabold text-zinc-100 font-sans tracking-tight">Smart Trigger Wizard</h2>
          <p className="text-xs text-zinc-500 font-mono mt-1">STREAMING ENGINE ASSESSING WEB-SOCKET THRESHOLDS IN REAL TIME</p>
        </div>

        <button
          id="open-wizard-btn"
          onClick={() => {
            setIsWizardOpen(true);
            setStep(1);
          }}
          className="h-10 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold font-mono tracking-wider uppercase rounded-xl flex items-center gap-2 cursor-pointer transition-colors shadow-lg shadow-indigo-600/15"
        >
          <Plus size={14} />
          PROVISION ALARM
        </button>
      </div>

      {/* Grid of active triggers */}
      {triggers.length === 0 ? (
        <div id="empty-triggers-card" className="border border-zinc-900 bg-zinc-950/40 rounded-2xl p-12 text-center flex flex-col items-center justify-center max-w-xl mx-auto w-full mt-4">
          <div className="p-4 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-600 mb-4 animate-pulse">
            <BellRing size={28} />
          </div>
          <h3 className="text-sm font-bold text-zinc-300 font-sans">No Alarm Triggers Active</h3>
          <p className="text-xs text-zinc-500 mt-2 leading-relaxed max-w-sm">
            Configure price alarms above or below target thresholds. Once the WebSocket prices cross these values, you will be alerted instantly in real-time.
          </p>
          <button
            id="empty-state-open-wizard"
            onClick={() => setIsWizardOpen(true)}
            className="mt-5 text-xs font-mono font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5"
          >
            LAUNCH CONFIGURATION DESK →
          </button>
        </div>
      ) : (
        <div id="triggers-grid" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {triggers.map((trigger) => {
              const coinDetails = SUPPORTED_COINS[trigger.topic];
              const directionLabel = trigger.threshold_direction === 'above' ? 'Crosses Above' : 'Drops Below';

              return (
                <motion.div
                  key={trigger.id}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className={`bg-zinc-950/80 border rounded-xl p-5 backdrop-blur-md flex flex-col justify-between gap-4 transition-all duration-300 ${
                    trigger.is_active
                      ? 'border-zinc-800/80 shadow-[0_4px_15px_-4px_rgba(99,102,241,0.05)]'
                      : 'border-zinc-900/80 opacity-50'
                  }`}
                >
                  {/* Header metadata */}
                  <div className="flex items-center justify-between pb-3 border-b border-zinc-900/60">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center font-mono text-xs font-bold text-zinc-400">
                        {coinDetails?.symbol}
                      </div>
                      <div>
                        <span className="block text-xs font-bold text-zinc-100">{coinDetails?.name}</span>
                        <span className="text-[9px] font-mono text-zinc-500 uppercase">{trigger.id}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        id={`toggle-trigger-active-${trigger.id}`}
                        onClick={() => handleToggleActive(trigger.id)}
                        title={trigger.is_active ? 'Mute' : 'Activate'}
                        className={`p-1.5 rounded-lg border transition-all cursor-pointer ${
                          trigger.is_active
                            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                            : 'bg-zinc-900/60 border-zinc-850 text-zinc-500 hover:bg-zinc-900'
                        }`}
                      >
                        {trigger.is_active ? <Shield size={13} /> : <ShieldOff size={13} />}
                      </button>
                      <button
                        id={`delete-trigger-${trigger.id}`}
                        onClick={() => handleDeleteTrigger(trigger.id)}
                        className="p-1.5 rounded-lg bg-zinc-900/60 border border-zinc-850 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/5 transition-all cursor-pointer"
                        title="Delete"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Core Alarm Information */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-xs font-mono">
                      <span className="text-zinc-500 uppercase">Alert Mode:</span>
                      <span className={`font-bold ${trigger.threshold_direction === 'above' ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {directionLabel}
                      </span>
                    </div>

                    <div className="flex justify-between items-end">
                      <span className="text-[10px] font-mono text-zinc-500 uppercase pb-1 leading-none">Alarm Threshold:</span>
                      <span className="text-lg font-black text-zinc-100 font-mono tracking-tight leading-none">
                        ${trigger.threshold_value.toLocaleString(undefined, { minimumFractionDigits: trigger.topic === 'doge' || trigger.topic === 'ada' ? 4 : 2 })}
                      </span>
                    </div>

                    {/* Meta stats list */}
                    <div className="pt-2 border-t border-zinc-900/40 space-y-1.5 text-[10px] font-mono text-zinc-500">
                      <div className="flex justify-between">
                        <span className="flex items-center gap-1"><Clock size={10} /> Cooldown</span>
                        <span className="text-zinc-400 font-bold">{trigger.cooldown_minutes}min</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="flex items-center gap-1"><Calendar size={10} /> Expiration</span>
                        <span className="text-zinc-400">
                          {trigger.expires_at ? new Date(trigger.expires_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'NEVER'}
                        </span>
                      </div>
                      <div className="flex justify-between border-t border-zinc-900/40 pt-1.5 mt-1">
                        <span className="flex items-center gap-1"><AlertCircle size={10} /> Cumulative Fires</span>
                        <span className={`font-bold ${trigger.current_alert_count > 0 ? 'text-indigo-400' : 'text-zinc-600'}`}>
                          {trigger.current_alert_count} alerts
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      {/* Step-by-Step wizard Modal */}
      {isWizardOpen && (
        <div id="wizard-modal-overlay" className="fixed inset-0 bg-black/85 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl"
          >
            {/* Header progress line */}
            <div className="h-1 w-full bg-zinc-900">
              <div
                className="h-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="p-6">
              <div className="flex justify-between items-center pb-4 border-b border-zinc-900 mb-6">
                <div>
                  <h3 className="text-sm font-bold text-zinc-200 font-mono tracking-widest uppercase">TRIGGER WIZARD</h3>
                  <span className="text-[10px] text-zinc-500 font-mono">STEP {step} OF 3</span>
                </div>
                <button
                  id="close-wizard-modal"
                  onClick={() => setIsWizardOpen(false)}
                  className="text-zinc-500 hover:text-zinc-300 text-xs font-mono"
                >
                  ABORT
                </button>
              </div>

              <form onSubmit={handleCreateTrigger} className="space-y-6">
                {step === 1 && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-2">
                        Step 1: Select Monitored Crypto Asset
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {(Object.keys(SUPPORTED_COINS) as CoinId[]).map((id) => {
                          const isCoinSelected = wizardCoin === id;
                          return (
                            <button
                              key={id}
                              id={`wizard-coin-select-${id}`}
                              type="button"
                              onClick={() => setWizardCoin(id)}
                              className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                                isCoinSelected
                                  ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-400'
                                  : 'bg-zinc-900/30 border-zinc-900 text-zinc-400 hover:bg-zinc-900/50 hover:border-zinc-800'
                              }`}
                            >
                              <span className="block text-xs font-bold font-mono">{SUPPORTED_COINS[id].symbol}</span>
                              <span className="text-[10px] text-zinc-500 font-sans mt-0.5">{SUPPORTED_COINS[id].name}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="pt-4 flex justify-end">
                      <button
                        id="wizard-next-step-1"
                        type="button"
                        onClick={() => setStep(2)}
                        className="h-10 px-6 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold font-mono rounded-lg transition-colors cursor-pointer"
                      >
                        CONTINUE TO DIRECTION →
                      </button>
                    </div>
                  </div>
                )}

                {step === 2 && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-2">
                        Step 2: Define Threshold Boundary
                      </label>
                      
                      <div className="grid grid-cols-2 gap-2 mb-4">
                        <button
                          id="direction-above-btn"
                          type="button"
                          onClick={() => setWizardDirection('above')}
                          className={`p-3 rounded-lg border font-mono font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all ${
                            wizardDirection === 'above'
                              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.05)]'
                              : 'bg-zinc-900/30 border-zinc-900 text-zinc-500 hover:bg-zinc-900/50'
                          }`}
                        >
                          CROSSES ABOVE
                        </button>

                        <button
                          id="direction-below-btn"
                          type="button"
                          onClick={() => setWizardDirection('below')}
                          className={`p-3 rounded-lg border font-mono font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all ${
                            wizardDirection === 'below'
                              ? 'bg-rose-500/10 border-rose-500/40 text-rose-400 shadow-[0_0_12px_rgba(244,63,94,0.05)]'
                              : 'bg-zinc-900/30 border-zinc-900 text-zinc-500 hover:bg-zinc-900/50'
                          }`}
                        >
                          DROPS BELOW
                        </button>
                      </div>

                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-mono">$</span>
                        <input
                          id="wizard-threshold-input"
                          type="number"
                          step="any"
                          required
                          value={wizardThreshold}
                          onChange={(e) => setWizardThreshold(e.target.value)}
                          placeholder={`e.g. ${SUPPORTED_COINS[wizardCoin].basePrice}`}
                          className="w-full h-11 bg-zinc-900 border border-zinc-800 rounded-lg pl-8 pr-4 text-sm font-mono text-zinc-200 outline-none focus:border-indigo-500"
                        />
                      </div>
                      <span className="block text-[10px] text-zinc-500 mt-2 font-mono">
                        Target coin: {SUPPORTED_COINS[wizardCoin].name} ({SUPPORTED_COINS[wizardCoin].symbol})
                      </span>
                    </div>

                    <div className="pt-4 flex justify-between">
                      <button
                        id="wizard-prev-step-2"
                        type="button"
                        onClick={() => setStep(1)}
                        className="text-xs font-mono font-bold text-zinc-500 hover:text-zinc-300"
                      >
                        ← BACK
                      </button>
                      <button
                        id="wizard-next-step-2"
                        type="button"
                        onClick={() => setStep(3)}
                        disabled={!wizardThreshold}
                        className="h-10 px-6 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-900 disabled:text-zinc-600 text-white text-xs font-bold font-mono rounded-lg transition-colors cursor-pointer"
                      >
                        SET COOLDOWN & EXPIRE →
                      </button>
                    </div>
                  </div>
                )}

                {step === 3 && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between items-center mb-1.5">
                        <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider">
                          Step 3: Alert Cooldown Interval
                        </label>
                        <span className="text-xs font-mono text-indigo-400 font-bold">{wizardCooldown} minutes</span>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <input
                          id="wizard-cooldown-slider"
                          type="range"
                          min="0"
                          max="300"
                          step="5"
                          value={wizardCooldown}
                          onChange={(e) => setWizardCooldown(parseInt(e.target.value))}
                          className="flex-1 accent-indigo-500 bg-zinc-900 h-1.5 rounded-lg appearance-none cursor-pointer"
                        />
                      </div>
                      <span className="block text-[10px] text-zinc-500 mt-1 font-mono leading-relaxed">
                        Cooldown in minutes. If 0, trigger fires every time without cooldown.
                      </span>
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-zinc-400 uppercase tracking-wider mb-2">
                        Expiration Calendar (Optional)
                      </label>
                      <div className="relative">
                        <Calendar size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
                        <input
                          id="wizard-expiration-input"
                          type="datetime-local"
                          value={wizardExpiration}
                          onChange={(e) => setWizardExpiration(e.target.value)}
                          className="w-full h-11 bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 text-xs font-mono text-zinc-200 outline-none focus:border-indigo-500"
                        />
                      </div>
                    </div>

                    {/* Summary Card before confirmation */}
                    <div className="bg-zinc-900/30 border border-zinc-900/80 p-3 rounded-lg space-y-1.5 text-[10px] font-mono text-zinc-400">
                      <span className="block font-bold text-[9px] text-zinc-500 uppercase tracking-wider">ALARM SPECIFICATION SUMMARY:</span>
                      <div>Coin: <span className="text-zinc-200 font-bold">{SUPPORTED_COINS[wizardCoin].name}</span></div>
                      <div>Condition: <span className="text-zinc-200 font-bold">{wizardDirection.toUpperCase()} ${parseFloat(wizardThreshold).toLocaleString()}</span></div>
                      <div>Cooldown: <span className="text-zinc-200 font-bold">{wizardCooldown} minutes</span></div>
                      <div>Expiry: <span className="text-zinc-200 font-bold">{wizardExpiration ? new Date(wizardExpiration).toLocaleString() : 'NEVER'}</span></div>
                    </div>

                    <div className="pt-4 flex justify-between items-center">
                      <button
                        id="wizard-prev-step-3"
                        type="button"
                        onClick={() => setStep(2)}
                        className="text-xs font-mono font-bold text-zinc-500 hover:text-zinc-300"
                      >
                        ← BACK
                      </button>
                      <button
                        id="wizard-submit-btn"
                        type="submit"
                        className="h-10 px-6 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold font-mono rounded-lg transition-colors cursor-pointer flex items-center gap-1.5"
                      >
                        <Check size={14} />
                        INSTANTIATE ALARM
                      </button>
                    </div>
                  </div>
                )}
              </form>
            </div>
          </motion.div>
        </div>
      )}

    </div>
  );
};
