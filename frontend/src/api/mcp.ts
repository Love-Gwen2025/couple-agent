/**
 * MCP 管理 API
 */
import apiClient from './client';
import type {
  ApiResponse,
  McpServer,
  McpServerPayload,
  McpServerUpdatePayload,
  McpTool,
  McpToolTestPayload,
  McpToolTestResult,
} from '../types';

export async function listMcpServers(): Promise<McpServer[]> {
  const response = await apiClient.get<ApiResponse<McpServer[]>>('/mcp/servers');
  return response.data.data || [];
}

export async function createMcpServer(payload: McpServerPayload): Promise<McpServer> {
  const response = await apiClient.post<ApiResponse<McpServer>>('/mcp/servers', payload);
  if (!response.data.success) {
    throw new Error(response.data.message || '创建 MCP Server 失败');
  }
  return response.data.data;
}

export async function updateMcpServer(
  serverId: string,
  payload: McpServerUpdatePayload
): Promise<McpServer> {
  const response = await apiClient.put<ApiResponse<McpServer>>(`/mcp/servers/${serverId}`, payload);
  if (!response.data.success) {
    throw new Error(response.data.message || '更新 MCP Server 失败');
  }
  return response.data.data;
}

export async function deleteMcpServer(serverId: string): Promise<void> {
  const response = await apiClient.delete<ApiResponse<null>>(`/mcp/servers/${serverId}`);
  if (!response.data.success) {
    throw new Error(response.data.message || '删除 MCP Server 失败');
  }
}

export async function syncMcpTools(serverId: string): Promise<{ count: number }> {
  const response = await apiClient.post<ApiResponse<{ count: number }>>(`/mcp/servers/${serverId}/sync`);
  if (!response.data.success) {
    throw new Error(response.data.message || '同步 MCP Tools 失败');
  }
  return response.data.data;
}

export async function listMcpTools(): Promise<McpTool[]> {
  const response = await apiClient.get<ApiResponse<McpTool[]>>('/mcp/tools');
  return response.data.data || [];
}

export async function updateMcpToolEnabled(toolId: string, enabled: boolean): Promise<McpTool> {
  const response = await apiClient.put<ApiResponse<McpTool>>(`/mcp/tools/${toolId}`, { enabled });
  if (!response.data.success) {
    throw new Error(response.data.message || '更新 MCP Tool 失败');
  }
  return response.data.data;
}

export async function testMcpTool(toolId: string, payload: McpToolTestPayload): Promise<McpToolTestResult> {
  const response = await apiClient.post<ApiResponse<McpToolTestResult>>(`/mcp/tools/${toolId}/test`, payload);
  if (!response.data.success) {
    throw new Error(response.data.message || '测试 MCP Tool 失败');
  }
  return response.data.data;
}
