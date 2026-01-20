/**
 * 知识库详情弹窗
 *
 * 显示知识库详情、文档列表、上传文档
 */
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X,
    Upload,
    FileText,
    File,
    Trash2,
    Loader2,
    CheckCircle,
    XCircle,
    Clock,
    RefreshCw,
} from 'lucide-react';
import clsx from 'clsx';
import {
    getDocuments,
    uploadDocument,
    deleteDocument,
    type KnowledgeBase,
    type Document,
} from '../../api/knowledge';

interface KnowledgeDetailModalProps {
    isOpen: boolean;
    onClose: () => void;
    knowledgeBase: KnowledgeBase | null;
}

// 文件类型图标
function FileIcon({ fileType }: { fileType: string | null }) {
    const iconClass = 'w-8 h-8';
    switch (fileType) {
        case 'pdf':
            return <File className={clsx(iconClass, 'text-red-400')} />;
        case 'docx':
        case 'doc':
            return <FileText className={clsx(iconClass, 'text-blue-400')} />;
        case 'txt':
            return <FileText className={clsx(iconClass, 'text-gray-400')} />;
        default:
            return <File className={clsx(iconClass, 'text-muted')} />;
    }
}

// 状态标签
function StatusBadge({ status }: { status: string }) {
    const config = {
        pending: { icon: Clock, color: 'text-yellow-400 bg-yellow-400/10', label: '待处理' },
        processing: { icon: RefreshCw, color: 'text-blue-400 bg-blue-400/10', label: '处理中' },
        done: { icon: CheckCircle, color: 'text-green-400 bg-green-400/10', label: '完成' },
        failed: { icon: XCircle, color: 'text-red-400 bg-red-400/10', label: '失败' },
    }[status] || { icon: Clock, color: 'text-muted bg-muted/10', label: status };

    const Icon = config.icon;

    return (
        <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs', config.color)}>
            <Icon className={clsx('w-3 h-3', status === 'processing' && 'animate-spin')} />
            {config.label}
        </span>
    );
}

export function KnowledgeDetailModal({
    isOpen,
    onClose,
    knowledgeBase,
}: KnowledgeDetailModalProps) {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState<string | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);

    // 加载文档列表
    useEffect(() => {
        if (isOpen && knowledgeBase) {
            loadDocuments();
        }
    }, [isOpen, knowledgeBase?.id]);

    async function loadDocuments() {
        if (!knowledgeBase) return;
        setIsLoading(true);
        try {
            const docsPage = await getDocuments(knowledgeBase.id);
            setDocuments(docsPage?.records || []);
        } catch (error) {
            console.error('Failed to load documents:', error);
        } finally {
            setIsLoading(false);
        }
    }

    // 上传文件
    async function handleUpload(files: FileList | null) {
        if (!files || files.length === 0 || !knowledgeBase) return;

        setIsUploading(true);
        const totalFiles = files.length;
        let successCount = 0;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            setUploadProgress(`正在上传 ${i + 1}/${totalFiles}: ${file.name}`);

            try {
                const doc = await uploadDocument(knowledgeBase.id, file);
                setDocuments((prev) => [doc, ...prev]);
                successCount++;
            } catch (error) {
                console.error(`Failed to upload ${file.name}:`, error);
            }
        }

        setUploadProgress(null);
        setIsUploading(false);
        alert(`上传完成：${successCount}/${totalFiles} 个文件成功`);
    }

    // 删除文档
    async function handleDeleteDocument(docId: string) {
        if (!knowledgeBase) return;
        if (!confirm('确定要删除这个文档吗？')) return;

        try {
            await deleteDocument(knowledgeBase.id, docId);
            setDocuments(documents.filter((d) => d.id !== docId));
        } catch (error) {
            console.error('Failed to delete document:', error);
        }
    }

    // 拖拽处理
    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        handleUpload(e.dataTransfer.files);
    }, [knowledgeBase]);

    // 格式化文件大小
    function formatFileSize(bytes: number | null): string {
        if (bytes === null) return '-';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }

    if (!isOpen || !knowledgeBase) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full max-w-3xl max-h-[80vh] bg-surface-container rounded-3xl shadow-2xl overflow-hidden flex flex-col"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-border/50">
                        <div>
                            <h2 className="text-xl font-bold text-foreground">{knowledgeBase.name}</h2>
                            <p className="text-sm text-muted">
                                {knowledgeBase.documentCount} 文档 · {knowledgeBase.chunkCount} 分块
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-surface-container-high rounded-full transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Upload Area */}
                    <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={isUploading ? undefined : handleDrop}
                        className={clsx(
                            'mx-6 mt-4 p-6 border-2 border-dashed rounded-2xl transition-all',
                            isUploading
                                ? 'border-muted bg-muted/10 cursor-not-allowed'
                                : isDragOver
                                    ? 'border-primary bg-primary/10'
                                    : 'border-border/50 hover:border-primary/50'
                        )}
                    >
                        <div className="flex flex-col items-center gap-3">
                            <Upload className={clsx('w-10 h-10', isDragOver ? 'text-primary' : 'text-muted')} />
                            <div className="text-center">
                                <p className="text-sm text-foreground">
                                    拖拽文件到这里，或{' '}
                                    <label className="text-primary cursor-pointer hover:underline">
                                        点击上传
                                        <input
                                            type="file"
                                            multiple
                                            accept=".pdf,.docx,.doc,.txt"
                                            onChange={(e) => handleUpload(e.target.files)}
                                            className="hidden"
                                        />
                                    </label>
                                </p>
                                <p className="text-xs text-muted mt-1">支持 PDF、Word、TXT 格式</p>
                            </div>
                            {uploadProgress && (
                                <div className="flex items-center gap-2 text-sm text-primary">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    {uploadProgress}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Document List */}
                    <div className="flex-1 overflow-y-auto px-6 py-4">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 animate-spin text-muted" />
                            </div>
                        ) : documents.length === 0 ? (
                            <div className="text-center py-8 text-muted">暂无文档，请上传</div>
                        ) : (
                            <div className="space-y-2">
                                {documents.map((doc) => (
                                    <motion.div
                                        key={doc.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="flex items-center gap-4 p-4 bg-surface-container-high/50 rounded-xl group hover:bg-surface-container-high transition-colors"
                                    >
                                        <FileIcon fileType={doc.fileType} />
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium text-foreground truncate">{doc.fileName}</div>
                                            <div className="text-sm text-muted">
                                                {formatFileSize(doc.fileSize)} · {doc.chunkCount} 分块
                                            </div>
                                        </div>
                                        <StatusBadge status={doc.status} />
                                        <button
                                            onClick={() => handleDeleteDocument(doc.id)}
                                            className="opacity-0 group-hover:opacity-100 p-2 hover:bg-red-500/20 rounded-full text-muted hover:text-red-400 transition-all"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4 border-t border-border/50 flex justify-end gap-3">
                        <button
                            onClick={loadDocuments}
                            className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors"
                        >
                            <RefreshCw className="w-4 h-4 inline mr-1" />
                            刷新
                        </button>
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm bg-primary/20 hover:bg-primary/30 text-primary rounded-lg transition-colors"
                        >
                            关闭
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
