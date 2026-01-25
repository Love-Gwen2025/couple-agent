/**
 * Agent 管理 API
 */
import apiClient from './client';
import type { ApiResponse, Agent, AgentPayload, AgentUpdatePayload } from '../types';

/**
 * 规范化 Agent 请求体
 * 
 * 注意：ID 保持字符串格式发送，避免 JS 大整数精度丢失
 * 后端 SnowflakeId 类型会自动处理 str->int 转换
 */
function normalizeAgentPayload(payload: AgentPayload | AgentUpdatePayload): Record<string, unknown> {
  // 直接返回 payload，ID 保持字符串格式
  return { ...payload };
}


/**
 * 获取 Agent 列表（轻量）
 */
export async function listAgents(): Promise<Agent[]> {
  const response = await apiClient.get<ApiResponse<Agent[]>>('/agents');
  return response.data.data || [];
}

/**
 * 获取 Agent 详情（含绑定信息）
 */
export async function getAgent(agentId: string): Promise<Agent> {
  const response = await apiClient.get<ApiResponse<Agent>>(`/agents/${agentId}`);
  return response.data.data;
}

/**
 * 创建 Agent
 */
export async function createAgent(payload: AgentPayload): Promise<Agent> {
  const response = await apiClient.post<ApiResponse<Agent>>('/agents', normalizeAgentPayload(payload));
  if (!response.data.success) {
    throw new Error(response.data.message || '创建 Agent 失败');
  }
  return response.data.data;
}

/**
 * 更新 Agent
 */
export async function updateAgent(agentId: string, payload: AgentUpdatePayload): Promise<Agent> {
  const response = await apiClient.put<ApiResponse<Agent>>(
    `/agents/${agentId}`,
    normalizeAgentPayload(payload)
  );
  if (!response.data.success) {
    throw new Error(response.data.message || '更新 Agent 失败');
  }
  return response.data.data;
}

/**
 * 删除 Agent
 */
export async function deleteAgent(agentId: string): Promise<void> {
  const response = await apiClient.delete<ApiResponse<null>>(`/agents/${agentId}`);
  if (!response.data.success) {
    throw new Error(response.data.message || '删除 Agent 失败');
  }
}
