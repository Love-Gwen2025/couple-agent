/**
 * 全局状态管理
 *
 * 使用 Zustand 管理应用状态
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Conversation, Message, AiModel } from '../types';
import type { ThemeMode, AccentColor } from '../config/themes';

/** 应用状态接口 */
interface AppState {
  /** 当前用户 */
  user: User | null;
  /** 认证 Token */
  token: string | null;
  /** 会话列表 */
  conversations: Conversation[];
  /** 当前选中的会话ID */
  currentConversationId: string | null;
  /** 当前会话的消息列表 */
  messages: Message[];
  /** 当前分支使用的 checkpoint ID */
  currentCheckpointId: string | null;
  /** 可用的 AI 模型列表 */
  models: AiModel[];
  /** 当前选中的模型编码 */
  currentModelCode: string | null;
  /** 当前选中的用户模型 ID（系统默认模型为 null） */
  currentModelId: string | null;
  /** 侧边栏是否展开 */
  sidebarOpen: boolean;
  /** 是否正在加载 */
  isLoading: boolean;
  /** 流式响应的临时内容 */
  streamingContent: string;
  /** 主题模式 (亮色/暗色/跟随系统) */
  themeMode: ThemeMode;
  /** 强调色主题 */
  accentColor: AccentColor;
  /** 当前页面 */
  currentPage: 'chat' | 'model-settings' | 'knowledge' | 'knowledge-detail';
  /** 选中的知识库ID（用于详情页） */
  selectedKnowledgeBaseId: string | null;
}

/** 应用操作接口 */
interface AppActions {
  /** 设置用户信息 */
  setUser: (user: User | null) => void;
  /** 设置 Token */
  setToken: (token: string | null) => void;
  /** 登出 */
  logout: () => void;
  /** 设置会话列表 */
  setConversations: (conversations: Conversation[]) => void;
  /** 添加新会话 */
  addConversation: (conversation: Conversation) => void;
  /** 删除会话 */
  removeConversation: (id: string) => void;
  /** 更新会话信息 */
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  /** 设置当前会话 */
  setCurrentConversationId: (id: string | null) => void;
  /** 设置消息列表 */
  setMessages: (messages: Message[]) => void;
  /** 添加消息 */
  addMessage: (message: Message) => void;
  /** 设置模型列表 */
  setModels: (models: AiModel[]) => void;
  /** 设置当前模型 */
  setCurrentModelCode: (code: string | null) => void;
  /** 设置当前用户模型 ID */
  setCurrentModelId: (id: string | null) => void;
  /** 设置当前 checkpoint ID */
  setCurrentCheckpointId: (checkpointId: string | null) => void;
  /** 切换侧边栏 */
  toggleSidebar: () => void;
  /** 设置加载状态 */
  setIsLoading: (loading: boolean) => void;
  /** 设置流式内容 */
  setStreamingContent: (content: string) => void;
  /** 追加流式内容 */
  appendStreamingContent: (chunk: string) => void;
  /** 清空流式内容 */
  clearStreamingContent: () => void;
  /** 设置主题模式 */
  setThemeMode: (mode: ThemeMode) => void;
  /** 设置强调色 */
  setAccentColor: (color: AccentColor) => void;
  /** 设置当前页面 */
  setCurrentPage: (page: 'chat' | 'model-settings' | 'knowledge' | 'knowledge-detail') => void;
  /** 设置选中的知识库ID */
  setSelectedKnowledgeBaseId: (id: string | null) => void;
  /** 进入知识库详情页 */
  openKnowledgeDetail: (id: string) => void;
}

/** 应用 Store */
export const useAppStore = create<AppState & AppActions>()(
  persist(
    (set) => ({
      // 初始状态
      user: null,
      token: null,
      conversations: [],
      currentConversationId: null,
      messages: [],
      currentCheckpointId: null,
      models: [],
      currentModelCode: null,
      currentModelId: null,
      sidebarOpen: true,
      isLoading: false,
      streamingContent: '',
      themeMode: 'system',
      accentColor: 'blue',
      currentPage: 'chat',
      selectedKnowledgeBaseId: null,

      // 用户相关操作
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
        set({
          user: null,
          token: null,
          conversations: [],
          currentConversationId: null,
          messages: [],
          currentCheckpointId: null,
        });
      },

      // 会话相关操作
      setConversations: (conversations) => set({ conversations }),
      addConversation: (conversation) =>
        set((state) => ({
          conversations: [conversation, ...state.conversations],
        })),
      removeConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
          currentConversationId:
            state.currentConversationId === id
              ? null
              : state.currentConversationId,
        })),
      updateConversation: (id, updates) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, ...updates } : c
          ),
        })),
      setCurrentConversationId: (id) =>
        set({ currentConversationId: id, messages: [], streamingContent: '', currentCheckpointId: null }),

      // 消息相关操作
      setMessages: (messages) => set({ messages }),
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      // 模型相关操作
      setModels: (models) => set({ models }),
      setCurrentModelCode: (code) => set({ currentModelCode: code }),
      setCurrentModelId: (id) => set({ currentModelId: id }),
      setCurrentCheckpointId: (checkpointId) => set({ currentCheckpointId: checkpointId }),

      // UI 相关操作
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setIsLoading: (loading) => set({ isLoading: loading }),

      // 流式内容操作
      setStreamingContent: (content) => set({ streamingContent: content }),
      appendStreamingContent: (chunk) =>
        set((state) => ({
          streamingContent: state.streamingContent + chunk,
        })),
      clearStreamingContent: () => set({ streamingContent: '' }),

      // 主题相关操作
      setThemeMode: (mode) => set({ themeMode: mode }),
      setAccentColor: (color) => set({ accentColor: color }),
      // 页面导航
      setCurrentPage: (page) => set({ currentPage: page }),
      setSelectedKnowledgeBaseId: (id) => set({ selectedKnowledgeBaseId: id }),
      openKnowledgeDetail: (id) => set({ currentPage: 'knowledge-detail', selectedKnowledgeBaseId: id }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        currentModelCode: state.currentModelCode,
        currentModelId: state.currentModelId,
        themeMode: state.themeMode,
        accentColor: state.accentColor,
      }),
    }
  )
);
