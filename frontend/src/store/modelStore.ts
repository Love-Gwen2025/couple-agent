/**
 * 模型状态管理
 *
 * 管理 AI 模型选择
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AiModel } from '../types';

/** 模型状态接口 */
interface ModelState {
  /** 可用的 AI 模型列表 */
  models: AiModel[];
  /** 当前选中的模型编码 */
  currentModelCode: string | null;
  /** 当前选中的用户模型 ID（系统默认模型为 null） */
  currentModelId: string | null;
}

/** 模型操作接口 */
interface ModelActions {
  /** 设置模型列表 */
  setModels: (models: AiModel[]) => void;
  /** 设置当前模型编码 */
  setCurrentModelCode: (code: string | null) => void;
  /** 设置当前用户模型 ID */
  setCurrentModelId: (id: string | null) => void;
}

/** 模型 Store */
export const useModelStore = create<ModelState & ModelActions>()(
  persist(
    (set) => ({
      // 初始状态
      models: [],
      currentModelCode: null,
      currentModelId: null,

      // 操作方法
      setModels: (models) => set({ models }),
      setCurrentModelCode: (code) => set({ currentModelCode: code }),
      setCurrentModelId: (id) => set({ currentModelId: id }),
    }),
    {
      name: 'model-storage',
      partialize: (state) => ({
        currentModelCode: state.currentModelCode,
        currentModelId: state.currentModelId,
      }),
    }
  )
);

// 选择器 Hooks
export const useCurrentModel = () =>
  useModelStore((state) => ({
    code: state.currentModelCode,
    id: state.currentModelId,
  }));

export const useModels = () => useModelStore((state) => state.models);
