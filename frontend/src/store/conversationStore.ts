/**
 * 会话状态管理
 *
 * 管理会话列表和消息
 */
import { create } from 'zustand';
import type { Conversation, Message } from '../types';

/** 会话状态接口 */
interface ConversationState {
  /** 会话列表 */
  conversations: Conversation[];
  /** 当前选中的会话ID */
  currentConversationId: string | null;
  /** 当前会话的消息列表 */
  messages: Message[];
  /** 当前分支使用的 checkpoint ID */
  currentCheckpointId: string | null;
  /** 流式响应的临时内容 */
  streamingContent: string;
  /** 是否正在加载 */
  isLoading: boolean;
}

/** 会话操作接口 */
interface ConversationActions {
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
  /** 设置当前 checkpoint ID */
  setCurrentCheckpointId: (checkpointId: string | null) => void;
  /** 设置加载状态 */
  setIsLoading: (loading: boolean) => void;
  /** 设置流式内容 */
  setStreamingContent: (content: string) => void;
  /** 追加流式内容 */
  appendStreamingContent: (chunk: string) => void;
  /** 清空流式内容 */
  clearStreamingContent: () => void;
  /** 清空会话数据（登出时使用） */
  clearAll: () => void;
}

/** 会话 Store */
export const useConversationStore = create<ConversationState & ConversationActions>()(
  (set) => ({
    // 初始状态
    conversations: [],
    currentConversationId: null,
    messages: [],
    currentCheckpointId: null,
    streamingContent: '',
    isLoading: false,

    // 会话操作
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
      set({
        currentConversationId: id,
        messages: [],
        streamingContent: '',
        currentCheckpointId: null,
      }),

    // 消息操作
    setMessages: (messages) => set({ messages }),

    addMessage: (message) =>
      set((state) => ({
        messages: [...state.messages, message],
      })),

    setCurrentCheckpointId: (checkpointId) => set({ currentCheckpointId: checkpointId }),

    // 加载状态
    setIsLoading: (loading) => set({ isLoading: loading }),

    // 流式内容操作
    setStreamingContent: (content) => set({ streamingContent: content }),

    appendStreamingContent: (chunk) =>
      set((state) => ({
        streamingContent: state.streamingContent + chunk,
      })),

    clearStreamingContent: () => set({ streamingContent: '' }),

    // 清空所有数据
    clearAll: () =>
      set({
        conversations: [],
        currentConversationId: null,
        messages: [],
        currentCheckpointId: null,
        streamingContent: '',
        isLoading: false,
      }),
  })
);

// 选择器 Hooks
export const useCurrentConversationId = () =>
  useConversationStore((state) => state.currentConversationId);

export const useMessages = () =>
  useConversationStore((state) => state.messages);

export const useStreamingContent = () =>
  useConversationStore((state) => state.streamingContent);

export const useConversationLoading = () =>
  useConversationStore((state) => state.isLoading);
