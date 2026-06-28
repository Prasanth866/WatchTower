import React, { useState } from 'react';
import { api } from '../api';
import { UserProfile } from '../types';
import { useToast } from './ToastProvider';
import { Shield, Lock, Mail, User, Eye, EyeOff, Check, X, ArrowRight } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface AuthLayoutProps {
  onAuthSuccess: (user: UserProfile) => void;
}

type AuthScreen = 'login' | 'register' | 'forgot' | 'reset';

export const AuthLayout: React.FC<AuthLayoutProps> = ({ onAuthSuccess }) => {
  const [screen, setScreen] = useState<AuthScreen>('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { addToast } = useToast();

  // Real-time password validation state
  const isLengthValid = password.length >= 8 && password.length <= 72;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);
  const doPasswordsMatch = screen === 'register' ? password === confirmPassword && password !== '' : true;

  const isRegisterFormValid = 
    username.trim().length > 0 &&
    email.includes('@') &&
    isLengthValid &&
    hasUpper &&
    hasLower &&
    hasNumber &&
    hasSpecial &&
    doPasswordsMatch;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      addToast('error', 'Login Failed', 'Please fill in all fields.');
      return;
    }

    setIsLoading(true);
    try {
      // Form encoding application/x-www-form-urlencoded
      const formParams = new URLSearchParams();
      formParams.append('username', username.trim());
      formParams.append('password', password);

      const res = await api.login(formParams);
      const user = await api.getCurrentUser();
      
      if (user) {
        addToast('success', 'Welcome Back', `Access granted. Authenticated as ${user.email}.`);
        onAuthSuccess(user);
      } else {
        throw new Error('Authentication state corrupt.');
      }
    } catch (err: any) {
      addToast('error', 'Authentication Failed', err.message || 'Invalid credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isRegisterFormValid) {
      addToast('error', 'Validation Error', 'Please satisfy all security password requirements.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await api.register({
        username: username.trim(),
        email: email.trim(),
        password,
      });
      addToast('success', 'Registration Successful', `Welcome to WatchTower, ${user.email}!`);
      onAuthSuccess(user);
    } catch (err: any) {
      addToast('error', 'Registration Failed', err.message || 'Try a different username/email.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim().includes('@')) {
      addToast('error', 'Validation Error', 'Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await api.forgotPassword(email);
      addToast('success', 'Token Dispatched', res.message);
      // Move to reset
      setScreen('reset');
    } catch (err: any) {
      addToast('error', 'Dispatch Failed', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetToken.trim()) {
      addToast('error', 'Error', 'Please provide your reset token.');
      return;
    }
    if (!isLengthValid) {
      addToast('error', 'Validation Error', 'Password must be 8-72 characters.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await api.resetPassword(resetToken, password);
      addToast('success', 'Password Updated', res.message);
      setScreen('login');
      // Clear password states
      setPassword('');
      setConfirmPassword('');
      setResetToken('');
    } catch (err: any) {
      addToast('error', 'Reset Failed', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div id="auth-container" className="min-h-screen bg-[#06080F] flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Visual background ambient grids/glows */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-96 h-96 bg-emerald-500/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0F172A_1px,transparent_1px),linear-gradient(to_bottom,#0F172A_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30 pointer-events-none" />

      {/* Main Box wrapper */}
      <div className="w-full max-w-md z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 shadow-[0_0_15px_rgba(99,102,241,0.15)] text-indigo-400">
              <Shield size={28} />
            </div>
            <span className="text-2xl font-extrabold tracking-tight text-white font-sans flex items-center">
              WATCH<span className="text-indigo-400">TOWER</span>
            </span>
          </div>
          <span className="text-xs text-zinc-500 tracking-wider font-mono font-bold uppercase">
            REAL-TIME INTEL & TRADE DESK
          </span>
        </div>

        <motion.div
          layout
          className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-8 backdrop-blur-md shadow-[0_20px_50px_-12px_rgba(0,0,0,0.5)]"
        >
          <AnimatePresence mode="wait">
            {screen === 'login' && (
              <motion.div
                key="login"
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 15 }}
                transition={{ duration: 0.2 }}
              >
                <h3 className="text-lg font-bold text-zinc-100 tracking-tight mb-1">TERMINAL INGRESS</h3>
                <p className="text-xs text-zinc-500 mb-6 font-mono">AUTHORIZED PERSONNEL ONLY. INPUT CREDENTIALS.</p>

                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Username / Email
                    </label>
                    <div className="relative">
                      <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="login-username"
                        type="text"
                        required
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="e.g. admin or operator@watchtower.io"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
                        Secure Password
                      </label>
                      <button
                        id="go-forgot-btn"
                        type="button"
                        onClick={() => setScreen('forgot')}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 font-mono"
                      >
                        RECOVER TOKEN?
                      </button>
                    </div>
                    <div className="relative">
                      <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-10 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                      <button
                        id="toggle-login-pwd"
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  <button
                    id="submit-login-btn"
                    type="submit"
                    disabled={isLoading}
                    className="w-full h-11 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:text-zinc-400 text-white font-bold text-sm rounded-lg flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-lg shadow-indigo-600/15"
                  >
                    {isLoading ? 'ESTABLISHING INGRESS...' : 'EXECUTE ACCESS'}
                    <ArrowRight size={16} />
                  </button>
                </form>

                <div className="mt-6 text-center border-t border-zinc-900 pt-5">
                  <span className="text-xs text-zinc-500">
                    New operator?{' '}
                    <button
                      id="switch-to-register"
                      onClick={() => {
                        setScreen('register');
                        setPassword('');
                      }}
                      className="text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer"
                    >
                      Provision Account
                    </button>
                  </span>
                </div>
              </motion.div>
            )}

            {screen === 'register' && (
              <motion.div
                key="register"
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 15 }}
                transition={{ duration: 0.2 }}
              >
                <h3 className="text-lg font-bold text-zinc-100 tracking-tight mb-1">PROVISION OPERATOR</h3>
                <p className="text-xs text-zinc-500 mb-6 font-mono">COMPLETE ENROLLMENT CRITERIA.</p>

                <form onSubmit={handleRegister} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Username
                    </label>
                    <div className="relative">
                      <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="register-username"
                        type="text"
                        required
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="operator1"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="register-email"
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="operator@watchtower.io"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Set Password
                    </label>
                    <div className="relative">
                      <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="register-password"
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-10 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                      <button
                        id="toggle-register-pwd"
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>

                    {/* Password requirements visual grid */}
                    <div className="mt-3 p-3 bg-zinc-900/40 rounded-lg border border-zinc-800/50 space-y-2">
                      <span className="block text-[10px] font-mono text-zinc-500 uppercase tracking-wide">
                        Security Requirements:
                      </span>
                      <div className="grid grid-cols-2 gap-x-2 gap-y-1.5">
                        <div className="flex items-center gap-1.5 text-[10px] font-mono">
                          {isLengthValid ? <Check size={10} className="text-emerald-400" /> : <X size={10} className="text-zinc-600" />}
                          <span className={isLengthValid ? 'text-zinc-300' : 'text-zinc-500'}>8–72 Chars</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] font-mono">
                          {hasUpper ? <Check size={10} className="text-emerald-400" /> : <X size={10} className="text-zinc-600" />}
                          <span className={hasUpper ? 'text-zinc-300' : 'text-zinc-500'}>Uppercase [A-Z]</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] font-mono">
                          {hasLower ? <Check size={10} className="text-emerald-400" /> : <X size={10} className="text-zinc-600" />}
                          <span className={hasLower ? 'text-zinc-300' : 'text-zinc-500'}>Lowercase [a-z]</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] font-mono">
                          {hasNumber ? <Check size={10} className="text-emerald-400" /> : <X size={10} className="text-zinc-600" />}
                          <span className={hasNumber ? 'text-zinc-300' : 'text-zinc-500'}>Numeric [0-9]</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[10px] font-mono col-span-2 border-t border-zinc-900/80 pt-1.5 mt-1">
                          {hasSpecial ? <Check size={10} className="text-emerald-400" /> : <X size={10} className="text-zinc-600" />}
                          <span className={hasSpecial ? 'text-zinc-300' : 'text-zinc-500'}>Special Char (!@#$%^&*)</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Confirm Password
                    </label>
                    <div className="relative">
                      <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="register-confirm-password"
                        type="password"
                        required
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                    {password && confirmPassword && (
                      <span className={`block text-[10px] font-mono mt-1.5 ${doPasswordsMatch ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {doPasswordsMatch ? '✓ Passwords match' : '✗ Passwords do not match'}
                      </span>
                    )}
                  </div>

                  <button
                    id="submit-register-btn"
                    type="submit"
                    disabled={isLoading || !isRegisterFormValid}
                    className="w-full h-11 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900/40 disabled:text-zinc-600 text-white font-bold text-sm rounded-lg flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-lg shadow-emerald-600/10"
                  >
                    {isLoading ? 'ENROLLING PROTOCOL...' : 'CONFIRM ENROLLMENT'}
                  </button>
                </form>

                <div className="mt-6 text-center border-t border-zinc-900 pt-5">
                  <span className="text-xs text-zinc-500">
                    Already a member?{' '}
                    <button
                      id="switch-to-login"
                      onClick={() => setScreen('login')}
                      className="text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer"
                    >
                      Login here
                    </button>
                  </span>
                </div>
              </motion.div>
            )}

            {screen === 'forgot' && (
              <motion.div
                key="forgot"
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 15 }}
                transition={{ duration: 0.2 }}
              >
                <h3 className="text-lg font-bold text-zinc-100 tracking-tight mb-1">RECOVER SECURITY TOKEN</h3>
                <p className="text-xs text-zinc-500 mb-6 font-mono">PROVIDE YOUR REGISTERED EMAIL ADDRESS.</p>

                <form onSubmit={handleForgot} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="forgot-email"
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="operator@watchtower.io"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                  </div>

                  <button
                    id="submit-forgot-btn"
                    type="submit"
                    disabled={isLoading}
                    className="w-full h-11 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-bold text-sm rounded-lg flex items-center justify-center gap-2 cursor-pointer transition-colors"
                  >
                    {isLoading ? 'DISPATCHING TOKEN...' : 'REQUEST DISPATCH'}
                  </button>
                </form>

                <div className="mt-6 text-center border-t border-zinc-900 pt-5">
                  <button
                    id="forgot-back-btn"
                    onClick={() => setScreen('login')}
                    className="text-xs text-zinc-400 hover:text-zinc-200 font-medium font-mono"
                  >
                    ← BACK TO LOGIN
                  </button>
                </div>
              </motion.div>
            )}

            {screen === 'reset' && (
              <motion.div
                key="reset"
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 15 }}
                transition={{ duration: 0.2 }}
              >
                <h3 className="text-lg font-bold text-zinc-100 tracking-tight mb-1">RESET CREDENTIALS</h3>
                <p className="text-xs text-zinc-500 mb-6 font-mono">INPUT DISPATCH TOKEN AND NEW SECURITY KEY.</p>

                <form onSubmit={handleReset} className="space-y-4">
                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      Dispatch Token
                    </label>
                    <div className="relative">
                      <Shield size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="reset-token"
                        type="text"
                        required
                        value={resetToken}
                        onChange={(e) => setResetToken(e.target.value)}
                        placeholder="Input any token received"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-mono text-zinc-400 uppercase tracking-wider mb-1.5">
                      New Password
                    </label>
                    <div className="relative">
                      <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                      <input
                        id="reset-password"
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full h-11 bg-zinc-900/60 border border-zinc-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-lg pl-10 pr-4 text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-all"
                      />
                    </div>
                    <div className="mt-2 text-[10px] font-mono text-zinc-500">
                      Requirement: 8-72 characters.
                    </div>
                  </div>

                  <button
                    id="submit-reset-btn"
                    type="submit"
                    disabled={isLoading}
                    className="w-full h-11 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-850 text-white font-bold text-sm rounded-lg flex items-center justify-center gap-2 cursor-pointer transition-colors"
                  >
                    {isLoading ? 'RESETTING CREDENTIALS...' : 'CONFIRM RESET'}
                  </button>
                </form>

                <div className="mt-6 text-center border-t border-zinc-900 pt-5">
                  <button
                    id="reset-back-btn"
                    onClick={() => setScreen('login')}
                    className="text-xs text-zinc-400 hover:text-zinc-200 font-medium font-mono"
                  >
                    ← BACK TO LOGIN
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
};
