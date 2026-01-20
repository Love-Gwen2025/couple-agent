/**
 * 用户模型管理 API
 */
import apiClient from './client';
import type {
    ApiResponse,
    UserModel,
    UserModelPayload,
    UserModelUpdatePayload,
    UserModelTestPayload,
    UserModelTestResult,
} from '../types';

/**
 * 获取用户模型列表
 */
export async function getUserModels(): Promise<UserModel[]> {
    try {
        const response = await apiClient.get<ApiResponse<UserModel[]>>('/user/model');
        return response.data.data || [];
    } catch (e) {
        console.error('获取用户模型列表失败:', e);
        return [];
    }
}

/**
 * 添加用户模型
 */
export async function createUserModel(payload: UserModelPayload): Promise<UserModel> {
    const response = await apiClient.post<ApiResponse<UserModel>>('/user/model', payload);
    if (!response.data.success) {
        throw new Error(response.data.message || '添加模型失败');
    }
    return response.data.data;
}

/**
 * 更新用户模型
 */
export async function updateUserModel(id: string, payload: UserModelUpdatePayload): Promise<UserModel> {
    const response = await apiClient.put<ApiResponse<UserModel>>(`/user/model/${id}`, payload);
    if (!response.data.success) {
        throw new Error(response.data.message || '更新模型失败');
    }
    return response.data.data;
}

/**
 * 删除用户模型
 */
export async function deleteUserModel(id: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse<null>>(`/user/model/${id}`);
    if (!response.data.success) {
        throw new Error(response.data.message || '删除模型失败');
    }
}

/**
 * 设置默认模型
 */
export async function setDefaultUserModel(id: string): Promise<void> {
    const response = await apiClient.put<ApiResponse<null>>(`/user/model/${id}/default`);
    if (!response.data.success) {
        throw new Error(response.data.message || '设置默认模型失败');
    }
}

/**
 * 测试模型连接
 */
export async function testUserModel(payload: UserModelTestPayload): Promise<UserModelTestResult> {
    const response = await apiClient.post<ApiResponse<UserModelTestResult>>('/user/model/test', payload);
    return response.data.data;
}
