/**
 * 类型定义文件
 *
 * 定义前端使用的所有 TypeScript 类型
 * 注意: 所有 ID 字段使用 string 类型，避免 JavaScript 大整数精度丢失
 */

/** 用户信息（后端字段命名） */
export interface User {
  id: number;  // 用户 ID 暂时保留 number（通常较小）
  userCode: string;
  userName?: string;
  avatar?: string;
}

/** 登录参数（后端要求 userCode/userPassword） */
export interface LoginParams {
  userCode: string;
  userPassword: string;
}

/** 登录响应：后端仅返回 token 字符串 */
export type LoginResponse = string;

/** 会话信息 */
export interface Conversation {
  id: string;  // 雪花ID，使用 string 避免精度丢失
  title: string;
  userId?: string;
  modelCode?: string;
  lastMessageId?: string;
  lastMessageAt?: string;
  avatar?: string;
  createdAt?: string;
  updatedAt?: string;
}

/** 消息信息 */
export interface Message {
  id: string;  // 消息 ID，统一使用 string（包括临时 ID 如 "temp-xxx"）
  conversationId: string;
  senderId: number | string;  // 兼容 AI (-1) 和用户 ID
  role: 'user' | 'assistant' | 'system';
  content: string;
  contentType: string;
  modelCode?: string;
  tokenCount?: number;
  createTime: string;
  /** 父消息 ID，用于分支导航 */
  parentId?: string;
  /** Checkpoint ID，用于 LangGraph 恢复执行 */
  checkpointId?: string;
}

/** 分支信息（用于 2/3 导航） */
export interface SiblingInfo {
  current: number;
  total: number;
  siblings: string[];
}

/** 会话历史消息视图（后端 history 接口返回） */
export interface HistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

/** AI 模型信息 */
export interface AiModel {
  id: number;
  modelCode: string;
  modelName: string;
  provider: string;
  isDefault: boolean;
  status: number;
}

/** 用户自定义模型配置 */
export interface UserModel {
  id: string;
  modelName: string;
  provider: string;  // 'openai' | 'deepseek' | 'gemini' | 'custom'
  modelCode: string;
  baseUrl?: string;
  temperature: number;
  timeout: number;
  // 高级参数
  topP?: number;
  maxTokens?: number;
  topK?: number;
  isDefault: boolean;
  status: number;
}

/** 添加用户模型请求 */
export interface UserModelPayload {
  modelName: string;
  provider: string;
  modelCode: string;
  apiKey: string;
  baseUrl?: string;
  temperature?: number;
  timeout?: number;
  // 高级参数
  topP?: number;
  maxTokens?: number;
  topK?: number;
}

/** 更新用户模型请求（apiKey 可选） */
export interface UserModelUpdatePayload {
  modelName?: string;
  provider?: string;
  modelCode?: string;
  apiKey?: string;
  baseUrl?: string;
  temperature?: number;
  timeout?: number;
  // 高级参数
  topP?: number;
  maxTokens?: number;
  topK?: number;
}

/** 测试模型连接请求 */
export interface UserModelTestPayload {
  provider: string;
  modelCode: string;
  apiKey: string;
  baseUrl?: string;
}

/** 测试模型连接响应 */
export interface UserModelTestResult {
  success: boolean;
  message: string;
  response?: string;
}

/** 创建会话参数 */
export interface CreateConversationParams {
  title?: string;
  modelCode?: string;
}

/** 流式聊天请求参数 */
export interface StreamChatRequest {
  conversationId: string;
  content: string;
  modelCode?: string;
  /** 用户模型 ID，传此参数则使用用户自定义模型 */
  modelId?: string;
  systemPrompt?: string;
  /** 父消息 ID，用于构建消息树 */
  parentMessageId?: string;
  /** 是否重新生成 */
  regenerate?: boolean;
  /** 对话模式: chat/deep_search */
  mode?: string;
}

/** 流式聊天事件 */
export interface StreamChatEvent {
  type: 'chunk' | 'done' | 'error' | 'tool_start' | 'tool_end';
  content?: string;
  messageId?: string;
  conversationId?: string;
  tokenCount?: number;
  error?: string;
  /** 父消息 ID */
  parentId?: string;
  /** 用户消息真实 ID */
  userMessageId?: string;
  /** 工具名称（tool_start/tool_end 事件时使用） */
  tool?: string;
  /** 新生成的会话标题（首次发消息时返回） */
  title?: string;
}

/** 消息历史响应 */
export interface HistoryResponse {
  messages: Message[];
  currentMessageId: string | null;
}

/** API 响应包装 */
export interface ApiResponse<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
}

/** 分页参数 */
export interface PageParams {
  page?: number;
  size?: number;
}

/** 分页响应 */
export interface PageResponse<T> {
  records: T[];
  total: number;
  size: number;
  current: number;
  pages: number;
}

