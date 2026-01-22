/**
 * UI 状态管理
 *
 * 管理界面显示状态和主题设置
 * 支持 Open WebUI 风格的侧边栏宽度调整和 UI 缩放
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ThemeMode, AccentColor } from '../config/themes';

/** 主题皮肤类型 */
export type ThemeSkin = 'default' | 'rosepine' | 'rosepine-dawn';

/** 侧边栏宽度范围 */
export const SIDEBAR_WIDTH_MIN = 220;
export const SIDEBAR_WIDTH_MAX = 480;
export const SIDEBAR_WIDTH_DEFAULT = 260;
export const SIDEBAR_COLLAPSED_WIDTH = 49;

/** UI 缩放范围 */
export const TEXT_SCALE_MIN = 0.8;
export const TEXT_SCALE_MAX = 1.2;
export const TEXT_SCALE_DEFAULT = 1;

/** UI 状态接口 */
interface UIState {
  /** 侧边栏是否展开 */
  sidebarOpen: boolean;
  /** 侧边栏宽度 (px) */
  sidebarWidth: number;
  /** 主题模式 (亮色/暗色/跟随系统) */
  themeMode: ThemeMode;
  /** 强调色主题 */
  accentColor: AccentColor;
  /** 主题皮肤 */
  themeSkin: ThemeSkin;
  /** UI 文字缩放比例 (0.8 - 1.2) */
  textScale: number;
}

/** UI 操作接口 */
interface UIActions {
  /** 切换侧边栏 */
  toggleSidebar: () => void;
  /** 设置侧边栏状态 */
  setSidebarOpen: (open: boolean) => void;
  /** 设置侧边栏宽度 */
  setSidebarWidth: (width: number) => void;
  /** 设置主题模式 */
  setThemeMode: (mode: ThemeMode) => void;
  /** 设置强调色 */
  setAccentColor: (color: AccentColor) => void;
  /** 设置主题皮肤 */
  setThemeSkin: (skin: ThemeSkin) => void;
  /** 设置 UI 缩放 */
  setTextScale: (scale: number) => void;
}

/** UI Store */
export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set) => ({
      // 初始状态
      sidebarOpen: true,
      sidebarWidth: SIDEBAR_WIDTH_DEFAULT,
      themeMode: 'system',
      accentColor: 'blue',
      themeSkin: 'default',
      textScale: TEXT_SCALE_DEFAULT,

      // 操作方法
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setSidebarWidth: (width) => {
        /*
         * 限制侧边栏宽度在有效范围内
         */
        const clampedWidth = Math.max(SIDEBAR_WIDTH_MIN, Math.min(SIDEBAR_WIDTH_MAX, width));
        set({ sidebarWidth: clampedWidth });
        /*
         * 同步更新 CSS 变量，确保布局即时响应
         */
        document.documentElement.style.setProperty('--sidebar-width', `${clampedWidth}px`);
      },
      setThemeMode: (mode) => set({ themeMode: mode }),
      setAccentColor: (color) => set({ accentColor: color }),
      setThemeSkin: (skin) => {
        set({ themeSkin: skin });
        /*
         * 设置主题皮肤的 data 属性，供 CSS 选择器使用
         */
        document.documentElement.setAttribute('data-theme-skin', skin);
      },
      setTextScale: (scale) => {
        /*
         * 限制缩放比例在有效范围内
         */
        const clampedScale = Math.max(TEXT_SCALE_MIN, Math.min(TEXT_SCALE_MAX, scale));
        set({ textScale: clampedScale });
        /*
         * 同步更新 CSS 变量，实现全局字体缩放
         */
        document.documentElement.style.setProperty('--app-text-scale', String(clampedScale));
      },
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        themeMode: state.themeMode,
        accentColor: state.accentColor,
        themeSkin: state.themeSkin,
        sidebarWidth: state.sidebarWidth,
        textScale: state.textScale,
      }),
    }
  )
);

// 选择器 Hooks
export const useTheme = () =>
  useUIStore((state) => ({
    mode: state.themeMode,
    accent: state.accentColor,
    skin: state.themeSkin,
  }));

export const useSidebarOpen = () => useUIStore((state) => state.sidebarOpen);

export const useSidebarWidth = () => useUIStore((state) => state.sidebarWidth);

export const useTextScale = () => useUIStore((state) => state.textScale);

/**
 * 初始化 UI 设置
 * 在应用启动时调用，将持久化的设置同步到 CSS 变量
 */
export const initUISettings = () => {
  const state = useUIStore.getState();
  /*
   * 恢复侧边栏宽度
   */
  document.documentElement.style.setProperty('--sidebar-width', `${state.sidebarWidth}px`);
  /*
   * 恢复 UI 缩放
   */
  document.documentElement.style.setProperty('--app-text-scale', String(state.textScale));
  /*
   * 恢复主题皮肤
   */
  if (state.themeSkin !== 'default') {
    document.documentElement.setAttribute('data-theme-skin', state.themeSkin);
  }
};
