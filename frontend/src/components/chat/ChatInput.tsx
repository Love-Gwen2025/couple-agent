/**
 * 消息输入框组件 - Refined Modern Edition
 * 
 * 支持：
 * - 普通对话模式
 * - DeepSearch 深度搜索模式
 * - 知识库多选检索
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, StopCircle, Plus, Search, Database } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { getAllKnowledgeBases, type KnowledgeBase } from '../../api/knowledge';

interface ChatInputProps {
  isLoading?: boolean;
  disabled?: boolean;
  onSend: (content: string, mode?: string, knowledgeBaseIds?: string[]) => void;
  onAbort?: () => void;
}

export function ChatInput({
  isLoading,
  disabled,
  onSend,
  onAbort,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [isDeepSearch, setIsDeepSearch] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const knowledgeBasePanelRef = useRef<HTMLDivElement>(null);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKnowledgeBaseIds, setSelectedKnowledgeBaseIds] = useState<string[]>([]);
  const [isKnowledgeBaseOpen, setIsKnowledgeBaseOpen] = useState(false);
  const [isKnowledgeBaseLoading, setIsKnowledgeBaseLoading] = useState(false);
  const [knowledgeBaseError, setKnowledgeBaseError] = useState('');
  const [hasLoadedKnowledgeBases, setHasLoadedKnowledgeBases] = useState(false);

  /**
   * 加载知识库列表
   */
  const loadKnowledgeBases = useCallback(async () => {
    /*
     1. 如果正在加载，直接返回，避免并发请求。
     2. 拉取知识库列表并同步已选结果，避免使用已被删除的知识库。
     3. 记录加载成功或失败的状态，供界面提示使用。
    */
    if (isKnowledgeBaseLoading) {
      return;
    }
    setIsKnowledgeBaseLoading(true);
    setKnowledgeBaseError('');
    try {
      /*
       直接使用不分页接口获取全部知识库，减少前端分页逻辑复杂度。
      */
      const records = await getAllKnowledgeBases();
      const normalizedRecords = Array.isArray(records) ? records : [];
      setKnowledgeBases(normalizedRecords);
      setSelectedKnowledgeBaseIds((prev) =>
        prev.filter((id) => normalizedRecords.some((kb) => Object.is(kb.id, id)))
      );
      setHasLoadedKnowledgeBases(true);
    } catch (error) {
      setKnowledgeBaseError('知识库加载失败，请稍后重试');
    } finally {
      setIsKnowledgeBaseLoading(false);
    }
  }, [isKnowledgeBaseLoading]);

  useEffect(() => {
    /*
     根据输入内容自动调整文本框高度，提升输入体验。
    */
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    /*
     打开知识库下拉面板时，按需加载知识库列表。
    */
    if (!isKnowledgeBaseOpen) {
      return;
    }
    if (hasLoadedKnowledgeBases) {
      return;
    }
    loadKnowledgeBases();
  }, [isKnowledgeBaseOpen, hasLoadedKnowledgeBases, loadKnowledgeBases]);

  useEffect(() => {
    /*
     监听点击区域，点击面板外部时关闭下拉面板。
    */
    if (!isKnowledgeBaseOpen) {
      return;
    }
    const handleClickOutside = (event: MouseEvent) => {
      /*
       判断点击目标是否位于面板外部，外部点击则关闭面板。
      */
      const target = event.target as Node;
      const panel = knowledgeBasePanelRef.current;
      if (panel && !panel.contains(target)) {
        setIsKnowledgeBaseOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isKnowledgeBaseOpen]);

  const toggleKnowledgeBase = useCallback((kbId: string) => {
    /*
     如果当前知识库已选中则取消，否则追加到已选列表。
    */
    setSelectedKnowledgeBaseIds((prev) => {
      const exists = prev.some((id) => Object.is(id, kbId));
      if (exists) {
        return prev.filter((id) => !Object.is(id, kbId));
      }
      return [...prev, kbId];
    });
  }, []);

  const clearSelectedKnowledgeBases = useCallback(() => {
    /*
     清空已选知识库，下一次发送消息时将不进行检索。
    */
    setSelectedKnowledgeBaseIds([]);
  }, []);

  const handleSend = () => {
    /*
     1. 根据当前模式与知识库选择构建发送参数。
     2. 若未选择知识库，传入 undefined，确保后端不触发检索。
    */
    const content = input.trim();
    if (!content || isLoading || disabled) return;
    const mode = isDeepSearch ? 'deep_search' : 'chat';
    const knowledgeBaseIds =
      selectedKnowledgeBaseIds.length > 0 ? selectedKnowledgeBaseIds : undefined;
    onSend(content, mode, knowledgeBaseIds);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    /*
     处理回车发送逻辑，Shift + Enter 保持换行。
    */
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="shrink-0 p-6 pt-2 pb-10 bg-transparent relative z-10">
      <div className="max-w-4xl mx-auto relative group">
        {/* Outer Soft Glow */}
        <div className="absolute inset-x-4 -top-10 -bottom-4 bg-purple-500/5 blur-[100px] pointer-events-none opacity-0 group-focus-within:opacity-100 transition-opacity duration-1000" />

        <motion.div
          initial={false}
          animate={{
            y: isFocused ? -4 : 0,
            scale: isFocused ? 1.01 : 1
          }}
          className={clsx(
            'flex items-end gap-2 p-3 rounded-[32px] transition-all duration-500',
            'glass-premium dual-stroke shadow-premium',
            isFocused ? 'ring-1 ring-white/10' : 'ring-1 ring-white/5'
          )}
        >
          {/* Left Actions */}
          <button
            className="p-3 rounded-2xl hover:bg-white/[0.05] text-gray-400 hover:text-foreground transition-all active:scale-95"
          >
            <Plus className="w-5 h-5" />
          </button>

          {/* DeepSearch Toggle */}
          <button
            onClick={() => setIsDeepSearch(!isDeepSearch)}
            className={clsx(
              "p-3 rounded-2xl transition-all duration-300 active:scale-95",
              isDeepSearch
                ? "bg-purple-500/20 text-purple-400 ring-1 ring-purple-500/30"
                : "hover:bg-white/[0.05] text-gray-400 hover:text-foreground"
            )}
            title={isDeepSearch ? "深度搜索模式（已开启）" : "切换到深度搜索模式"}
            aria-label={isDeepSearch ? "关闭深度搜索模式" : "开启深度搜索模式"}
            aria-pressed={isDeepSearch}
          >
            <Search className="w-5 h-5" />
          </button>

          {/* 知识库选择面板（支持多选） */}
          <div className="relative" ref={knowledgeBasePanelRef}>
            <button
              onClick={() => setIsKnowledgeBaseOpen((prev) => !prev)}
              className={clsx(
                "flex items-center gap-2 p-3 rounded-2xl transition-all duration-300 active:scale-95",
                isKnowledgeBaseOpen
                  ? "bg-purple-500/20 text-purple-400 ring-1 ring-purple-500/30"
                  : "hover:bg-white/[0.05] text-gray-400 hover:text-foreground"
              )}
              aria-label="选择知识库"
              aria-expanded={isKnowledgeBaseOpen}
            >
              <Database className="w-5 h-5" />
              {selectedKnowledgeBaseIds.length > 0 && (
                <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-purple-500/30 text-purple-200">
                  {selectedKnowledgeBaseIds.length}
                </span>
              )}
            </button>
            {isKnowledgeBaseOpen && (
              <div className="absolute left-0 bottom-full mb-3 w-72 rounded-2xl border border-border/30 bg-surface/95 backdrop-blur-xl shadow-xl p-3 z-50">
                <div className="flex items-center justify-between pb-2 border-b border-border/20">
                  <span className="text-sm font-semibold text-foreground">知识库检索</span>
                  <button
                    onClick={clearSelectedKnowledgeBases}
                    className="text-xs text-muted hover:text-foreground transition-colors"
                  >
                    清空
                  </button>
                </div>
                <div className="max-h-56 overflow-y-auto py-2 space-y-1">
                  {isKnowledgeBaseLoading && (
                    <div className="text-xs text-muted px-2 py-3">正在加载知识库...</div>
                  )}
                  {!isKnowledgeBaseLoading && knowledgeBaseError && (
                    <div className="text-xs text-red-400 px-2 py-3">
                      <div>{knowledgeBaseError}</div>
                      <button
                        onClick={loadKnowledgeBases}
                        className="mt-2 text-xs text-purple-300 hover:text-purple-200 transition-colors"
                      >
                        重新加载
                      </button>
                    </div>
                  )}
                  {!isKnowledgeBaseLoading && !knowledgeBaseError && knowledgeBases.length === 0 && (
                    <div className="text-xs text-muted px-2 py-3">暂无可用知识库</div>
                  )}
                  {!isKnowledgeBaseLoading &&
                    !knowledgeBaseError &&
                    knowledgeBases.map((kb) => {
                      const isSelected = selectedKnowledgeBaseIds.some((id) =>
                        Object.is(id, kb.id)
                      );
                      return (
                        <button
                          key={kb.id}
                          onClick={() => toggleKnowledgeBase(kb.id)}
                          className={clsx(
                            "w-full flex items-center justify-between px-2 py-2 rounded-xl text-left transition-colors",
                            isSelected
                              ? "bg-purple-500/15 text-purple-100"
                              : "hover:bg-white/[0.05] text-foreground"
                          )}
                        >
                          <div className="flex flex-col">
                            <span className="text-sm font-medium">{kb.name}</span>
                            <span className="text-[11px] text-muted truncate">
                              {kb.description || '暂无描述'}
                            </span>
                          </div>
                          {isSelected && (
                            <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-500/30 text-purple-200">
                              已选
                            </span>
                          )}
                        </button>
                      );
                    })}
                </div>
                <div className="pt-2 border-t border-border/20 text-[11px] text-muted">
                  未选择知识库时将跳过检索
                </div>
              </div>
            )}
          </div>

          <textarea
            ref={textareaRef}
            className="flex-1 bg-transparent text-foreground resize-none outline-none py-3 px-2 max-h-[200px] placeholder:text-muted text-[16px] min-h-[48px] leading-relaxed font-medium"
            placeholder={isDeepSearch ? "深度研究：输入复杂问题..." : "Ask anything..."}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            disabled={disabled}
          />

          {/* Right Actions */}
          <div className="flex items-center gap-2 pb-1 px-1">
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.button
                  key="stop"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  whileTap={{ scale: 0.9 }}
                  className="p-2.5 rounded-full bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all"
                  onClick={onAbort}
                  aria-label="停止生成"
                >
                  <StopCircle className="w-6 h-6 fill-current" />
                </motion.button>
              ) : (
                <motion.button
                  key="send"
                  disabled={!input.trim()}
                  initial={{ scale: 0.9, opacity: 0.5 }}
                  animate={{
                    scale: input.trim() ? 1 : 0.95,
                    opacity: input.trim() ? 1 : 0.3
                  }}
                  whileHover={input.trim() ? { scale: 1.05 } : {}}
                  whileTap={input.trim() ? { scale: 0.95 } : {}}
                  className={clsx(
                    "p-3 rounded-2xl transition-all duration-500",
                    input.trim()
                      ? "bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-lg shadow-purple-500/20"
                      : "bg-white/5 text-gray-500"
                  )}
                  onClick={handleSend}
                  aria-label="发送消息"
                >
                  <Send className="w-5 h-5 ml-0.5" />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Mode Indicator & Secondary Branding */}
        <div className="flex items-center justify-center gap-6 mt-4 opacity-40 hover:opacity-100 transition-opacity duration-500">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          <p className="text-[10px] text-gray-400 font-bold tracking-[0.3em] uppercase whitespace-nowrap">
            {isDeepSearch ? 'Protocol Active • Deep Reasoning' : 'MYAGENT KERNEL • v2.5'}
          </p>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        </div>
      </div>
    </div>
  );
}
