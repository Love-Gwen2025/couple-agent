/**
 * Tool 目录 API
 *
 * 统一对外暴露内置工具 + MCP 工具（同一层级）。
 */
import apiClient from './client';
import type { ApiResponse, ToolItem } from '../types';

export async function listTools(): Promise<ToolItem[]> {
  const response = await apiClient.get<ApiResponse<ToolItem[]>>('/tools');
  return response.data.data || [];
}

