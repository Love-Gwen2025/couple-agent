/**
 * Agent Workflow 设计器（MVP）
 *
 * 目标：
 * - 为 kind=single Agent 提供可视化 DAG 编辑（最小闭环节点）
 * - 保存为 Agent 默认 workflow（后端创建新版本并设为默认）
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Link2, Loader2, Save, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import { useNavigationStore } from '../../store';
import { getAgent, getAgentWorkflow, listWorkflowNodeTypes, updateAgentWorkflow } from '../../api';
import type { Agent, AgentWorkflow, WorkflowDefinition, WorkflowEdge, WorkflowNode, WorkflowNodeType } from '../../types';

const NODE_WIDTH = 140;
const NODE_HEIGHT = 44;

function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function nodeColor(type: WorkflowNodeType) {
  switch (type) {
    case 'start':
      return 'bg-green-500/10 border-green-500/30 text-green-400';
    case 'end':
      return 'bg-red-500/10 border-red-500/30 text-red-400';
    case 'router':
      return 'bg-purple-500/10 border-purple-500/30 text-purple-400';
    case 'context':
      return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
    case 'llm':
      return 'bg-primary/10 border-primary/30 text-primary';
    case 'verify':
      return 'bg-amber-500/10 border-amber-500/30 text-amber-400';
  }
}

function clampNumber(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function AgentWorkflowDesignerPage() {
  const { backToAgents, selectedWorkflowAgentId } = useNavigationStore();
  const canvasRef = useRef<HTMLDivElement | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [workflow, setWorkflow] = useState<AgentWorkflow | null>(null);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [edges, setEdges] = useState<WorkflowEdge[]>([]);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [connectingFrom, setConnectingFrom] = useState<string | null>(null);

  const draggingRef = useRef<{
    nodeId: string;
    offsetX: number;
    offsetY: number;
  } | null>(null);

  const nodesById = useMemo(() => {
    const map = new Map<string, WorkflowNode>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  const nodeTypesInGraph = useMemo(() => new Set(nodes.map((n) => n.type)), [nodes]);

  useEffect(() => {
    if (!selectedWorkflowAgentId) {
      backToAgents();
      return;
    }
    void loadAll(selectedWorkflowAgentId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedWorkflowAgentId]);

  useEffect(() => {
    function handleMove(event: PointerEvent) {
      const dragging = draggingRef.current;
      const canvas = canvasRef.current;
      if (!dragging || !canvas) return;

      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left - dragging.offsetX;
      const y = event.clientY - rect.top - dragging.offsetY;

      setNodes((prev) =>
        prev.map((n) =>
          n.id === dragging.nodeId
            ? {
                ...n,
                position: {
                  x: clampNumber(x, -2000, 2000),
                  y: clampNumber(y, -2000, 2000),
                },
              }
            : n
        )
      );
    }

    function handleUp() {
      draggingRef.current = null;
    }

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, []);

  async function loadAll(agentId: string) {
    setLoading(true);
    try {
      // 触发一次 node types 拉取（用于后端健康与未来扩展），MVP UI 直接硬编码按钮
      await listWorkflowNodeTypes();

      const [agentDetail, wf] = await Promise.all([getAgent(agentId), getAgentWorkflow(agentId)]);
      setAgent(agentDetail);
      setWorkflow(wf);
      hydrateFromDefinition(wf.definition);
    } catch (error) {
      alert('加载 workflow 失败: ' + (error as Error).message);
      backToAgents();
    } finally {
      setLoading(false);
    }
  }

  function hydrateFromDefinition(definition: WorkflowDefinition) {
    const normalizedNodes: WorkflowNode[] = (definition.nodes || []).map((n, idx) => ({
      ...n,
      config: n.config || {},
      position: n.position || { x: 140 + idx * 180, y: 160 },
      label: n.label ?? undefined,
    }));

    const normalizedEdges: WorkflowEdge[] = (definition.edges || []).map((e) => ({
      ...e,
      id: e.id || `${e.source}->${e.target}-${e.case || ''}`,
    }));

    setNodes(normalizedNodes);
    setEdges(normalizedEdges);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setConnectingFrom(null);
  }

  function addNode(type: WorkflowNodeType) {
    if (type === 'start' && nodeTypesInGraph.has('start')) return;
    if (type === 'end' && nodeTypesInGraph.has('end')) return;
    if (type === 'llm' && nodeTypesInGraph.has('llm')) return;

    const id = createId(type);
    const newNode: WorkflowNode = {
      id,
      type,
      label: type.toUpperCase(),
      config:
        type === 'context'
          ? { enableHistory: true, enableKnowledgeBase: true }
          : type === 'router'
            ? { strategy: 'field', field: 'mode' }
            : {},
      position: { x: 200, y: 160 + nodes.length * 80 },
    };
    setNodes((prev) => [...prev, newNode]);
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
  }

  function removeSelected() {
    if (selectedEdgeId) {
      setEdges((prev) => prev.filter((e) => (e.id || '') !== selectedEdgeId));
      setSelectedEdgeId(null);
      return;
    }
    if (selectedNodeId) {
      setNodes((prev) => prev.filter((n) => n.id !== selectedNodeId));
      setEdges((prev) => prev.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
      setSelectedNodeId(null);
      setConnectingFrom(null);
    }
  }

  function beginConnectFrom(nodeId: string) {
    setConnectingFrom(nodeId);
    setSelectedEdgeId(null);
  }

  function connect(sourceId: string, targetId: string) {
    const source = nodesById.get(sourceId);
    if (!source) return;

    const isRouter = source.type === 'router';
    const newEdge: WorkflowEdge = {
      id: createId('edge'),
      source: sourceId,
      target: targetId,
      case: isRouter ? `case${(edges.filter((e) => e.source === sourceId).length || 0) + 1}` : undefined,
    };

    setEdges((prev) => {
      if (isRouter) return [...prev, newEdge];
      // 非 router：替换已有出边，保持“单出边”约束更直观
      const filtered = prev.filter((e) => e.source !== sourceId);
      return [...filtered, newEdge];
    });
  }

  function handleNodePointerDown(event: React.PointerEvent, nodeId: string) {
    event.stopPropagation();

    if (connectingFrom && connectingFrom !== nodeId) {
      connect(connectingFrom, nodeId);
      setConnectingFrom(null);
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      return;
    }

    const node = nodesById.get(nodeId);
    const canvas = canvasRef.current;
    if (!node || !canvas) return;

    setSelectedNodeId(nodeId);
    setSelectedEdgeId(null);

    const rect = canvas.getBoundingClientRect();
    const px = event.clientX - rect.left;
    const py = event.clientY - rect.top;
    const pos = node.position || { x: 0, y: 0 };

    draggingRef.current = {
      nodeId,
      offsetX: px - pos.x,
      offsetY: py - pos.y,
    };
  }

  function handleCanvasPointerDown() {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setConnectingFrom(null);
    draggingRef.current = null;
  }

  function updateNode(nodeId: string, patch: Partial<WorkflowNode>) {
    setNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, ...patch } : n)));
  }

  function updateEdge(edgeId: string, patch: Partial<WorkflowEdge>) {
    setEdges((prev) => prev.map((e) => ((e.id || '') === edgeId ? { ...e, ...patch } : e)));
  }

  async function handleSave() {
    if (!selectedWorkflowAgentId) return;
    if (!workflow) return;
    if (agent?.kind !== 'single') {
      alert('仅 single Agent 支持 workflow 编辑');
      return;
    }

    setSaving(true);
    try {
      const definition: WorkflowDefinition = {
        schemaVersion: workflow.definition.schemaVersion || 1,
        nodes,
        edges,
      };
      const updated = await updateAgentWorkflow(selectedWorkflowAgentId, definition);
      setWorkflow(updated);
      hydrateFromDefinition(updated.definition);
      alert('保存成功（已创建新版本并设为默认）');
    } catch (error) {
      alert('保存失败: ' + (error as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const selectedNode = selectedNodeId ? nodesById.get(selectedNodeId) || null : null;
  const selectedEdge = selectedEdgeId ? edges.find((e) => (e.id || '') === selectedEdgeId) || null : null;
  const selectedEdgeSource = selectedEdge ? nodesById.get(selectedEdge.source) || null : null;

  const edgePaths = useMemo(() => {
    return edges
      .map((edge) => {
        const source = nodesById.get(edge.source);
        const target = nodesById.get(edge.target);
        if (!source || !target) return null;
        const sp = source.position || { x: 0, y: 0 };
        const tp = target.position || { x: 0, y: 0 };
        const sx = sp.x + NODE_WIDTH / 2;
        const sy = sp.y + NODE_HEIGHT / 2;
        const tx = tp.x + NODE_WIDTH / 2;
        const ty = tp.y + NODE_HEIGHT / 2;
        const dx = Math.max(80, Math.abs(tx - sx));
        const c1x = sx + dx * 0.5 * (tx >= sx ? 1 : -1);
        const c2x = tx - dx * 0.5 * (tx >= sx ? 1 : -1);
        const d = `M ${sx} ${sy} C ${c1x} ${sy}, ${c2x} ${ty}, ${tx} ${ty}`;
        return { edge, d, mx: (sx + tx) / 2, my: (sy + ty) / 2 };
      })
      .filter(Boolean) as { edge: WorkflowEdge; d: string; mx: number; my: number }[];
  }, [edges, nodesById]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        加载中...
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
      <header className="flex items-center gap-4 px-8 py-6 border-b border-border/10 bg-surface/50 backdrop-blur-md z-10">
        <button
          onClick={backToAgents}
          className="p-2 rounded-xl hover:bg-surface-highlight/20 transition-all text-muted hover:text-foreground"
          title="Back"
          type="button"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold tracking-tight">Workflow Designer</h1>
          <p className="text-sm text-muted truncate">
            {agent ? `${agent.name} (${agent.kind})` : '未选择 Agent'}
            {workflow ? ` · 当前版本 ${workflow.workflowId}` : ''}
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving || agent?.kind !== 'single'}
          className={clsx(
            'inline-flex items-center gap-2 px-4 py-2 rounded-xl transition-all shadow-sm',
            saving || agent?.kind !== 'single'
              ? 'bg-surface-highlight text-muted cursor-not-allowed'
              : 'bg-primary text-white hover:bg-primary/90'
          )}
          type="button"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          保存
        </button>
      </header>

      <main className="flex-1 flex overflow-hidden">
        {/* Palette */}
        <aside className="w-64 border-r border-border/10 bg-surface/30 p-4 overflow-auto">
          <div className="text-xs font-black text-muted uppercase tracking-widest mb-3">Nodes</div>
          <div className="space-y-2">
            {(['start', 'router', 'context', 'llm', 'verify', 'end'] as WorkflowNodeType[]).map((t) => {
              const disabled =
                (t === 'start' && nodeTypesInGraph.has('start')) ||
                (t === 'end' && nodeTypesInGraph.has('end')) ||
                (t === 'llm' && nodeTypesInGraph.has('llm'));
              return (
                <button
                  key={t}
                  type="button"
                  disabled={disabled}
                  onClick={() => addNode(t)}
                  className={clsx(
                    'w-full text-left px-3 py-2 rounded-xl border transition-colors',
                    disabled
                      ? 'bg-surface-highlight/20 text-muted border-border/10 cursor-not-allowed'
                      : 'bg-surface/40 hover:bg-surface-highlight text-foreground border-border/20'
                  )}
                >
                  <div className="text-sm font-semibold">{t.toUpperCase()}</div>
                  <div className="text-xs text-muted mt-0.5">添加 {t} 节点</div>
                </button>
              );
            })}
          </div>

          <div className="mt-6 text-xs font-black text-muted uppercase tracking-widest mb-2">Tips</div>
          <div className="text-xs text-muted leading-relaxed">
            <div>1) 先放置 start / llm / end</div>
            <div>2) 选中节点后点击“连线”，再点目标节点</div>
            <div>3) router 支持多出边，需配置 case 标签</div>
          </div>
        </aside>

        {/* Canvas */}
        <section className="flex-1 relative bg-background overflow-hidden" ref={canvasRef} onPointerDown={handleCanvasPointerDown}>
          <svg className="absolute inset-0 w-full h-full">
            {edgePaths.map(({ edge, d, mx, my }) => {
              const isSelected = (edge.id || '') === selectedEdgeId;
              return (
                <g key={edge.id || `${edge.source}-${edge.target}-${edge.case || ''}`}>
                  <path d={d} stroke={isSelected ? 'rgb(99 102 241)' : 'rgba(148,163,184,0.35)'} strokeWidth={2} fill="none" />
                  <path
                    d={d}
                    stroke="transparent"
                    strokeWidth={12}
                    fill="none"
                    onPointerDown={(e) => {
                      e.stopPropagation();
                      setSelectedEdgeId(edge.id || '');
                      setSelectedNodeId(null);
                      setConnectingFrom(null);
                    }}
                    style={{ cursor: 'pointer' }}
                  />
                  {edge.case && (
                    <text x={mx} y={my - 6} textAnchor="middle" fontSize="11" fill="rgba(148,163,184,0.9)">
                      {edge.case}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {nodes.map((node) => {
            const pos = node.position || { x: 0, y: 0 };
            const selected = node.id === selectedNodeId;
            const connecting = connectingFrom === node.id;
            return (
              <div
                key={node.id}
                className={clsx(
                  'absolute rounded-2xl border px-3 py-2 select-none shadow-sm',
                  nodeColor(node.type),
                  selected ? 'ring-2 ring-primary/30' : 'ring-0',
                  connecting ? 'ring-2 ring-purple-500/30' : ''
                )}
                style={{
                  left: pos.x,
                  top: pos.y,
                  width: NODE_WIDTH,
                  height: NODE_HEIGHT,
                }}
                onPointerDown={(e) => handleNodePointerDown(e, node.id)}
              >
                <div className="text-xs font-black uppercase tracking-widest truncate">{node.type}</div>
                <div className="text-sm font-semibold truncate">{node.label || node.id}</div>
              </div>
            );
          })}
        </section>

        {/* Inspector */}
        <aside className="w-80 border-l border-border/10 bg-surface/30 p-4 overflow-auto">
          <div className="flex items-center justify-between">
            <div className="text-xs font-black text-muted uppercase tracking-widest">Inspector</div>
            <button
              type="button"
              onClick={removeSelected}
              disabled={!selectedNodeId && !selectedEdgeId}
              className={clsx(
                'inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border transition-colors text-sm',
                selectedNodeId || selectedEdgeId
                  ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/15'
                  : 'bg-surface-highlight/20 text-muted border-border/10 cursor-not-allowed'
              )}
            >
              <Trash2 className="w-4 h-4" />
              删除
            </button>
          </div>

          {selectedNode ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-xs font-semibold text-muted mb-1">节点</div>
                <div className="text-sm font-bold">{selectedNode.type}</div>
                <div className="text-xs text-muted break-all mt-1">{selectedNode.id}</div>
              </div>

              <div>
                <div className="text-xs font-semibold text-muted mb-1">Label</div>
                <input
                  className="w-full px-3 py-2 rounded-xl bg-surface/40 border border-border/20 outline-none focus:ring-2 focus:ring-primary/20 text-sm"
                  value={selectedNode.label || ''}
                  onChange={(e) => updateNode(selectedNode.id, { label: e.target.value })}
                />
              </div>

              {selectedNode.type === 'router' && (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-muted">Router 配置</div>
                  <div>
                    <div className="text-xs text-muted mb-1">strategy</div>
                    <select
                      className="w-full px-3 py-2 rounded-xl bg-surface/40 border border-border/20 outline-none focus:ring-2 focus:ring-primary/20 text-sm"
                      value={String(selectedNode.config?.strategy || 'field')}
                      onChange={(e) =>
                        updateNode(selectedNode.id, {
                          config: { ...(selectedNode.config || {}), strategy: e.target.value },
                        })
                      }
                    >
                      <option value="field">field</option>
                      <option value="llm">llm</option>
                    </select>
                  </div>
                  {String(selectedNode.config?.strategy || 'field') === 'field' ? (
                    <div>
                      <div className="text-xs text-muted mb-1">field</div>
                      <input
                        className="w-full px-3 py-2 rounded-xl bg-surface/40 border border-border/20 outline-none focus:ring-2 focus:ring-primary/20 text-sm"
                        value={String(selectedNode.config?.field || 'mode')}
                        onChange={(e) =>
                          updateNode(selectedNode.id, {
                            config: { ...(selectedNode.config || {}), field: e.target.value },
                          })
                        }
                      />
                    </div>
                  ) : (
                    <div>
                      <div className="text-xs text-muted mb-1">prompt</div>
                      <textarea
                        className="w-full px-3 py-2 rounded-xl bg-surface/40 border border-border/20 outline-none focus:ring-2 focus:ring-primary/20 text-sm h-28 resize-none"
                        value={String(selectedNode.config?.prompt || '')}
                        onChange={(e) =>
                          updateNode(selectedNode.id, {
                            config: { ...(selectedNode.config || {}), prompt: e.target.value },
                          })
                        }
                      />
                    </div>
                  )}
                  <div>
                    <div className="text-xs text-muted mb-1">defaultCase</div>
                    <input
                      className="w-full px-3 py-2 rounded-xl bg-surface/40 border border-border/20 outline-none focus:ring-2 focus:ring-primary/20 text-sm"
                      value={String(selectedNode.config?.defaultCase || '')}
                      onChange={(e) =>
                        updateNode(selectedNode.id, {
                          config: { ...(selectedNode.config || {}), defaultCase: e.target.value },
                        })
                      }
                    />
                  </div>
                </div>
              )}

              {selectedNode.type === 'context' && (
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-muted">Context 配置</div>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(selectedNode.config?.enableHistory ?? true)}
                      onChange={(e) =>
                        updateNode(selectedNode.id, {
                          config: { ...(selectedNode.config || {}), enableHistory: e.target.checked },
                        })
                      }
                    />
                    <span>启用历史检索</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(selectedNode.config?.enableKnowledgeBase ?? true)}
                      onChange={(e) =>
                        updateNode(selectedNode.id, {
                          config: { ...(selectedNode.config || {}), enableKnowledgeBase: e.target.checked },
                        })
                      }
                    />
                    <span>启用知识库检索</span>
                  </label>
                </div>
              )}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => beginConnectFrom(selectedNode.id)}
                  className={clsx(
                    'inline-flex items-center gap-2 px-3 py-2 rounded-xl border transition-colors text-sm',
                    connectingFrom === selectedNode.id
                      ? 'bg-purple-500/10 text-purple-300 border-purple-500/20'
                      : 'bg-surface/40 hover:bg-surface-highlight text-foreground border-border/20'
                  )}
                >
                  <Link2 className="w-4 h-4" />
                  连线
                </button>
                {connectingFrom && (
                  <div className="text-xs text-muted truncate">
                    从 <span className="font-semibold">{connectingFrom}</span> 连接到...
                  </div>
                )}
              </div>
            </div>
          ) : selectedEdge ? (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-xs font-semibold text-muted mb-1">边</div>
                <div className="text-xs text-muted break-all">
                  {selectedEdge.source} → {selectedEdge.target}
                </div>
              </div>
              {selectedEdgeSource?.type === 'router' ? (
                <div>
                  <div className="text-xs font-semibold text-muted mb-1">case</div>
                  <input
                    className="w-full px-3 py-2 rounded-xl bg-surface/40 border border-border/20 outline-none focus:ring-2 focus:ring-primary/20 text-sm"
                    value={selectedEdge.case || ''}
                    onChange={(e) => updateEdge(selectedEdge.id || '', { case: e.target.value })}
                  />
                  <div className="text-xs text-muted mt-1">router 出边必须设置唯一 case</div>
                </div>
              ) : (
                <div className="text-xs text-muted">非 router 出边不支持 case</div>
              )}
            </div>
          ) : (
            <div className="mt-4 text-sm text-muted leading-relaxed">
              选择节点或边以编辑属性。
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

