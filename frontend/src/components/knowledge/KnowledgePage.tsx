/**
 * 知识库列表页组件
 *
 * 以表格形式展示所有知识库，支持创建、删除和进入详情
 */
import { useState, useEffect } from 'react';
import { ArrowLeft, Plus, Database, Trash2, TestTube, Loader2, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigationStore } from '../../store';
import {
    getKnowledgeBases,
    createKnowledgeBase,
    deleteKnowledgeBase,
    type KnowledgeBase,
} from '../../api/knowledge';
import { RecallTestModal } from '.';
import { Pagination } from '../common/Pagination';

/** 格式化时间 */
function formatTime(isoString: string | null): string {
    if (!isoString) return '-';
    return new Date(isoString).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export function KnowledgePage() {
    // 导航状态
    const { setCurrentPage, openKnowledgeDetail } = useNavigationStore();
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isCreating, setIsCreating] = useState(false);
    const [newKbName, setNewKbName] = useState('');
    const [newKbDesc, setNewKbDesc] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    // 分页状态
    const [pagination, setPagination] = useState({ current: 1, size: 10, total: 0, pages: 0 });

    // 召回测试弹窗状态
    const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
    const [isRecallModalOpen, setIsRecallModalOpen] = useState(false);

    useEffect(() => {
        loadKnowledgeBases();
    }, []);

    async function loadKnowledgeBases(page: number = 1) {
        setIsLoading(true);
        try {
            const pageData = await getKnowledgeBases(page, pagination.size);
            setKnowledgeBases(pageData?.records || []);
            setPagination({
                current: pageData?.current || 1,
                size: pageData?.size || 10,
                total: pageData?.total || 0,
                pages: pageData?.pages || 0,
            });
        } catch (error) {
            console.error('Failed to load knowledge bases:', error);
        } finally {
            setIsLoading(false);
        }
    }

    // 处理页码变化
    function handlePageChange(page: number) {
        loadKnowledgeBases(page);
    }

    async function handleCreate() {
        if (!newKbName.trim()) return;
        setIsCreating(true);
        try {
            await createKnowledgeBase(newKbName.trim(), newKbDesc.trim() || undefined);
            setNewKbName('');
            setNewKbDesc('');
            setShowCreateModal(false);
            loadKnowledgeBases();
        } catch (error) {
            console.error('Failed to create knowledge base:', error);
        } finally {
            setIsCreating(false);
        }
    }

    async function handleDelete(id: string, e: React.MouseEvent) {
        e.stopPropagation();
        if (!confirm('确定要删除这个知识库吗？所有文档都将被删除且不可恢复。')) return;
        try {
            await deleteKnowledgeBase(id);
            setKnowledgeBases(knowledgeBases.filter((kb) => kb.id !== id));
        } catch (error) {
            console.error('Failed to delete knowledge base:', error);
        }
    }

    // 过滤知识库
    const filteredKbs = knowledgeBases.filter(kb =>
        kb.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (kb.description && kb.description.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <div className="h-screen flex flex-col" style={{ backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}>
            {/* 顶部导航栏 */}
            <header className="flex items-center gap-4 px-6 py-4 border-b" style={{ borderColor: 'rgb(var(--border) / 0.2)', backgroundColor: 'rgb(var(--surface-container))' }}>
                <button
                    onClick={() => setCurrentPage('chat')}
                    className="p-2 rounded-lg transition-colors"
                    style={{ backgroundColor: 'transparent' }}
                    onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgb(var(--surface-container-high))'}
                    onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <div className="flex-1">
                    <h1 className="text-xl font-bold">知识库</h1>
                    <p className="text-sm text-muted">管理您的知识库和文档</p>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    新建知识库
                </button>
            </header>

            {/* 内容区域 */}
            <main className="flex-1 overflow-auto p-6">
                {/* 搜索栏 */}
                <div className="mb-4">
                    <div className="relative max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                        <input
                            type="text"
                            placeholder="搜索知识库..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 rounded-xl border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                            style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--surface))' }}
                        />
                    </div>
                </div>

                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                ) : filteredKbs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 text-muted space-y-4">
                        <div className="p-6 rounded-full" style={{ backgroundColor: 'rgb(var(--surface-container-high))' }}>
                            <Database className="w-12 h-12" />
                        </div>
                        <p className="text-lg font-medium">
                            {knowledgeBases.length === 0 ? '暂无知识库' : '没有匹配的知识库'}
                        </p>
                        {knowledgeBases.length === 0 && (
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="text-primary hover:underline font-medium"
                            >
                                创建您的第一个知识库
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="rounded-2xl border overflow-hidden" style={{ borderColor: 'rgb(var(--border) / 0.2)' }}>
                        <table className="w-full">
                            <thead>
                                <tr style={{ backgroundColor: 'rgb(var(--surface-container))' }}>
                                    <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">知识库名称</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">简介</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">文档数</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">切片数</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">创建时间</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                <AnimatePresence>
                                    {filteredKbs.map((kb) => (
                                        <motion.tr
                                            key={kb.id}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            className="border-t cursor-pointer transition-colors"
                                            style={{ borderColor: 'rgb(var(--border) / 0.1)' }}
                                            onClick={() => openKnowledgeDetail(kb.id)}
                                            onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgb(var(--surface-container-high) / 0.5)')}
                                            onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
                                        >
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-3">
                                                    <div className="p-2 bg-purple-500/10 rounded-lg">
                                                        <Database className="w-4 h-4 text-purple-500" />
                                                    </div>
                                                    <span className="font-medium">{kb.name}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-muted max-w-[200px] truncate">
                                                {kb.description || '-'}
                                            </td>
                                            <td className="px-4 py-3 text-sm">{kb.documentCount}</td>
                                            <td className="px-4 py-3 text-sm">{kb.chunkCount}</td>
                                            <td className="px-4 py-3 text-sm text-muted">{formatTime(kb.createTime)}</td>
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            setSelectedKb(kb);
                                                            setIsRecallModalOpen(true);
                                                        }}
                                                        className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-primary/10 transition-colors"
                                                        title="召回测试"
                                                    >
                                                        <TestTube className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={(e) => handleDelete(kb.id, e)}
                                                        className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                                                        title="删除"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </motion.tr>
                                    ))}
                                </AnimatePresence>
                            </tbody>
                        </table>
                        {/* 分页组件 */}
                        <Pagination
                            current={pagination.current}
                            size={pagination.size}
                            total={pagination.total}
                            pages={pagination.pages}
                            onChange={handlePageChange}
                        />
                    </div>
                )}
            </main>

            {/* 创建弹窗 */}
            <AnimatePresence>
                {showCreateModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="w-full max-w-md rounded-2xl border p-6 shadow-2xl"
                            style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--background))' }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h2 className="text-xl font-bold mb-4">新建知识库</h2>
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted">名称 *</label>
                                    <input
                                        type="text"
                                        value={newKbName}
                                        onChange={(e) => setNewKbName(e.target.value)}
                                        placeholder="例如：产品文档库"
                                        className="w-full px-4 py-2 rounded-xl border focus:outline-none focus:border-primary transition-colors"
                                        style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                        autoFocus
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-muted">简介</label>
                                    <textarea
                                        value={newKbDesc}
                                        onChange={(e) => setNewKbDesc(e.target.value)}
                                        placeholder="可选：描述知识库的用途"
                                        rows={3}
                                        className="w-full px-4 py-2 rounded-xl border focus:outline-none focus:border-primary transition-colors resize-none"
                                        style={{ borderColor: 'rgb(var(--border) / 0.5)', backgroundColor: 'rgb(var(--surface))' }}
                                    />
                                </div>
                                <div className="flex justify-end gap-3 pt-2">
                                    <button
                                        onClick={() => setShowCreateModal(false)}
                                        className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                                        style={{ backgroundColor: 'rgb(var(--surface-container-high))' }}
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleCreate}
                                        disabled={isCreating || !newKbName.trim()}
                                        className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {isCreating && <Loader2 className="w-4 h-4 animate-spin" />}
                                        创建
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 召回测试弹窗 */}
            <RecallTestModal
                isOpen={isRecallModalOpen}
                onClose={() => setIsRecallModalOpen(false)}
                knowledgeBase={selectedKb}
            />
        </div>
    );
}
