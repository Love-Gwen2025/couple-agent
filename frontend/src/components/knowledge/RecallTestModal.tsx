/**
 * 召回测试弹窗
 *
 * 提供知识库检索测试功能
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, Loader2, FileText, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import {
    recallTest,
    type KnowledgeBase,
    type RecallResult,
    type RecallTestParams,
} from '../../api/knowledge';

interface RecallTestModalProps {
    isOpen: boolean;
    onClose: () => void;
    knowledgeBase: KnowledgeBase | null;
}

export function RecallTestModal({
    isOpen,
    onClose,
    knowledgeBase,
}: RecallTestModalProps) {
    const [query, setQuery] = useState('');
    const [mode, setMode] = useState<'vector' | 'union' | 'intersection'>('union');
    const [topK, setTopK] = useState(5);
    const [threshold, setThreshold] = useState(0.5);
    const [results, setResults] = useState<RecallResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);

    // 执行检索
    async function handleSearch() {
        if (!query.trim() || !knowledgeBase) return;

        setIsSearching(true);
        setHasSearched(true);
        try {
            const params: RecallTestParams = { query, mode, topK, threshold };
            const res = await recallTest(knowledgeBase.id, params);
            setResults(res);
        } catch (error) {
            console.error('Recall test failed:', error);
            setResults([]);
        } finally {
            setIsSearching(false);
        }
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
                    className="w-full max-w-4xl max-h-[85vh] bg-surface-container rounded-3xl shadow-2xl overflow-hidden flex flex-col"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-border/50">
                        <div className="flex items-center gap-3">
                            <Sparkles className="w-6 h-6 text-cyan-400" />
                            <div>
                                <h2 className="text-xl font-bold text-foreground">召回测试</h2>
                                <p className="text-sm text-muted">{knowledgeBase.name}</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-surface-container-high rounded-full transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Search Area */}
                    <div className="px-6 py-4 border-b border-border/50 space-y-4">
                        {/* Query Input */}
                        <div className="flex gap-3">
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                placeholder="输入测试查询..."
                                className="flex-1 bg-surface-container-high/50 text-foreground px-4 py-3 rounded-xl outline-none border border-border/50 focus:border-primary/50"
                            />
                            <button
                                onClick={handleSearch}
                                disabled={isSearching || !query.trim()}
                                className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isSearching ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Search className="w-5 h-5" />
                                )}
                                检索
                            </button>
                        </div>

                        {/* Parameters */}
                        <div className="flex flex-wrap gap-4">
                            {/* Mode */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-muted">检索模式:</span>
                                <select
                                    value={mode}
                                    onChange={(e) => setMode(e.target.value as typeof mode)}
                                    className="bg-surface-container-high/50 text-foreground text-sm px-3 py-1.5 rounded-lg border border-border/50"
                                >
                                    <option value="vector">纯向量</option>
                                    <option value="union">混合 (并集)</option>
                                    <option value="intersection">混合 (交集)</option>
                                </select>
                            </div>

                            {/* Top K */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-muted">Top K:</span>
                                <input
                                    type="number"
                                    value={topK}
                                    onChange={(e) => setTopK(Number(e.target.value))}
                                    min={1}
                                    max={20}
                                    className="w-16 bg-surface-container-high/50 text-foreground text-sm px-3 py-1.5 rounded-lg border border-border/50"
                                />
                            </div>

                            {/* Threshold */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-muted">阈值:</span>
                                <input
                                    type="number"
                                    value={threshold}
                                    onChange={(e) => setThreshold(Number(e.target.value))}
                                    min={0}
                                    max={1}
                                    step={0.1}
                                    className="w-20 bg-surface-container-high/50 text-foreground text-sm px-3 py-1.5 rounded-lg border border-border/50"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Results Area */}
                    <div className="flex-1 overflow-y-auto px-6 py-4">
                        {isSearching ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
                            </div>
                        ) : !hasSearched ? (
                            <div className="text-center py-12 text-muted">
                                输入查询并点击检索按钮开始测试
                            </div>
                        ) : results.length === 0 ? (
                            <div className="text-center py-12 text-muted">未找到匹配的内容</div>
                        ) : (
                            <div className="space-y-4">
                                {results.map((result, index) => (
                                    <motion.div
                                        key={index}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="p-4 bg-surface-container-high/50 rounded-xl border border-border/30"
                                    >
                                        {/* Header */}
                                        <div className="flex items-center justify-between mb-3">
                                            <div className="flex items-center gap-2">
                                                <FileText className="w-4 h-4 text-cyan-400" />
                                                <span className="text-sm font-medium text-foreground">
                                                    {result.fileName || '未知文件'}
                                                </span>
                                                <span className="text-xs text-muted">#{result.chunkIndex}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-muted">相似度</span>
                                                <span
                                                    className={clsx(
                                                        'px-2 py-0.5 rounded-full text-sm font-medium',
                                                        result.similarity >= 0.8
                                                            ? 'bg-green-500/20 text-green-400'
                                                            : result.similarity >= 0.6
                                                                ? 'bg-yellow-500/20 text-yellow-400'
                                                                : 'bg-gray-500/20 text-gray-400'
                                                    )}
                                                >
                                                    {(result.similarity * 100).toFixed(1)}%
                                                </span>
                                            </div>
                                        </div>

                                        {/* Content */}
                                        <div className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">
                                            {result.content}
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
