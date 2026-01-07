/**
 * UI 状态管理
 *
 * 管理界面显示状态和主题设置
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThemeMode, AccentColor } from '../config/themes';

/** UI 状态接口 */
interface UIState {
  /** 侧边栏是否展开 */
  sidebarOpen: boolean;
  /** 主题模式 (亮色/暗色/跟随系统) */
  themeMode: ThemeMode;
  /** 强调色主题 */
  accentColor: AccentColor;
}

/** UI 操作接口 */
interface UIActions {
  /** 切换侧边栏 */
  toggleSidebar: () => void;
  /** 设置侧边栏状态 */
  setSidebarOpen: (open: boolean) => void;
  /** 设置主题模式 */
  setThemeMode: (mode: ThemeMode) => void;
  /** 设置强调色 */
  setAccentColor: (color: AccentColor) => void;
}

/** UI Store */
export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set) => ({
      // 初始状态
      sidebarOpen: true,
      themeMode: 'system',
      accentColor: 'blue',

      // 操作方法
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setThemeMode: (mode) => set({ themeMode: mode }),
      setAccentColor: (color) => set({ accentColor: color }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        themeMode: state.themeMode,
        accentColor: state.accentColor,
      }),
    }
  )
);

// 选择器 Hooks
export const useTheme = () =>
  useUIStore((state) => ({
    mode: state.themeMode,
    accent: state.accentColor,
  }));

export const useSidebarOpen = () => useUIStore((state) => state.sidebarOpen);
