/**
 * 欢迎落地页组件 - 沉浸式暗核风格 (Inspired by reference)
 */
import { motion } from 'framer-motion';
import heroBg from '../../assets/hero_bg.png';

interface WelcomePageProps {
  onSignIn: () => void;
  onSignUp: () => void;
}

export function WelcomePage({ onSignIn, onSignUp }: WelcomePageProps) {
  return (
    <div className="min-h-screen w-full bg-[#000000] relative overflow-hidden font-sans selection:bg-purple-500/30 text-white">

      {/* --- 全屏背景层 --- */}
      <div className="absolute inset-0 z-0">
        <img
          src={heroBg}
          alt="Background"
          className="w-full h-full object-cover opacity-60"
        />
        {/* 暗色渐变遮罩，增强文字对比度 */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-black/80" />
      </div>

      {/* --- 顶部导航栏 --- */}
      <nav className="relative z-20 w-full max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-black tracking-[0.2em] uppercase">
            MY<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">AGENT</span>
          </span>
        </div>

        <div className="hidden md:flex items-center gap-8 text-sm font-bold tracking-widest uppercase text-gray-300">
          <a href="#" className="hover:text-purple-400 transition-colors">首页</a>
          <a href="#" className="hover:text-purple-400 transition-colors">新功能</a>
          <a href="#" className="hover:text-purple-400 transition-colors">代理索引</a>
          <a href="#" className="hover:text-purple-400 transition-colors">交流区</a>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onSignIn}
            className="px-4 py-2 text-sm font-bold tracking-wider hover:text-purple-400 transition-colors"
          >
            登录
          </button>
        </div>
      </nav>

      {/* --- 主英雄区 (居中) --- */}
      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-80px)] px-6 pb-20 text-center">

        {/* 主标题 */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="mb-6"
        >
          <h1 className="text-6xl md:text-9xl font-black tracking-tighter uppercase leading-tight">
            UNLIMITED <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-500 via-purple-400 to-pink-500">AGENTS</span>
          </h1>
        </motion.div>

        {/* 描述文案 */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.8 }}
          className="max-w-3xl text-lg md:text-xl text-gray-400 font-medium tracking-widest leading-relaxed mb-12"
        >
          沉浸式智能体管理体验 | 私有文档增强 | 极速响应响应处理
        </motion.p>

        {/* 动作按钮 (紫色渐变) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.5 }}
        >
          <button
            onClick={onSignUp}
            className="group relative px-12 py-5 bg-gradient-to-r from-purple-600 to-pink-500 rounded-full font-black text-lg shadow-[0_10px_40px_-10px_rgba(168,85,247,0.5)] hover:shadow-[0_15px_60px_-10px_rgba(168,85,247,0.7)] hover:scale-105 active:scale-95 transition-all duration-300"
          >
            <span className="relative z-10 flex items-center gap-3">
              立即开始
              <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
            </span>
          </button>
        </motion.div>

      </main>

      {/* --- 装饰性细节 --- */}
      <div className="absolute bottom-10 left-10 pointer-events-none opacity-20">
        <div className="text-[10px] tracking-[0.5em] uppercase font-mono">MyAgent Protocol v2.5.0</div>
      </div>
    </div>
  );
}