/**
 * API 客户端配置
 *
 * 使用 axios 封装 HTTP 请求，支持拦截器和统一错误处理
 */
import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '../types';
import { useAuthStore, useConversationStore } from '../store';

/** API 基础地址 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api';

/**
 * 处理未授权响应
 *
 * 1. 清理本地 token 与用户信息，避免继续使用失效会话
 * 2. 同步重置 Zustand 持久化存储，避免刷新后仍加载旧 token
 * 3. 跳转到登录页重新获取登录态
 */
export function handleUnauthorized(): void {
  // 清除认证状态
  useAuthStore.getState().logout();
  // 清除会话数据
  useConversationStore.getState().clearAll();
  window.location.href = '/login';
}

/** 创建 axios 实例 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // 重要：允许发送 Cookie（包括 HttpOnly Cookie）
});

/**
 * 请求拦截器
 *
 * 安全改进：
 * - HttpOnly Cookie 会自动发送，无需手动设置
 * - 保留 localStorage 检查作为备用（向后兼容）
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 检查是否有旧的 localStorage token（向后兼容）
    const legacyToken = localStorage.getItem('token');
    if (legacyToken && config.headers) {
      // 如果存在旧 token，通过 header 发送（兼容模式）
      config.headers.token = legacyToken;
    }
    // 注意：HttpOnly Cookie 会由浏览器自动发送，无需手动处理
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 *
 * 统一处理响应和错误
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError<ApiResponse<unknown>>) => {
    // 处理 401 未授权
    if (error.response?.status === 401) {
      handleUnauthorized();
    }
    return Promise.reject(error);
  }
);

export default apiClient;
export { API_BASE_URL };
