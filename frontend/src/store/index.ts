/**
 * 全局状态管理入口
 *
 * 采用领域分离的 Store 架构，每个 Store 只负责单一领域
 */

// 导出新的拆分 Store
export {
  useAuthStore,
  useUser,
  useToken,
  useIsAuthenticated,
} from './authStore';

export {
  useConversationStore,
  useCurrentConversationId,
  useMessages,
  useStreamingContent,
  useConversationLoading,
} from './conversationStore';

export {
  useModelStore,
  useCurrentModel,
  useModels,
} from './modelStore';

export {
  useAgentStore,
  useAgents,
  useCurrentAgentId,
} from './agentStore';

export {
  useUIStore,
  useTheme,
  useSidebarOpen,
  useSidebarWidth,
  useTextScale,
  initUISettings,
} from './uiStore';

export {
  useNavigationStore,
  useCurrentPage,
  useSelectedKnowledgeBaseId,
  type PageType,
} from './navigationStore';

// 导出迁移工具
export { checkAndMigrate, rollbackMigration } from './migration';

// ============================================================================
// 向后兼容层 - 逐步废弃
// ============================================================================

import { useAuthStore } from './authStore';
import { useConversationStore } from './conversationStore';
import { useModelStore } from './modelStore';
import { useAgentStore } from './agentStore';
import { useUIStore } from './uiStore';
import { useNavigationStore, type PageType } from './navigationStore';
import type { User, Conversation, Message, AiModel } from '../types';
import type { ThemeMode, AccentColor } from '../config/themes';

/** 应用状态接口（向后兼容） */
interface AppState {
  user: User | null;
  token: string | null;
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: Message[];
  currentCheckpointId: string | null;
  models: AiModel[];
  currentModelCode: string | null;
  currentModelId: string | null;
  currentAgentId: string | null;
  sidebarOpen: boolean;
  isLoading: boolean;
  streamingContent: string;
  themeMode: ThemeMode;
  accentColor: AccentColor;
  currentPage: PageType;
  selectedKnowledgeBaseId: string | null;
}

/** 应用操作接口（向后兼容） */
interface AppActions {
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  removeConversation: (id: string) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  setCurrentConversationId: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setModels: (models: AiModel[]) => void;
  setCurrentModelCode: (code: string | null) => void;
  setCurrentModelId: (id: string | null) => void;
  setCurrentAgentId: (id: string | null) => void;
  setCurrentCheckpointId: (checkpointId: string | null) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (chunk: string) => void;
  clearStreamingContent: () => void;
  setThemeMode: (mode: ThemeMode) => void;
  setAccentColor: (color: AccentColor) => void;
  setCurrentPage: (page: PageType) => void;
  setSelectedKnowledgeBaseId: (id: string | null) => void;
  openKnowledgeDetail: (id: string) => void;
  backToKnowledgeList: () => void;
}

/**
 * 兼容层 Hook
 *
 * @deprecated 请使用拆分后的专用 Store：
 * - useAuthStore - 认证状态
 * - useConversationStore - 会话状态
 * - useModelStore - 模型状态
 * - useUIStore - UI 状态
 * - useNavigationStore - 导航状态
 */
export function useAppStore(): AppState & AppActions;
export function useAppStore<T>(selector: (state: AppState & AppActions) => T): T;
export function useAppStore<T>(selector?: (state: AppState & AppActions) => T) {
  // 获取所有 Store 状态
  const authState = useAuthStore();
  const conversationState = useConversationStore();
  const modelState = useModelStore();
  const agentState = useAgentStore();
  const uiState = useUIStore();
  const navigationState = useNavigationStore();

  // 组合成兼容的状态对象
  const combinedState: AppState & AppActions = {
    // AuthStore 状态
    user: authState.user,
    token: authState.token,
    setUser: authState.setUser,
    setToken: authState.setToken,
    logout: () => {
      authState.logout();
      conversationState.clearAll();
    },

    // ConversationStore 状态
    conversations: conversationState.conversations,
    currentConversationId: conversationState.currentConversationId,
    messages: conversationState.messages,
    currentCheckpointId: conversationState.currentCheckpointId,
    streamingContent: conversationState.streamingContent,
    isLoading: conversationState.isLoading,
    setConversations: conversationState.setConversations,
    addConversation: conversationState.addConversation,
    removeConversation: conversationState.removeConversation,
    updateConversation: conversationState.updateConversation,
    setCurrentConversationId: conversationState.setCurrentConversationId,
    setMessages: conversationState.setMessages,
    addMessage: conversationState.addMessage,
    setCurrentCheckpointId: conversationState.setCurrentCheckpointId,
    setIsLoading: conversationState.setIsLoading,
    setStreamingContent: conversationState.setStreamingContent,
    appendStreamingContent: conversationState.appendStreamingContent,
    clearStreamingContent: conversationState.clearStreamingContent,

    // ModelStore 状态
    models: modelState.models,
    currentModelCode: modelState.currentModelCode,
    currentModelId: modelState.currentModelId,
    setModels: modelState.setModels,
    setCurrentModelCode: modelState.setCurrentModelCode,
    setCurrentModelId: modelState.setCurrentModelId,

    // AgentStore 状态
    currentAgentId: agentState.currentAgentId,
    setCurrentAgentId: agentState.setCurrentAgentId,

    // UIStore 状态
    sidebarOpen: uiState.sidebarOpen,
    themeMode: uiState.themeMode,
    accentColor: uiState.accentColor,
    toggleSidebar: uiState.toggleSidebar,
    setSidebarOpen: uiState.setSidebarOpen,
    setThemeMode: uiState.setThemeMode,
    setAccentColor: uiState.setAccentColor,

    // NavigationStore 状态
    currentPage: navigationState.currentPage,
    selectedKnowledgeBaseId: navigationState.selectedKnowledgeBaseId,
    setCurrentPage: navigationState.setCurrentPage,
    setSelectedKnowledgeBaseId: navigationState.setSelectedKnowledgeBaseId,
    openKnowledgeDetail: navigationState.openKnowledgeDetail,
    backToKnowledgeList: navigationState.backToKnowledgeList,
  };

  if (selector) {
    return selector(combinedState);
  }

  return combinedState;
}
