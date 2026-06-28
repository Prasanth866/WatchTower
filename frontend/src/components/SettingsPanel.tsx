import React, { useState } from 'react';
import { api } from '../api';
import { UserProfile } from '../types';
import { useToast } from './ToastProvider';
import { User, Mail, ShieldAlert, ToggleLeft, ToggleRight, Calendar, Lock, Terminal } from 'lucide-react';
import { motion } from 'motion/react';

interface SettingsPanelProps {
  user: UserProfile;
  onUpdateUser: (user: UserProfile) => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ user, onUpdateUser }) => {
  const [emailNotifications, setEmailNotifications] = useState(user.emailNotifications);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();

  const handleToggleNotifications = async () => {
    const nextVal = !emailNotifications;
    setEmailNotifications(nextVal);
    setIsLoading(true);

    try {
      const updatedUser = await api.updateNotificationPreferences(nextVal);
      onUpdateUser(updatedUser);
      addToast(
        'success',
        'Preferences Updated',
        `Email notifications are now ${nextVal ? 'ENABLED' : 'DISABLED'} instantly in the registry.`
      );
    } catch {
      // Revert if failed
      setEmailNotifications(!nextVal);
      addToast('error', 'Update Failed', 'Failed to save notifications preferences.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="settings-panel-container" className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
      
      {/* Profile Metrics Card (Left- col-span-5) */}
      <div className="md:col-span-5 bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col gap-5">
        <div className="flex items-center gap-3 pb-3 border-b border-zinc-900">
          <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg">
            <User size={18} />
          </div>
          <div>
            <span className="block text-xs font-bold font-mono text-zinc-400 tracking-wider">OPERATOR SECURITY CARD</span>
            <span className="text-sm font-black font-mono text-zinc-100">{user.email}</span>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-zinc-900/30 border border-zinc-900 p-4 rounded-xl space-y-1.5 font-mono text-xs">
            <div className="flex justify-between">
              <span className="text-zinc-500">USER ID:</span>
              <span className="text-zinc-300 font-bold select-all">{user.id}</span>
            </div>
            <div className="flex justify-between border-t border-zinc-900/60 pt-2 mt-2">
              <span className="text-zinc-500">ROUTER IP:</span>
              <span className="text-zinc-400">127.0.0.1</span>
            </div>
            <div className="flex justify-between border-t border-zinc-900/60 pt-2 mt-2">
              <span className="text-zinc-500">AUTH SCOPE:</span>
              <span className="text-indigo-400 font-bold">OPERATOR_ADMIN</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-zinc-400 px-1">
            <Mail size={14} className="text-zinc-500" />
            <div className="flex-1 min-w-0">
              <span className="block text-[9px] text-zinc-500 leading-none mb-1">REGISTERED EMAIL</span>
              <span className="block text-zinc-300 font-medium truncate">{user.email}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-zinc-400 px-1">
            <Calendar size={14} className="text-zinc-500" />
            <div className="flex-1 min-w-0">
              <span className="block text-[9px] text-zinc-500 leading-none mb-1">PROVISION DATE</span>
              <span className="block text-zinc-300 font-medium">
                {new Date(user.created_at).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Preferences Settings (Right- col-span-7) */}
      <div className="md:col-span-7 bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col gap-5">
        <div className="flex justify-between items-center pb-3 border-b border-zinc-900">
          <span className="text-xs font-bold font-mono text-zinc-300 uppercase tracking-wider">SYSTEM CONFIGURATIONS</span>
          <Terminal size={14} className="text-zinc-500" />
        </div>

        <div className="space-y-6">
          
          {/* Email Notifications Toggle Switch Card */}
          <div className="flex items-start justify-between p-4 bg-zinc-900/20 border border-zinc-900 rounded-xl gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-1.5">
                <ShieldAlert size={14} className="text-indigo-400" />
                <span className="text-xs font-bold text-zinc-200 font-mono uppercase tracking-wider">DISPATCH EMAIL NOTIFICATIONS</span>
              </div>
              <p className="text-[11px] text-zinc-500 mt-1.5 leading-relaxed font-sans">
                Instantly routes system-critical warnings, WebSocket alert crosses, and clearing desk receipts directly to your registered mailbox.
              </p>
            </div>

            <button
              id="notifications-toggle-btn"
              onClick={handleToggleNotifications}
              disabled={isLoading}
              className="p-1 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
            >
              {emailNotifications ? (
                <ToggleRight size={38} className="text-indigo-400" />
              ) : (
                <ToggleLeft size={38} className="text-zinc-600" />
              )}
            </button>
          </div>

          {/* Secure Environment Note */}
          <div className="p-4 bg-zinc-950 border border-zinc-900 rounded-xl space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 font-semibold uppercase">
              <Lock size={12} className="text-indigo-400" />
              <span>TERMINAL SECURITY BOUNDARY</span>
            </div>
            <p className="text-[10px] text-zinc-600 leading-relaxed">
              Sessions expire upon logout. Cleans and wipes browser-side memory state immediately. API endpoints utilize cached values to preserve network volume limits.
            </p>
          </div>

        </div>
      </div>

    </div>
  );
};
