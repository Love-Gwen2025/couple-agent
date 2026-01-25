/**
 * Agent 状态管理
 *
 * 管理 Agent 列表与当前选择（用于聊天发起与新会话创建）。
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Agent } from '../types';

interface AgentState {
  agents: Agent[];
  currentAgentId: string | null;
}

interface AgentActions {
  setAgents: (agents: Agent[]) => void;
  setCurrentAgentId: (agentId: string | null) => void;
  clearAgents: () => void;
}

export const useAgentStore = create<AgentState & AgentActions>()(
  persist(
    (set) => ({
      agents: [],
      currentAgentId: null,

      setAgents: (agents) => set({ agents }),
      setCurrentAgentId: (agentId) => set({ currentAgentId: agentId }),
      clearAgents: () => set({ agents: [] }),
    }),
    {
      name: 'agent-storage',
      partialize: (state) => ({
        currentAgentId: state.currentAgentId,
      }),
    }
  )
);

export const useAgents = () => useAgentStore((state) => state.agents);
export const useCurrentAgentId = () => useAgentStore((state) => state.currentAgentId);

