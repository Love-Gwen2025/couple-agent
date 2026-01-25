/**
 * Tools 管理页面
 *
 * - 统一工具目录（内置 + MCP）
 * - MCP Server 管理
 * - MCP Tool 启用/禁用与测试调用
 */
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Edit2, Loader2, Plus, RefreshCw, TestTube, Trash2, Wrench } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import clsx from 'clsx';
import { useNavigationStore } from '../../store';
import {
  createMcpServer,
  deleteMcpServer,
  listMcpServers,
  listMcpTools,
  listTools,
  syncMcpTools,
  testMcpTool,
  updateMcpServer,
  updateMcpToolEnabled,
} from '../../api';
import type { McpServer, McpServerPayload, McpTool, ToolItem } from '../../types';

function safeJsonParse(input: string): unknown {
  if (!input.trim()) return {};
  return JSON.parse(input);
}

export function ToolsPage() {
  const { setCurrentPage } = useNavigationStore();

  const [toolDirectory, setToolDirectory] = useState<ToolItem[]>([]);
  const [servers, setServers] = useState<McpServer[]>([]);
  const [mcpTools, setMcpTools] = useState<McpTool[]>([]);

  const [loading, setLoading] = useState(true);

  const [showServerModal, setShowServerModal] = useState(false);
  const [editingServer, setEditingServer] = useState<McpServer | null>(null);

  const [showTestModal, setShowTestModal] = useState(false);
  const [testingTool, setTestingTool] = useState<McpTool | null>(null);

  const serverNameById = useMemo(() => {
    const map = new Map<string, string>();
    servers.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [servers]);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [dir, srv, tools] = await Promise.all([listTools(), listMcpServers(), listMcpTools()]);
      setToolDirectory(dir);
      setServers(srv);
      setMcpTools(tools);
    } catch (error) {
      console.error('Failed to load tools:', error);
    } finally {
      setLoading(false);
    }
  }

  async function openCreateServer() {
    setEditingServer(null);
    setShowServerModal(true);
  }

  async function openEditServer(server: McpServer) {
    setEditingServer(server);
    setShowServerModal(true);
  }

  async function handleDeleteServer(serverId: string) {
    if (!confirm('确定要删除这个 MCP Server 吗？')) return;
    try {
      await deleteMcpServer(serverId);
      await loadAll();
    } catch (error) {
      alert('删除失败: ' + (error as Error).message);
    }
  }

  async function handleSync(serverId: string) {
    try {
      await syncMcpTools(serverId);
      await loadAll();
    } catch (error) {
      alert('同步失败: ' + (error as Error).message);
    }
  }

  async function handleToggleTool(tool: McpTool) {
    try {
      await updateMcpToolEnabled(tool.id, !tool.enabled);
      await loadAll();
    } catch (error) {
      alert('更新失败: ' + (error as Error).message);
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
            <Wrench className="w-5 h-5 text-primary" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-tight">Tools</h1>
            <p className="text-sm text-muted">内置工具与 MCP 工具同层级管理；MCP 仅支持 HTTP(S)</p>
          </div>
        </div>

        <button
          onClick={openCreateServer}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary/90 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          新建 MCP Server
        </button>
      </header>

      <main className="flex-1 overflow-auto p-8 space-y-8">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            加载中...
          </div>
        ) : (
          <>
            {/* Tool Directory */}
            <section className="space-y-3">
              <h2 className="text-sm font-bold tracking-widest uppercase text-muted">Tool Directory</h2>
              <div className="rounded-2xl border border-border/10 bg-surface/30 overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-surface/40 border-b border-border/10">
                    <tr>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Display</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">ToolRef</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Type</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted text-center uppercase tracking-widest">Enabled</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/5">
                    {toolDirectory.map((t) => (
                      <tr key={t.toolRef} className="hover:bg-surface-highlight/5 transition-colors">
                        <td className="px-6 py-5">
                          <div className="font-semibold text-foreground">{t.displayName || t.name}</div>
                          {t.description && <div className="text-xs text-muted mt-1 line-clamp-1">{t.description}</div>}
                        </td>
                        <td className="px-6 py-5">
                          <code className="text-[11px] text-muted bg-surface/40 px-2 py-1 rounded-md border border-border/10">
                            {t.toolRef}
                          </code>
                        </td>
                        <td className="px-6 py-5">
                          <span className="px-3 py-1 text-[10px] font-black rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 uppercase tracking-widest">
                            {t.type.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-5 text-center">
                          <span
                            className={clsx(
                              'px-2.5 py-1 text-[10px] font-black rounded-full uppercase tracking-widest border',
                              t.enabled
                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : 'bg-surface-highlight/10 text-muted border-border/10'
                            )}
                          >
                            {t.enabled ? 'YES' : 'NO'}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {toolDirectory.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-12 text-center text-muted font-medium">
                          暂无工具
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* MCP Servers */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold tracking-widest uppercase text-muted">MCP Servers</h2>
                <button
                  onClick={loadAll}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-border/20 bg-surface/40 text-muted hover:text-foreground hover:bg-surface-highlight/10 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  刷新
                </button>
              </div>
              <div className="rounded-2xl border border-border/10 bg-surface/30 overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-surface/40 border-b border-border/10">
                    <tr>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Name</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">URL</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted text-center uppercase tracking-widest">Status</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted text-right uppercase tracking-widest">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/5">
                    {servers.map((s) => (
                      <tr key={s.id} className="hover:bg-surface-highlight/5 transition-colors">
                        <td className="px-6 py-5">
                          <div className="font-semibold text-foreground">{s.name}</div>
                          {s.hasHeaders && <div className="text-xs text-muted mt-1">已配置 headers</div>}
                        </td>
                        <td className="px-6 py-5">
                          <code className="text-[11px] text-muted bg-surface/40 px-2 py-1 rounded-md border border-border/10">
                            {s.url}
                          </code>
                        </td>
                        <td className="px-6 py-5 text-center">
                          <span
                            className={clsx(
                              'px-2.5 py-1 text-[10px] font-black rounded-full uppercase tracking-widest border',
                              s.status === 1
                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : 'bg-surface-highlight/10 text-muted border-border/10'
                            )}
                          >
                            {s.status === 1 ? 'ONLINE' : 'OFFLINE'}
                          </span>
                        </td>
                        <td className="px-6 py-5">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleSync(s.id)}
                              className="p-2 rounded-lg hover:bg-surface-highlight/20 transition-colors text-muted hover:text-foreground"
                              title="同步 tools"
                            >
                              <RefreshCw className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => openEditServer(s)}
                              className="p-2 rounded-lg hover:bg-surface-highlight/20 transition-colors text-muted hover:text-foreground"
                              title="编辑"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteServer(s.id)}
                              className="p-2 rounded-lg hover:bg-red-500/10 transition-colors text-muted hover:text-red-400"
                              title="删除"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {servers.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-12 text-center text-muted font-medium">
                          暂无 MCP Server。点击右上角新建。
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* MCP Tools */}
            <section className="space-y-3">
              <h2 className="text-sm font-bold tracking-widest uppercase text-muted">MCP Tools</h2>
              <div className="rounded-2xl border border-border/10 bg-surface/30 overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-surface/40 border-b border-border/10">
                    <tr>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Tool</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted uppercase tracking-widest">Server</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted text-center uppercase tracking-widest">Enabled</th>
                      <th className="px-6 py-4 text-[10px] font-black text-muted text-right uppercase tracking-widest">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/5">
                    {mcpTools.map((t) => (
                      <tr key={t.id} className="hover:bg-surface-highlight/5 transition-colors">
                        <td className="px-6 py-5">
                          <div className="font-semibold text-foreground">{t.name}</div>
                          {t.description && <div className="text-xs text-muted mt-1 line-clamp-1">{t.description}</div>}
                        </td>
                        <td className="px-6 py-5 text-sm text-muted">
                          {serverNameById.get(t.serverId) || t.serverId}
                        </td>
                        <td className="px-6 py-5 text-center">
                          <button
                            onClick={() => handleToggleTool(t)}
                            className={clsx(
                              'px-3 py-1 text-[10px] font-black rounded-full uppercase tracking-widest border transition-colors',
                              t.enabled
                                ? 'bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/15'
                                : 'bg-surface-highlight/10 text-muted border-border/10 hover:bg-surface-highlight/20'
                            )}
                            title="切换启用状态"
                          >
                            {t.enabled ? 'ON' : 'OFF'}
                          </button>
                        </td>
                        <td className="px-6 py-5">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                setTestingTool(t);
                                setShowTestModal(true);
                              }}
                              className="p-2 rounded-lg hover:bg-surface-highlight/20 transition-colors text-muted hover:text-foreground"
                              title="测试调用"
                            >
                              <TestTube className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {mcpTools.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-12 text-center text-muted font-medium">
                          暂无 MCP Tools。先创建 Server 并同步。
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </main>

      <AnimatePresence>
        {showServerModal && (
          <McpServerModal
            server={editingServer}
            onClose={() => {
              setShowServerModal(false);
              setEditingServer(null);
            }}
            onSaved={async () => {
              setShowServerModal(false);
              setEditingServer(null);
              await loadAll();
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showTestModal && testingTool && (
          <McpToolTestModal
            tool={testingTool}
            serverName={serverNameById.get(testingTool.serverId) || testingTool.serverId}
            onClose={() => {
              setShowTestModal(false);
              setTestingTool(null);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function McpServerModal({
  server,
  onClose,
  onSaved,
}: {
  server: McpServer | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const isEdit = !!server;

  const [loading, setLoading] = useState(false);
  const [name, setName] = useState(server?.name || '');
  const [url, setUrl] = useState(server?.url || '');
  const [status, setStatus] = useState(server?.status ?? 1);
  const [headersJson, setHeadersJson] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !url.trim()) {
      alert('请填写 name 与 url');
      return;
    }

    let headers: Record<string, string> | undefined = undefined;
    if (headersJson.trim()) {
      try {
        const parsed = safeJsonParse(headersJson);
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          throw new Error('headers 必须是 JSON object');
        }
        headers = parsed as Record<string, string>;
      } catch (error) {
        alert('headers JSON 解析失败: ' + (error as Error).message);
        return;
      }
    }

    setLoading(true);
    try {
      const payload: McpServerPayload = {
        name: name.trim(),
        url: url.trim(),
        status,
        headers,
      };
      if (isEdit && server) {
        await updateMcpServer(server.id, payload);
      } else {
        await createMcpServer(payload);
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
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-xl rounded-2xl border p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--background))' }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">{isEdit ? '编辑 MCP Server' : '新建 MCP Server'}</h2>
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all"
              style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
              placeholder="例如：my-mcp"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">URL（仅支持 http/https）</label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all"
              style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
              placeholder="http://127.0.0.1:9000/mcp"
            />
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
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">Headers（可选，JSON object）</label>
            <textarea
              value={headersJson}
              onChange={(e) => setHeadersJson(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all min-h-[100px]"
              style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
              placeholder='例如：{"Authorization":"Bearer xxx"}'
            />
          </div>

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

function McpToolTestModal({
  tool,
  serverName,
  onClose,
}: {
  tool: McpTool;
  serverName: string;
  onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [argumentsJson, setArgumentsJson] = useState('{}');
  const [resultText, setResultText] = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setResultText(null);
    try {
      const parsed = safeJsonParse(argumentsJson);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('arguments 必须是 JSON object');
      }
      const result = await testMcpTool(tool.id, { arguments: parsed as Record<string, unknown> });
      const text = result.text || (result.data ? JSON.stringify(result.data, null, 2) : '');
      setResultText(text || (result.success ? '调用成功' : '调用失败'));
    } catch (error) {
      setResultText('调用失败: ' + (error as Error).message);
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
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-2xl rounded-2xl border p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--background))' }}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold">测试 MCP Tool</h2>
            <div className="text-sm text-muted mt-1">
              {serverName} · {tool.name} · id={tool.id}
            </div>
          </div>
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

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted">Arguments（JSON object）</label>
            <textarea
              value={argumentsJson}
              onChange={(e) => setArgumentsJson(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border bg-surface text-foreground focus:outline-none focus:border-primary transition-all min-h-[120px] font-mono text-sm"
              style={{ borderColor: 'rgb(var(--border) / 0.5)' }}
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleRun}
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary/90 transition-all shadow-sm disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
              运行
            </button>
          </div>

          {resultText !== null && (
            <pre className="whitespace-pre-wrap text-sm bg-surface/40 border border-border/20 rounded-xl p-4 max-h-64 overflow-auto custom-scrollbar">
              {resultText}
            </pre>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

