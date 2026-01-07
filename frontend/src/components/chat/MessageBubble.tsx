/**
 * 消息组件 - Refined Modern Edition
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Sparkles, RefreshCw, Pencil, ThumbsUp, ThumbsDown, Share2, MoreHorizontal } from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';
import type { Message, SiblingInfo } from '../../types';
import { BranchNavigator } from './BranchNavigator';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  siblingInfo?: SiblingInfo;
  onNavigateBranch?: (direction: 'prev' | 'next') => void;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  onEdit?: () => void;
  isEditing?: boolean;
  editingContent?: string;
  onEditChange?: (value: string) => void;
  onEditSubmit?: () => void;
  onEditCancel?: () => void;
  /** 用户头像 URL */
  userAvatar?: string;
}

function CodeBlock({ language, children }: { language: string; children: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group/code rounded-xl overflow-hidden my-4 border border-border/40 bg-surface-highlight/30">
      <div className="flex items-center justify-between px-4 py-2 bg-surface-highlight/40 border-b border-border/40">
        <span className="text-xs font-medium text-muted-foreground">{language || 'text'}</span>
        <button
          className="p-1 rounded hover:bg-surface-container-high transition-colors text-muted-foreground hover:text-foreground"
          onClick={handleCopy}
          aria-label="Copy code"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: '1rem',
          fontSize: '0.85rem',
          background: 'transparent', // Let container bg handle it or oneDark
          lineHeight: 1.5,
        }}
        codeTagProps={{
          style: { fontFamily: '"JetBrains Mono", "Fira Code", monospace' }
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

export function MessageBubble({
  message,
  isStreaming,
  siblingInfo,
  onNavigateBranch,
  onRegenerate,
  isRegenerating = false,
  onEdit,
  isEditing = false,
  editingContent = '',
  onEditChange,
  onEditSubmit,
  onEditCancel,
  userAvatar,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const showBranchNav = isAssistant && siblingInfo && siblingInfo.total > 1;

  return (
    <div
      className={clsx("flex gap-4 p-2 mb-2 group/row w-full", isUser ? "flex-row-reverse" : "flex-row")}
      aria-live={isStreaming ? "polite" : undefined}
      aria-busy={isStreaming}
    >

      {/* Avatar Area */}
      <div className="flex-shrink-0 mt-1">
        {isUser ? (
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-secondary flex items-center justify-center text-white text-xs font-medium shadow-sm overflow-hidden ring-2 ring-background">
            {userAvatar ? (
              <img src={userAvatar} alt="U" className="w-full h-full object-cover" />
            ) : (
              'U'
            )}
          </div>
        ) : (
          <div className={clsx(
            "w-8 h-8 rounded-full flex items-center justify-center border border-border bg-surface shadow-sm",
            isStreaming && "animate-pulse-soft"
          )}>
            <Sparkles className="w-4 h-4 text-primary fill-primary/20" />
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className={clsx("flex flex-col max-w-[85%] lg:max-w-[75%]", isUser ? "items-end" : "items-start")}>

        <div className={clsx(
          "text-xs font-medium mb-1 px-1 opacity-90",
          isUser ? "text-muted" : "text-muted"
        )}>
          {isUser ? 'You' : 'AI Assistant'}
        </div>

        <div className={clsx(
          "w-full relative",
          // User messages: Purple gradient with glow
          isUser && !isEditing ? "bg-gradient-to-br from-purple-600 to-pink-500 text-white rounded-[24px] rounded-tr-sm px-5 py-3 shadow-[0_4px_15px_-5px_rgba(168,85,247,0.4)]" : "",
          // Assistant messages: Glassy effect
          isAssistant ? "px-1 text-gray-100" : ""
        )}>

          {isEditing ? (
            <div className="w-full bg-background border border-border rounded-xl shadow-lg p-3">
              <textarea
                className="w-full min-h-[100px] bg-transparent outline-none resize-none text-sm leading-relaxed p-1"
                value={editingContent}
                onChange={(e) => onEditChange?.(e.target.value)}
                autoFocus
              />
              <div className="flex justify-end gap-2 mt-2 pt-2 border-t border-border/50">
                <button
                  onClick={onEditCancel}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted hover:bg-surface-highlight transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={onEditSubmit}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary text-white hover:bg-primary/90 transition-colors shadow-sm"
                >
                  Update
                </button>
              </div>
            </div>
          ) : (
            <div className={clsx(isUser ? "" : "markdown-body")}>
              {isUser ? (
                <p className="whitespace-pre-wrap leading-relaxed text-[0.95rem]">{message.content}</p>
              ) : (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                  components={{
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !match ? (
                        <code className="bg-surface-highlight px-1.5 py-0.5 rounded text-[0.85em] font-mono text-primary font-medium" {...props}>
                          {children}
                        </code>
                      ) : (
                        <CodeBlock language={match[1]}>{String(children).replace(/\n$/, '')}</CodeBlock>
                      );
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>
          )}
        </div>

        {/* Toolbar for AI Messages */}
        {isAssistant && !isStreaming && (
          <div className="flex items-center gap-1 mt-1.5 opacity-0 group-hover/row:opacity-100 transition-opacity duration-200 pl-1">
            {showBranchNav && onNavigateBranch && (
              <BranchNavigator
                currentIndex={siblingInfo.current}
                totalCount={siblingInfo.total}
                onNavigate={onNavigateBranch}
              />
            )}

            <div className="flex items-center gap-0.5 bg-surface-container border border-border/60 rounded-lg p-0.5 shadow-sm">
              <button
                className="p-1.5 hover:bg-surface-highlight rounded-md text-muted hover:text-foreground transition-colors"
                title="Good response"
                aria-label="好的回复"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                className="p-1.5 hover:bg-surface-highlight rounded-md text-muted hover:text-foreground transition-colors"
                title="Bad response"
                aria-label="不好的回复"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
              <div className="w-px h-3 bg-border mx-0.5" />
              <button
                className={clsx(
                  "p-1.5 hover:bg-surface-highlight rounded-md text-muted hover:text-foreground transition-colors",
                  isRegenerating && "animate-spin text-primary"
                )}
                onClick={onRegenerate}
                title="Regenerate"
                aria-label="重新生成"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                className="p-1.5 hover:bg-surface-highlight rounded-md text-muted hover:text-foreground transition-colors"
                title="Share"
                aria-label="分享"
              >
                <Share2 className="w-3.5 h-3.5" />
              </button>
              <button
                className="p-1.5 hover:bg-surface-highlight rounded-md text-muted hover:text-foreground transition-colors"
                title="More"
                aria-label="更多选项"
              >
                <MoreHorizontal className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Edit Button for User Messages */}
        {isUser && !isEditing && (
          <div className="mt-1 mr-1 self-end opacity-0 group-hover/row:opacity-100 transition-opacity duration-200">
            <button
              onClick={onEdit}
              className="p-1.5 rounded-lg hover:bg-surface-highlight text-muted hover:text-primary transition-colors"
              title="Edit"
              aria-label="编辑消息"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
