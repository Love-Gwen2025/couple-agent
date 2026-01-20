import apiClient from './client';
import type {
  ApiResponse,
  Conversation,
  CreateConversationParams,
  Message,
  PageResponse,
} from '../types';

/**
 * 获取会话列表（分页）
 *
 * @param page 页码（从1开始）
 * @param size 每页数量
 * @returns 会话列表和是否有更多
 */
export async function getConversations(
  page: number = 1,
  size: number = 20
): Promise<{ items: Conversation[]; hasMore: boolean; total: number }> {
  const response = await apiClient.get<ApiResponse<PageResponse<Conversation>>>(
    '/conversation/list',
    { params: { page, size } }
  );
  const pageData = response.data.data;
  // 转换为兼容旧格式，同时保留 total
  return {
    items: pageData?.records || [],
    hasMore: (pageData?.current || 1) < (pageData?.pages || 0),
    total: pageData?.total || 0,
  };
}

/**
 * 创建新会话
 *
 * @param params 创建参数
 * @returns 新创建的会话
 */
export async function createConversation(
  params: CreateConversationParams
): Promise<Conversation> {
  // 后端 AI 会话创建接口
  const response = await apiClient.post<ApiResponse<Conversation>>(
    '/conversation/create/assistant',
    params
  );
  return response.data.data;
}

/**
 * 删除会话
 *
 * @param id 会话ID
 */
export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`/conversation/${id}`);
}

/**
 * 获取会话历史消息（返回完整消息树）
 *
 * @param conversationId 会话ID
 * @returns 包含所有消息和当前选中消息ID的响应
 */
export async function getConversationHistory(
  conversationId: string
): Promise<{ messages: Message[]; currentMessageId: string | null }> {
  const response = await apiClient.get<ApiResponse<{ messages: Message[]; currentMessageId: string | null }>>(
    `/conversation/history`,
    { params: { conversationId } }
  );
  return response.data.data || { messages: [], currentMessageId: null };
}

/**
 * 更新会话标题
 *
 * @param id 会话ID
 * @param title 新标题
 */
export async function updateConversationTitle(
  id: string,
  title: string
): Promise<void> {
  await apiClient.patch(`/conversation/modify`, { id, title });
}
