/**
 * Workflow 管理 API
 */
import apiClient from './client';
import type { ApiResponse, AgentWorkflow, NodeTypeCatalogItem, WorkflowDefinition } from '../types';

/**
 * 获取节点类型目录
 */
export async function listWorkflowNodeTypes(): Promise<NodeTypeCatalogItem[]> {
  const response = await apiClient.get<ApiResponse<NodeTypeCatalogItem[]>>('/workflow/node-types');
  return response.data.data || [];
}

/**
 * 获取 Agent 默认 workflow
 */
export async function getAgentWorkflow(agentId: string): Promise<AgentWorkflow> {
  const response = await apiClient.get<ApiResponse<AgentWorkflow>>(`/agents/${agentId}/workflow`);
  return response.data.data;
}

/**
 * 更新 Agent 默认 workflow（创建新版本并设为默认）
 */
export async function updateAgentWorkflow(
  agentId: string,
  definition: WorkflowDefinition
): Promise<AgentWorkflow> {
  const response = await apiClient.put<ApiResponse<AgentWorkflow>>(`/agents/${agentId}/workflow`, {
    definition,
  });
  if (!response.data.success) {
    throw new Error(response.data.message || '更新 workflow 失败');
  }
  return response.data.data;
}

