/**
 * 消息输入框组件 - Refined Modern Edition
 * 
 * 支持：
 * - 普通对话模式
 * - DeepSearch 深度搜索模式
 *
 * 注意：知识库/工具/模型以 Agent 配置为准，聊天请求不允许覆盖。
 */
import { useState, useRef, useEffect } from 'react';
import { Send, StopCircle, Plus, Search } from 'lucide-react';
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
    /*
     根据输入内容自动调整文本框高度，提升输入体验。
    */
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    /*
     根据当前模式构建发送参数。
    */
    const content = input.trim();
    if (!content || isLoading || disabled) return;
    const mode = isDeepSearch ? 'deep_search' : 'chat';
    onSend(content, mode);
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
    <div className="shrink-0 px-4 py-3 bg-transparent relative z-10">
      <div className="max-w-4xl mx-auto">
        <div
          className={clsx(
            'flex items-end gap-2 p-2 rounded-2xl transition-all',
            'bg-surface border border-border/50',
            isFocused && 'border-primary/30 shadow-sm'
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
                ? "bg-gray-200 dark:bg-gray-700 text-foreground ring-1 ring-gray-300 dark:ring-gray-600"
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
          <div className="flex items-center gap-1">
            {isLoading ? (
              <button
                className="p-2.5 rounded-xl bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                onClick={onAbort}
                aria-label="停止生成"
              >
                <StopCircle className="w-5 h-5 fill-current" />
              </button>
            ) : (
              <button
                disabled={!input.trim()}
                className={clsx(
                  "p-2.5 rounded-xl transition-colors",
                  input.trim()
                    ? "bg-primary text-white hover:bg-primary/90"
                    : "bg-white/5 text-gray-500 cursor-not-allowed"
                )}
                onClick={handleSend}
                aria-label="发送消息"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
