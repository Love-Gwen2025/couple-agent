/**
 * 知识库相关 API
 */
import apiClient from './client';
import type { ApiResponse, PageResponse } from '../types';

// ========== 类型定义 ==========

/** 知识库 */
export interface KnowledgeBase {
    id: string;
    name: string;
    description: string | null;
    documentCount: number;
    chunkCount: number;
    createTime: string | null;
    updateTime: string | null;
}

/** 文档 */
export interface Document {
    id: string;
    fileName: string;
    fileUrl: string;
    fileSize: number | null;
    fileType: string | null;
    chunkCount: number;
    status: 'pending' | 'processing' | 'done' | 'failed';
    createTime: string | null;
}

/** 召回结果 */
export interface RecallResult {
    content: string;
    similarity: number;
    fileName: string | null;
    chunkIndex: number;
    metadata: Record<string, unknown> | null;
}

/** 召回测试参数 */
export interface RecallTestParams {
    query: string;
    mode: 'vector' | 'union' | 'intersection';
    topK: number;
    threshold: number;
}

// ========== 知识库 CRUD ==========

/**
 * 获取知识库列表（分页）
 */
export async function getKnowledgeBases(
    page: number = 1,
    size: number = 20
): Promise<PageResponse<KnowledgeBase>> {
    const response = await apiClient.get<ApiResponse<PageResponse<KnowledgeBase>>>(
        '/knowledge-bases',
        { params: { page, size } }
    );
    return response.data.data || { records: [], total: 0, size, current: page, pages: 0 };
}

/**
 * 获取单个知识库详情
 */
export async function getKnowledgeBase(id: string): Promise<KnowledgeBase> {
    const response = await apiClient.get<ApiResponse<KnowledgeBase>>(`/knowledge-bases/${id}`);
    return response.data.data;
}

/**
 * 创建知识库
 */
export async function createKnowledgeBase(
    name: string,
    description?: string
): Promise<KnowledgeBase> {
    const response = await apiClient.post<ApiResponse<KnowledgeBase>>('/knowledge-bases', {
        name,
        description,
    });
    return response.data.data;
}

/**
 * 删除知识库
 */
export async function deleteKnowledgeBase(id: string): Promise<void> {
    await apiClient.delete(`/knowledge-bases/${id}`);
}

// ========== 文档管理 ==========

/**
 * 获取文档列表（分页）
 */
export async function getDocuments(
    kbId: string,
    page: number = 1,
    size: number = 20
): Promise<PageResponse<Document>> {
    const response = await apiClient.get<ApiResponse<PageResponse<Document>>>(
        `/knowledge-bases/${kbId}/documents`,
        { params: { page, size } }
    );
    return response.data.data || { records: [], total: 0, size, current: page, pages: 0 };
}

/**
 * 上传文档
 */
export async function uploadDocument(kbId: string, file: File): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<ApiResponse<Document>>(
        `/knowledge-bases/${kbId}/documents`,
        formData,
        {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 120000, // 文件上传可能需要更长时间
        }
    );
    return response.data.data;
}

/**
 * 删除文档
 */
export async function deleteDocument(kbId: string, docId: string): Promise<void> {
    await apiClient.delete(`/knowledge-bases/${kbId}/documents/${docId}`);
}

// ========== 召回测试 ==========

/**
 * 执行召回测试
 */
export async function recallTest(
    kbId: string,
    params: RecallTestParams
): Promise<RecallResult[]> {
    const response = await apiClient.post<ApiResponse<RecallResult[]>>(
        `/knowledge-bases/${kbId}/recall-test`,
        params
    );
    return response.data.data || [];
}
