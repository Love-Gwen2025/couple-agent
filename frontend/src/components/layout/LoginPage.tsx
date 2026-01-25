/**
 * 登录页面组件 - High-End Modern Edition
 *
 * 提供用户登录功能，支持自动注册
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Sparkles, ArrowRight, User, Lock, CheckCircle2, AlertCircle, ArrowLeft } from 'lucide-react';
import { useAuthStore } from '../../store';
import { login, register } from '../../api';
import clsx from 'clsx';

interface LoginPageProps {
  onBack?: () => void;
}

/**
 * 登录页面
 */
export function LoginPage({ onBack }: LoginPageProps) {
  const { setUser, setToken } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  /** 处理登录（登录即注册） */
  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码');
      return;
    }

    setIsLoading(true);
    setError('');

    const params = { userCode: username, userPassword: password };

    try {
      // 1. 先尝试登录
      const token = await login(params);
      setIsSuccess(true);
      setTimeout(() => {
        setToken(token);
        setUser({ id: 0, userCode: username, userName: username });
      }, 1000);
    } catch {
      try {
        // 2. 登录失败，尝试自动注册
        await register(params);
        // 3. 注册成功后重新登录
        const token = await login(params);
        setIsSuccess(true);
        setTimeout(() => {
          setToken(token);
          setUser({ id: 0, userCode: username, userName: username });
        }, 1000);
      } catch {
        setError('登录失败，请检查您的凭据');
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen w-full flex bg-background overflow-hidden selection:bg-primary/30">
      {/* Back Button */}
      {onBack && (
        <button
          onClick={onBack}
          className="absolute top-6 left-6 z-50 p-3 rounded-full bg-surface-container/30 hover:bg-surface-container/50 backdrop-blur-md transition-all duration-300 text-foreground border border-border/10 shadow-lg hover:scale-105 active:scale-95"
          aria-label="Back"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
      )}

      {/* --- 左侧：品牌展示区 (仅桌面端) --- */}
      <div className="hidden lg:flex lg:w-1/2 relative flex-col items-center justify-center p-12 overflow-hidden bg-black">
        {/* 沉浸式背景：沿用欢迎页的氛围 */}
        <div className="absolute inset-0 z-0">
          <img
            src="/src/assets/hero_bg.png"
            alt="Background"
            className="w-full h-full object-cover opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-black via-black/40 to-black/80" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="relative z-10 max-w-md text-center"
        >
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-[32px] bg-white/[0.03] backdrop-blur-2xl border border-white/[0.08] mb-10 shadow-2xl relative group">
            <div className="absolute inset-0 bg-gray-500/20 blur-2xl rounded-full animate-pulse" />
            <Sparkles className="w-12 h-12 text-gray-400 relative z-10" />
          </div>

          <h1 className="text-6xl font-black tracking-[0.2em] mb-8 uppercase italic">
            MY<span className="text-white">AGENT</span>
          </h1>

          <p className="text-lg text-gray-400 font-bold tracking-[0.3em] uppercase leading-relaxed">
            Unlimited Intelligence
            <br />
            <span className="text-xs font-mono text-gray-400/60 tracking-[0.5em]">AI Assistant</span>
          </p>
        </motion.div>

        {/* 底部装饰 */}
        <div className="absolute bottom-12 left-12 right-12 flex justify-between items-center text-[10px] text-gray-500/20 font-bold tracking-[0.4em] uppercase">
          <span>SECURE KERNEL</span>
          <div className="h-px flex-1 mx-6 bg-gray-500/10" />
          <span>EST. 2025</span>
        </div>
      </div>

      {/* --- 右侧：登录区 --- */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 relative bg-[#05050A]">
        {/* 移动端背景点缀 */}
        <div className="lg:hidden absolute inset-0 -z-10">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gray-500/10 blur-[80px]" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-gray-500/10 blur-[80px]" />
        </div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="w-full max-w-[420px]"
        >
          <div className="mb-10 lg:text-left text-center">
            <h2 className="text-4xl font-black tracking-tight text-white mb-3 uppercase italic">欢迎回来</h2>
            <p className="text-gray-400 text-sm font-bold tracking-widest uppercase opacity-60">Sign In</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-center gap-3 text-red-400 text-xs font-bold tracking-widest uppercase overflow-hidden"
                  role="alert"
                  aria-live="assertive"
                >
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            <div className="space-y-4">
              {/* 用户名输入 */}
              <div className="group relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-gray-500 group-focus-within:text-gray-400 transition-colors">
                  <User className="w-5 h-5" />
                </div>
                <input
                  type="text"
                  placeholder="用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading || isSuccess}
                  className={clsx(
                    "w-full pl-12 pr-4 py-4 bg-white/[0.03] border border-white/[0.08] rounded-2xl outline-none transition-all duration-300",
                    "focus:bg-white/[0.05] focus:border-gray-500/50 focus:ring-4 focus:ring-gray-500/10",
                    "placeholder:text-gray-600 text-white font-medium"
                  )}
                />
              </div>

              {/* 密码输入 */}
              <div className="group relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-gray-500 group-focus-within:text-gray-400 transition-colors">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type="password"
                  placeholder="密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading || isSuccess}
                  className={clsx(
                    "w-full pl-12 pr-4 py-4 bg-white/[0.03] border border-white/[0.08] rounded-2xl outline-none transition-all duration-300",
                    "focus:bg-white/[0.05] focus:border-gray-500/50 focus:ring-4 focus:ring-gray-500/10",
                    "placeholder:text-gray-600 text-white font-medium"
                  )}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || isSuccess}
              className={clsx(
                "w-full py-5 rounded-2xl font-black text-white transition-all duration-500 relative overflow-hidden group shadow-2xl uppercase tracking-widest",
                isSuccess ? "bg-green-600" : "bg-gray-900 hover:bg-gray-800 hover:scale-[1.02] active:scale-[0.98]",
                (isLoading || isSuccess) && "cursor-default"
              )}
            >
              <AnimatePresence mode="wait">
                {isLoading ? (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center justify-center gap-2"
                  >
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>AUTHORIZING...</span>
                  </motion.div>
                ) : isSuccess ? (
                  <motion.div
                    key="success"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-center gap-2"
                  >
                    <CheckCircle2 className="w-5 h-5" />
                    <span>GRANTED</span>
                  </motion.div>
                ) : (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center justify-center gap-3"
                  >
                    <span>进入空间</span>
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </motion.div>
                )}
              </AnimatePresence>
            </button>
          </form>

          <div className="mt-12 pt-8 border-t border-white/[0.05]">
            <p className="text-center text-gray-600 text-[10px] font-bold tracking-[0.2em] uppercase">
              Notice: Accounts are auto-initialized on first entry.
            </p>
          </div>
        </motion.div>

        {/* 底部版权 */}
        <div className="absolute bottom-6 left-0 right-0 text-center text-[10px] text-gray-700 uppercase tracking-[0.3em] font-medium">
          &copy; 2025 MYAGENT PROTOCOL. SECURE LINK ACTIVE.
        </div>
      </div>
    </div>
  );
}
