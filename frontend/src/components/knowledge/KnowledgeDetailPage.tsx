/**
 * 知识库详情页组件
 *
 * 展示知识库的详细信息、统计数据和文档列表
 */
import { useState, useEffect } from 'react';
import { ArrowLeft, Upload, Trash2, Download, Loader2, FileText, Layers, CheckCircle, XCircle, Clock, Search, TestTube } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigationStore } from '../../store';
import {
    getKnowledgeBase,
    getDocuments,
    uploadDocument,
    deleteDocument,
    type KnowledgeBase,
    type Document,
} from '../../api/knowledge';
import { RecallTestModal } from '.';
import { Pagination } from '../common/Pagination';

/** 格式化文件大小 */
function formatFileSize(bytes: number | null): string {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

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

/** 状态标签组件 */
function StatusBadge({ status }: { status: string }) {
    const config: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
        done: { bg: 'bg-green-500/10', text: 'text-green-500', icon: <CheckCircle className="w-3 h-3" /> },
        pending: { bg: 'bg-yellow-500/10', text: 'text-yellow-500', icon: <Clock className="w-3 h-3" /> },
        processing: { bg: 'bg-blue-500/10', text: 'text-blue-500', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
        failed: { bg: 'bg-red-500/10', text: 'text-red-500', icon: <XCircle className="w-3 h-3" /> },
    };
    const { bg, text, icon } = config[status] || config.pending;

    return (
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${bg} ${text}`}>
            {icon}
            {status === 'done' ? '完成' : status === 'pending' ? '待处理' : status === 'processing' ? '处理中' : '失败'}
        </span>
    );
}

export function KnowledgeDetailPage() {
    // 导航状态
    const { selectedKnowledgeBaseId, setCurrentPage } = useNavigationStore();
    const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [isRecallModalOpen, setIsRecallModalOpen] = useState(false);

    // 分页状态
    const [pagination, setPagination] = useState({ current: 1, size: 10, total: 0, pages: 0 });

    // 加载知识库详情和文档列表
    useEffect(() => {
        if (selectedKnowledgeBaseId) {
            loadData();
        }
    }, [selectedKnowledgeBaseId]);

    async function loadData(page: number = 1) {
        if (!selectedKnowledgeBaseId) return;
        setIsLoading(true);
        try {
            const [kb, docsPage] = await Promise.all([
                getKnowledgeBase(selectedKnowledgeBaseId),
                getDocuments(selectedKnowledgeBaseId, page, pagination.size),
            ]);
            setKnowledgeBase(kb);
            setDocuments(docsPage?.records || []);
            setPagination({
                current: docsPage?.current || 1,
                size: docsPage?.size || 10,
                total: docsPage?.total || 0,
                pages: docsPage?.pages || 0,
            });
        } catch (error) {
            console.error('Failed to load knowledge base:', error);
        } finally {
            setIsLoading(false);
        }
    }

    // 处理页码变化
    function handlePageChange(page: number) {
        loadData(page);
    }

    // 上传文件
    async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file || !selectedKnowledgeBaseId) return;

        setIsUploading(true);
        try {
            await uploadDocument(selectedKnowledgeBaseId, file);
            loadData(); // 重新加载
        } catch (error) {
            console.error('Failed to upload document:', error);
        } finally {
            setIsUploading(false);
            e.target.value = ''; // 重置input
        }
    }

    // 删除文档
    async function handleDeleteDoc(docId: string) {
        if (!selectedKnowledgeBaseId) return;
        if (!confirm('确定要删除这个文档吗？相关的切片数据将被永久删除。')) return;

        try {
            await deleteDocument(selectedKnowledgeBaseId, docId);
            setDocuments(documents.filter(d => d.id !== docId));
        } catch (error) {
            console.error('Failed to delete document:', error);
        }
    }

    // 统计数据
    const stats = {
        totalDocs: documents.length,
        totalChunks: documents.reduce((sum, d) => sum + d.chunkCount, 0),
        completed: documents.filter(d => d.status === 'done').length,
        failed: documents.filter(d => d.status === 'failed').length,
    };

    // 过滤文档
    const filteredDocs = documents.filter(d =>
        d.fileName.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (isLoading) {
        return (
            <div className="h-screen flex items-center justify-center" style={{ backgroundColor: 'rgb(var(--background))' }}>
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col" style={{ backgroundColor: 'rgb(var(--background))', color: 'rgb(var(--foreground))' }}>
            {/* 顶部导航栏 */}
            <header className="flex items-center gap-4 px-6 py-4 border-b" style={{ borderColor: 'rgb(var(--border) / 0.2)', backgroundColor: 'rgb(var(--surface-container))' }}>
                <button
                    onClick={() => setCurrentPage('knowledge')}
                    className="p-2 rounded-lg transition-colors"
                    style={{ backgroundColor: 'transparent' }}
                    onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgb(var(--surface-container-high))'}
                    onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                    <ArrowLeft className="w-5 h-5" />
                </button>
                <div className="flex-1">
                    <h1 className="text-xl font-bold">{knowledgeBase?.name || '知识库详情'}</h1>
                    {knowledgeBase?.description && (
                        <p className="text-sm text-muted mt-0.5">{knowledgeBase.description}</p>
                    )}
                </div>
                <button
                    onClick={() => setIsRecallModalOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors"
                    style={{ borderColor: 'rgb(var(--border) / 0.3)' }}
                >
                    <TestTube className="w-4 h-4" />
                    召回测试
                </button>
            </header>

            {/* 统计卡片 */}
            <div className="grid grid-cols-4 gap-4 p-6">
                {[
                    { label: '文档总数', value: stats.totalDocs, icon: FileText, color: 'text-blue-500', bg: 'bg-blue-500/10' },
                    { label: '切片总数', value: stats.totalChunks, icon: Layers, color: 'text-purple-500', bg: 'bg-purple-500/10' },
                    { label: '处理完成', value: stats.completed, icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' },
                    { label: '处理失败', value: stats.failed, icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
                ].map((stat, i) => (
                    <div key={i} className="p-4 rounded-2xl border" style={{ borderColor: 'rgb(var(--border) / 0.2)', backgroundColor: 'rgb(var(--surface))' }}>
                        <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-xl ${stat.bg}`}>
                                <stat.icon className={`w-5 h-5 ${stat.color}`} />
                            </div>
                            <div>
                                <div className="text-2xl font-bold">{stat.value}</div>
                                <div className="text-xs text-muted uppercase tracking-wide">{stat.label}</div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* 文档列表 */}
            <div className="flex-1 px-6 pb-6 overflow-hidden flex flex-col">
                {/* 工具栏 */}
                <div className="flex items-center justify-between mb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                        <input
                            type="text"
                            placeholder="搜索文档..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10 pr-4 py-2 rounded-xl border text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary/20"
                            style={{ borderColor: 'rgb(var(--border) / 0.3)', backgroundColor: 'rgb(var(--surface))' }}
                        />
                    </div>
                    <label className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg cursor-pointer hover:bg-primary/90 transition-colors">
                        {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                        上传文件
                        <input type="file" accept=".pdf,.docx,.doc,.txt" onChange={handleUpload} className="hidden" disabled={isUploading} />
                    </label>
                </div>

                {/* 表格 */}
                <div className="flex-1 overflow-auto rounded-2xl border" style={{ borderColor: 'rgb(var(--border) / 0.2)' }}>
                    <table className="w-full">
                        <thead>
                            <tr style={{ backgroundColor: 'rgb(var(--surface-container))' }}>
                                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">文件名</th>
                                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">切片数</th>
                                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">文件大小</th>
                                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">状态</th>
                                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">创建时间</th>
                                <th className="text-left px-4 py-3 text-xs font-bold uppercase tracking-wider text-muted">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <AnimatePresence>
                                {filteredDocs.map((doc) => (
                                    <motion.tr
                                        key={doc.id}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="border-t"
                                        style={{ borderColor: 'rgb(var(--border) / 0.1)' }}
                                    >
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2">
                                                <FileText className="w-4 h-4 text-muted" />
                                                <span className="font-medium truncate max-w-[200px]">{doc.fileName}</span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-sm">{doc.chunkCount}</td>
                                        <td className="px-4 py-3 text-sm text-muted">{formatFileSize(doc.fileSize)}</td>
                                        <td className="px-4 py-3"><StatusBadge status={doc.status} /></td>
                                        <td className="px-4 py-3 text-sm text-muted">{formatTime(doc.createTime)}</td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2">
                                                <a
                                                    href={doc.fileUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-container-high transition-colors"
                                                    title="下载"
                                                >
                                                    <Download className="w-4 h-4" />
                                                </a>
                                                <button
                                                    onClick={() => handleDeleteDoc(doc.id)}
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
                            {filteredDocs.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="px-4 py-12 text-center text-muted">
                                        {documents.length === 0 ? '暂无文档，点击上方按钮上传' : '没有匹配的文档'}
                                    </td>
                                </tr>
                            )}
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
            </div>

            {/* 召回测试弹窗 */}
            <RecallTestModal
                isOpen={isRecallModalOpen}
                onClose={() => setIsRecallModalOpen(false)}
                knowledgeBase={knowledgeBase}
            />
        </div>
    );
}
