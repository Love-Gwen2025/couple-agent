/**
 * 导航状态管理
 *
 * 管理页面导航和选中状态
 */
import { create } from 'zustand';

/** 页面类型 */
export type PageType = 'chat' | 'model-settings' | 'knowledge' | 'knowledge-detail';

/** 导航状态接口 */
interface NavigationState {
  /** 当前页面 */
  currentPage: PageType;
  /** 选中的知识库ID（用于详情页） */
  selectedKnowledgeBaseId: string | null;
}

/** 导航操作接口 */
interface NavigationActions {
  /** 设置当前页面 */
  setCurrentPage: (page: PageType) => void;
  /** 设置选中的知识库ID */
  setSelectedKnowledgeBaseId: (id: string | null) => void;
  /** 进入知识库详情页 */
  openKnowledgeDetail: (id: string) => void;
  /** 返回知识库列表 */
  backToKnowledgeList: () => void;
}

/** 导航 Store */
export const useNavigationStore = create<NavigationState & NavigationActions>()(
  (set) => ({
    // 初始状态
    currentPage: 'chat',
    selectedKnowledgeBaseId: null,

    // 操作方法
    setCurrentPage: (page) => set({ currentPage: page }),

    setSelectedKnowledgeBaseId: (id) => set({ selectedKnowledgeBaseId: id }),

    openKnowledgeDetail: (id) =>
      set({
        currentPage: 'knowledge-detail',
        selectedKnowledgeBaseId: id,
      }),

    backToKnowledgeList: () =>
      set({
        currentPage: 'knowledge',
        selectedKnowledgeBaseId: null,
      }),
  })
);

// 选择器 Hooks
export const useCurrentPage = () => useNavigationStore((state) => state.currentPage);

export const useSelectedKnowledgeBaseId = () =>
  useNavigationStore((state) => state.selectedKnowledgeBaseId);
