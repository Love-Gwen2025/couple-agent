/**
 * 应用根组件
 *
 * 包含认证状态检查和主题初始化
 */
import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'framer-motion';
import { useAuthStore, useUIStore, initUISettings } from './store';
import { MainLayout, LoginPage, WelcomePage } from './components/layout';

/** React Query 客户端 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

/**
 * 应用入口组件
 */
function AppContent() {
  // 认证状态
  const { token } = useAuthStore();

  // UI 状态
  const { themeMode, accentColor, themeSkin } = useUIStore();

  const [view, setView] = useState<'welcome' | 'login'>('welcome');

  /**
   * 应用启动时初始化 UI 设置
   * 将持久化的设置同步到 CSS 变量
   */
  useEffect(() => {
    initUISettings();
  }, []);

  /**
   * 主题初始化效果
   * 根据 store 中的主题设置，更新 document 上的 data 属性
   */
  useEffect(() => {
    const root = document.documentElement;

    // 设置强调色
    root.setAttribute('data-accent', accentColor);

    // 设置主题皮肤
    if (themeSkin !== 'default') {
      root.setAttribute('data-theme-skin', themeSkin);
    } else {
      root.removeAttribute('data-theme-skin');
    }

    // 设置明暗模式
    if (themeMode === 'system') {
      // 跟随系统偏好
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const updateSystemTheme = () => {
        root.setAttribute('data-theme', mediaQuery.matches ? 'dark' : 'light');
      };

      // 初始设置
      updateSystemTheme();

      // 监听系统偏好变化
      mediaQuery.addEventListener('change', updateSystemTheme);
      return () => mediaQuery.removeEventListener('change', updateSystemTheme);
    } else {
      // 手动设置
      root.setAttribute('data-theme', themeMode);
    }
  }, [themeMode, accentColor, themeSkin]);

  // 未登录显示欢迎页或登录页
  if (!token) {
    if (view === 'welcome') {
      return <WelcomePage onSignIn={() => setView('login')} onSignUp={() => setView('login')} />;
    }
    return <LoginPage onBack={() => setView('welcome')} />;
  }

  // 已登录显示主界面
  return <MainLayout />;
}

/**
 * 应用根组件
 * 包含 React Query 和 Framer Motion 配置
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user">
        <AppContent />
      </MotionConfig>
    </QueryClientProvider>
  );
}

export default App;

