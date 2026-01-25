/**
 * Agent 选择器组件
 *
 * 注意：
 * - 聊天请求以 agentId 为执行单位（模型/工具/知识库均来自 Agent 配置，不允许请求覆盖）
 * - 会话一旦绑定 agentId 后不可覆盖
 */
import { useEffect, useMemo, useState } from 'react';
import { Bot, Check, ChevronDown, Lock } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';
import { useAuthStore, useAgentStore } from '../../store';
import { listAgents } from '../../api';

export function AgentSelector({
  lockedAgentId,
  onOpenAgents,
}: {
  lockedAgentId: string | null;
  onOpenAgents?: () => void;
}) {
  const { token } = useAuthStore();
  const { agents, currentAgentId, setAgents, setCurrentAgentId } = useAgentStore();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (token) void loadAgents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function loadAgents() {
    try {
      const data = await listAgents();
      setAgents(data);

      const effectiveId = lockedAgentId || currentAgentId;
      if (!effectiveId && data.length > 0) {
        setCurrentAgentId(data[0].id);
      }
    } catch (error) {
      console.error('加载 Agent 列表失败:', error);
    }
  }

  const effectiveAgentId = lockedAgentId || currentAgentId;
  const currentAgent = useMemo(
    () => agents.find((a) => a.id === effectiveAgentId) || null,
    [agents, effectiveAgentId]
  );

  if (agents.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted bg-surface/50 border border-border/30 rounded-xl px-3 py-2">
        <Bot className="w-4 h-4" />
        <span>暂无 Agent</span>
        {onOpenAgents && (
          <button
            onClick={onOpenAgents}
            className="ml-2 text-primary hover:underline"
            type="button"
          >
            去创建
          </button>
        )}
      </div>
    );
  }

  const disabled = Boolean(lockedAgentId);

  return (
    <div className="relative z-50">
      <button
        type="button"
        disabled={disabled}
        className={clsx(
          'flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border/50 transition-all duration-200 text-sm font-medium',
          disabled ? 'bg-surface/40 text-muted cursor-not-allowed' : 'bg-surface/50 hover:bg-surface-highlight text-muted hover:text-foreground',
          isOpen && !disabled && 'bg-surface-highlight text-primary ring-2 ring-primary/10'
        )}
        onClick={() => setIsOpen((v) => !v)}
        title={disabled ? '该会话已绑定 Agent，禁止覆盖' : undefined}
      >
        {disabled ? (
          <Lock className="w-4 h-4 text-muted" />
        ) : (
          <Bot className={clsx('w-4 h-4', isOpen ? 'text-primary' : 'text-muted')} />
        )}
        <span className="max-w-[180px] truncate">{currentAgent?.name || '选择 Agent'}</span>
        <ChevronDown
          className={clsx(
            'w-3.5 h-3.5 transition-transform duration-200 opacity-50',
            isOpen && 'rotate-180 opacity-100'
          )}
        />
      </button>

      <AnimatePresence>
        {isOpen && !disabled && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 5, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 5, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full left-0 mt-2 w-72 bg-surface/90 backdrop-blur-xl border border-border rounded-xl shadow-2xl z-20 overflow-hidden p-1.5"
            >
              <div className="px-2 py-1.5 text-xs font-semibold text-muted/50 uppercase tracking-wider">
                Available Agents
              </div>
              {agents.map((agent) => {
                const isSelected = agent.id === effectiveAgentId;
                return (
                  <button
                    key={agent.id}
                    type="button"
                    className={clsx(
                      'w-full px-3 py-2.5 text-left text-sm rounded-lg transition-all flex items-center justify-between group',
                      isSelected
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-surface-highlight text-muted hover:text-foreground'
                    )}
                    onClick={() => {
                      setCurrentAgentId(agent.id);
                      setIsOpen(false);
                    }}
                  >
                    <div className="min-w-0">
                      <div className="font-medium truncate flex items-center gap-2">
                        <span className="truncate">{agent.name}</span>
                        <span className="px-2 py-0.5 text-[10px] font-black rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 uppercase tracking-widest">
                          {agent.kind.toUpperCase()}
                        </span>
                        {agent.status !== 1 && <span className="text-[10px] text-red-400">OFFLINE</span>}
                      </div>
                      {agent.description && (
                        <div className="text-xs text-muted mt-0.5 line-clamp-1">{agent.description}</div>
                      )}
                    </div>
                    {isSelected && <Check className="w-4 h-4 text-primary flex-shrink-0" />}
                  </button>
                );
              })}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

