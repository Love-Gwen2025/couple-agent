/**
 * 认证状态管理
 *
 * 管理用户登录状态和 Token
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

/** 认证状态接口 */
interface AuthState {
  /** 当前用户 */
  user: User | null;
  /** 认证 Token */
  token: string | null;
}

/** 认证操作接口 */
interface AuthActions {
  /** 设置用户信息 */
  setUser: (user: User | null) => void;
  /** 设置 Token */
  setToken: (token: string | null) => void;
  /** 登出 */
  logout: () => void;
}

/** 认证 Store */
export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set) => ({
      // 初始状态
      user: null,
      token: null,

      // 操作方法
      setUser: (user) => set({ user }),

      setToken: (token) => {
        // 将 Token 存储到 localStorage，供请求拦截器使用
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
        set({ token });
      },

      logout: () => {
        // 清除 localStorage 中的 Token
        localStorage.removeItem('token');
        set({ user: null, token: null });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    }
  )
);

// 选择器 Hooks
export const useUser = () => useAuthStore((state) => state.user);
export const useToken = () => useAuthStore((state) => state.token);
export const useIsAuthenticated = () => useAuthStore((state) => !!state.token);
