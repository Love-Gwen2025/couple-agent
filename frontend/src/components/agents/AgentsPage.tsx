/**
 * Agents 管理页面
 *
 * - Agent CRUD
 * - 绑定模型 / 工具 / 知识库
 * - 支持 team Agent 绑定成员（多 Agent 协作对外仍为一个 agentId）
 */
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Edit2, GitBranch, Loader2, Plus, Trash2, Users } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';
import { useNavigationStore } from '../../store';
import {
  createAgent,
  deleteAgent,
  getAgent,
  getUserModels,
  listAgents,
  listTools,
  updateAgent,
} from '../../api';
import { getAllKnowledgeBases, type KnowledgeBase } from '../../api/knowledge';
import type { Agent, AgentPayload, ToolItem, UserModel } from '../../types';

function badgeClass(enabled: boolean) {
  return clsx(
    'px-2.5 py-1 text-[10px] font-black rounded-full uppercase tracking-widest border',
    enabled
      ? 'bg-green-500/10 text-green-400 border-green-500/20'
      : 'bg-surface-highlight/10 text-muted border-border/10'
  );
}

function uniqueStrings(items: string[]) {
  return Array.from(new Set(items.filter(Boolean)));
}

export function AgentsPage() {
  const { setCurrentPage, openAgentWorkflow } = useNavigationStore();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [userModels, setUserModels] = useState<UserModel[]>([]);

  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);

  const modelNameById = useMemo(() => {
    const map = new Map<string, string>();
    userModels.forEach((m) => map.set(m.id, m.modelName));
    return map;
  }, [userModels]);

  const memberCandidates = useMemo(() => {
    return agents.filter((a) => a.kind === 'single' && a.status === 1);
  }, [agents]);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [agentList, toolList, kbList, modelList] = await Promise.all([
        listAgents(),
        listTools(),
        getAllKnowledgeBases(),
        getUserModels(),
      ]);
      setAgents(agentList);
      setTools(toolList);
      setKnowledgeBases(kbList);
      setUserModels(modelList);
    } catch (error) {
      console.error('Failed to load agents:', error);
    } finally {
      setLoading(false);
    }
  }

  async function openCreate() {
    setEditingAgent(null);
    setShowModal(true);
  }

  async function openEdit(agentId: string) {
    try {
      const detail = await getAgent(agentId);
      setEditingAgent(detail);
      setShowModal(true);
    } catch (error) {
      alert('加载 Agent 详情失败: ' + (error as Error).message);
    }
  }

  async function handleDelete(agentId: string) {
    if (!confirm('确定要删除这个 Agent 吗？')) return;
    try {
      await deleteAgent(agentId);
      setAgents((prev) => prev.filter((a) => a.id !== agentId));
    } catch (error) {
      alert('删除失败: ' + (error as Error).message);
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
      <header className="flex items-center gap-4 px-8 py-6 border-b border-border/10 bg-surface/50 backdrop-blur-md z-10">
        <button
          onClick={() => setCurrentPage('chat')}
          className="p-2 rounded-xl hover:bg-surface-highlight/20 transition-all text-muted hover:text-foreground"
          title="Back"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-2xl bg-surface-container border border-border/30 flex items-center justify-center">
            <Users className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-tight">Agents</h1>
            <p className="text-sm text-muted">按配置管理模型 / 工具 / 知识库；team Agent 支持多 Agent 协作</p>
          </div>
        </div>

        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary/90 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          新建 Agent
        </button>
      </header>

      <main className="flex-1 overflow-auto p-8">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            加载中...
          </div>
        ) : (
          <div className="rounded-2xl border border-border/10 bg-surface/30 overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-surface/40 border-b border-border/10">
                <tr>
                  <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Name</th>
                  <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Kind</th>
                  <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Model</th>
                  <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Bindings</th>
                  <th className="px-6 py-4 text-[10px] font-black text-muted text-center uppercase tracking-widest">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black text-muted text-right uppercase tracking-widest">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/5">
                {agents.map((agent) => (
                  <tr
                    key={agent.id}
                    className="border-b border-border/5 last:border-0 hover:bg-surface-highlight/5 transition-colors"
                  >
                    <td className="px-6 py-5">
                      <div className="font-bold text-foreground tracking-tight">{agent.name}</div>
                      {agent.description && (
                        <div className="text-xs text-muted mt-1 line-clamp-1">{agent.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-5">
                      <span className="px-3 py-1 text-[10px] font-black rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 uppercase tracking-widest">
                        {agent.kind.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <code className="text-[11px] text-muted bg-surface/40 px-2 py-1 rounded-md border border-border/10">
                        {modelNameById.get(agent.userModelId) || agent.userModelId}
                      </code>
                    </td>
                    <td className="px-6 py-5 text-sm text-muted">
                      工具 {agent.toolRefs?.length ?? 0} · KB {agent.knowledgeBaseIds?.length ?? 0}
                      {agent.kind === 'team' ? ` · 成员 ${agent.memberAgentIds?.length ?? 0}` : ''}
                    </td>
                    <td className="px-6 py-5 text-center">
                      <span className={badgeClass(agent.status === 1)}>
                        {agent.status === 1 ? 'ONLINE' : 'OFFLINE'}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openAgentWorkflow(agent.id)}
                          disabled={agent.kind !== 'single'}
                          className={clsx(
                            'p-2 rounded-lg transition-colors',
                            agent.kind === 'single'
                              ? 'hover:bg-surface-highlight/20 text-muted hover:text-foreground'
                              : 'text-muted/40 cursor-not-allowed'
                          )}
                          title={agent.kind === 'single' ? '编辑 Workflow' : '仅 single Agent 支持 Workflow'}
                        >
                          <GitBranch className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => openEdit(agent.id)}
                          className="p-2 rounded-lg hover:bg-surface-highlight/20 transition-colors text-muted hover:text-foreground"
                          title="编辑"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(agent.id)}
                          className="p-2 rounded-lg hover:bg-red-500/10 transition-colors text-muted hover:text-red-400"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {agents.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-muted font-medium">
                      暂无 Agent。点击右上角新建。
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <AnimatePresence>
        {showModal && (
          <AgentFormModal
            agent={editingAgent}
            tools={tools}
            knowledgeBases={knowledgeBases}
            userModels={userModels}
            memberCandidates={memberCandidates}
            onClose={() => {
              setShowModal(false);
              setEditingAgent(null);
            }}
            onSaved={async () => {
              setShowModal(false);
              setEditingAgent(null);
              await loadAll();
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function AgentFormModal({
  agent,
  tools,
  knowledgeBases,
  userModels,
  memberCandidates,
  onClose,
  onSaved,
}: {
  agent: Agent | null;
  tools: ToolItem[];
  knowledgeBases: KnowledgeBase[];
  userModels: UserModel[];
  memberCandidates: Agent[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const isEdit = !!agent;

  const [loading, setLoading] = useState(false);
  const [kind, setKind] = useState<'single' | 'team'>((agent?.kind as 'single' | 'team') || 'single');
  const [name, setName] = useState(agent?.name || '');
  const [description, setDescription] = useState(agent?.description || '');
  const [systemPrompt, setSystemPrompt] = useState(agent?.systemPrompt || '');
  const [userModelId, setUserModelId] = useState(agent?.userModelId || '');
  const [status, setStatus] = useState(agent?.status ?? 1);
  const [toolRefs, setToolRefs] = useState<string[]>(agent?.toolRefs || []);
  const [knowledgeBaseIds, setKnowledgeBaseIds] = useState<string[]>(agent?.knowledgeBaseIds || []);
  const [memberAgentIds, setMemberAgentIds] = useState<string[]>(agent?.memberAgentIds || []);

  const unavailableMembers = useMemo(() => {
    if (kind !== 'team') return [];
    const available = new Set(memberCandidates.map((a) => a.id));
    return memberAgentIds.filter((id) => !available.has(id));
  }, [kind, memberCandidates, memberAgentIds]);

  function toggleId(list: string[], id: string): string[] {
    return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!name.trim()) {
      alert('请填写 Agent 名称');
      return;
    }
    if (!userModelId) {
      alert('Agent 必须绑定模型');
      return;
    }
    if (kind !== 'team') {
      setMemberAgentIds([]);
    }

    setLoading(true);
    try {
      const payload: AgentPayload = {
        kind,
        name: name.trim(),
        description: description.trim() || null,
        systemPrompt: systemPrompt.trim() || null,
        userModelId,
        status,
        toolRefs: uniqueStrings(toolRefs),
        knowledgeBaseIds: uniqueStrings(knowledgeBaseIds),
        memberAgentIds: kind === 'team' ? uniqueStrings(memberAgentIds) : [],
      };

      if (isEdit && agent) {
        await updateAgent(agent.id, payload);
      } else {
        await createAgent(payload);
      }
      await onSaved();
    } catch (error) {
      alert('保存失败: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-3xl rounded-2xl border p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--background))' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">{isEdit ? '编辑 Agent' : '新建 Agent'}</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-surface-highlight/20 transition-all text-muted hover:text-foreground"
            title="关闭"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 max-h-[70vh] overflow-auto custom-scrollbar">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted">类型</label>
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value as 'single' | 'team')}
                className="w-full px-4 py-2 rounded-xl border text-foreground focus:outline-none focus:border-primary appearance-none transition-all"
                style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
              >
                <option value="single" className="bg-surface text-foreground">
                  single
                </option>
                <option value="team" className="bg-surface text-foreground">
                  team
                </option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-muted">状态</label>
              <select
                value={String(status)}
                onChange={(e) => setStatus(Number(e.target.value))}
                className="w-full px-4 py-2 rounded-xl border text-foreground focus:outline-none focus:border-primary appearance-none transition-all"
                style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
              >
                <option value="1" className="bg-surface text-foreground">
                  启用
                </option>
                <option value="0" className="bg-surface text-foreground">
                  禁用
                </option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted">名称</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all"
                style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
                placeholder="例如：RAG 助手 / 代码审查 / 资料整理"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted">绑定模型</label>
              <select
                value={userModelId}
                onChange={(e) => setUserModelId(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border text-foreground focus:outline-none focus:border-primary appearance-none transition-all"
                style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
              >
                <option value="" className="bg-surface text-muted">
                  请选择用户模型…
                </option>
                {userModels.map((m) => (
                  <option key={m.id} value={m.id} className="bg-surface text-foreground">
                    {m.modelName} ({m.provider}/{m.modelCode}) {m.status === 1 ? '' : '·OFFLINE'}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">描述（可选）</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all"
              style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
              placeholder="用于在 team/supervisor 中帮助选择合适的 Agent"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">系统提示词（可选）</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all min-h-[120px]"
              style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
              placeholder="将写入 Agent 的 system prompt；聊天请求不允许覆盖"
            />
          </div>

          {/* Tools */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">绑定工具</label>
            <div className="rounded-xl border border-border/20 bg-surface/40 p-3 max-h-56 overflow-auto custom-scrollbar space-y-1">
              {tools.map((t) => {
                const checked = toolRefs.includes(t.toolRef);
                const disabled = !t.enabled;
                return (
                  <label
                    key={t.toolRef}
                    className={clsx(
                      'flex items-start gap-3 p-2 rounded-lg transition-colors',
                      disabled ? 'opacity-60' : 'hover:bg-surface-highlight/10'
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => setToolRefs((prev) => toggleId(prev, t.toolRef))}
                      className="mt-1"
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-foreground truncate">
                          {t.displayName || t.name}
                        </span>
                        <code className="text-[10px] text-muted bg-surface/40 px-2 py-0.5 rounded-md border border-border/10">
                          {t.type}
                        </code>
                        {!t.enabled && (
                          <span className="text-[10px] text-red-400">禁用</span>
                        )}
                      </div>
                      <div className="text-xs text-muted break-all">{t.toolRef}</div>
                      {t.description && (
                        <div className="text-xs text-muted mt-1 line-clamp-1">{t.description}</div>
                      )}
                    </div>
                  </label>
                );
              })}
              {tools.length === 0 && <div className="text-sm text-muted px-2 py-3">暂无工具</div>}
            </div>
          </div>

          {/* KB */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">绑定知识库</label>
            <div className="rounded-xl border border-border/20 bg-surface/40 p-3 max-h-56 overflow-auto custom-scrollbar space-y-1">
              {knowledgeBases.map((kb) => {
                const checked = knowledgeBaseIds.includes(kb.id);
                return (
                  <label key={kb.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-highlight/10 transition-colors">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => setKnowledgeBaseIds((prev) => toggleId(prev, kb.id))}
                    />
                    <span className="text-sm text-foreground">{kb.name}</span>
                    <span className="text-xs text-muted ml-auto">{kb.id}</span>
                  </label>
                );
              })}
              {knowledgeBases.length === 0 && (
                <div className="text-sm text-muted px-2 py-3">暂无知识库</div>
              )}
            </div>
          </div>

          {/* Team members */}
          {kind === 'team' && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted">team 成员（仅 single 且启用）</label>

              {unavailableMembers.length > 0 && (
                <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3 text-sm text-yellow-200">
                  存在不可用成员（已禁用/不存在）：{unavailableMembers.join(', ')}。保存前请移除。
                  <div className="mt-2 flex flex-wrap gap-2">
                    {unavailableMembers.map((id) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setMemberAgentIds((prev) => prev.filter((x) => x !== id))}
                        className="px-2 py-1 rounded-lg bg-surface/40 border border-border/20 text-xs hover:bg-surface-highlight/10"
                      >
                        移除 {id}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="rounded-xl border border-border/20 bg-surface/40 p-3 max-h-56 overflow-auto custom-scrollbar space-y-1">
                {memberCandidates.map((a) => {
                  const checked = memberAgentIds.includes(a.id);
                  return (
                    <label key={a.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-highlight/10 transition-colors">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => setMemberAgentIds((prev) => toggleId(prev, a.id))}
                      />
                      <span className="text-sm text-foreground">{a.name}</span>
                      <span className="text-xs text-muted ml-auto">{a.id}</span>
                    </label>
                  );
                })}
                {memberCandidates.length === 0 && (
                  <div className="text-sm text-muted px-2 py-3">暂无可用 single Agent</div>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border/20 bg-surface/40 text-muted hover:text-foreground hover:bg-surface-highlight/10 transition-colors"
              disabled={loading}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary/90 transition-all shadow-sm disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              保存
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
