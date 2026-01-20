/**
 * 消息输入框组件 - Refined Modern Edition
 * 
 * 支持：
 * - 普通对话模式
 * - DeepSearch 深度搜索模式
 */
import { useState, useRef, useEffect } from 'react';
import { Send, StopCircle, Plus, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface ChatInputProps {
  isLoading?: boolean;
  disabled?: boolean;
  onSend: (content: string, mode?: string) => void;
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

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    const content = input.trim();
    if (!content || isLoading || disabled) return;
    onSend(content, isDeepSearch ? 'deep_search' : 'chat');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
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
