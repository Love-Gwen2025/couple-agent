/**
 * 消息列表组件
 *
 * 显示会话中的消息列表，支持分支导航、编辑和流式内容
 */
import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { MessageBubble } from './MessageBubble';
import { getToolDisplayName } from '../../hooks';
import type { Message } from '../../types';

/** 分支信息 */
export interface SiblingInfo {
  current: number;
  total: number;
  siblings: string[];
}

/** 消息列表属性 */
export interface MessageListProps {
  /** 消息列表 */
  messages: Message[];
  /** 当前会话 ID */
  conversationId: string;
  /** 流式内容 */
  streamingContent: string;
  /** 当前活动工具名称 */
  activeTool: string | null;
  /** 用户头像 */
  userAvatar?: string;
  /** 正在重新生成的消息 ID */
  regeneratingId: string | null;
  /** 导航加载中的消息 ID */
  navLoadingId: string | null;
  /** 正在编辑的消息 ID */
  editingMessageId: string | null;
  /** 编辑内容 */
  editingContent: string;
  /** 获取分支信息 */
  getSiblingInfo: (messageId: string) => SiblingInfo | null;
  /** 切换分支 */
  onNavigateBranch: (messageId: string, direction: 'prev' | 'next') => void;
  /** 重新生成回复 */
  onRegenerate: (message: Message, index: number) => void;
  /** 开始编辑消息 */
  onStartEdit: (message: Message) => void;
  /** 编辑内容变更 */
  onEditChange: (content: string) => void;
  /** 提交编辑 */
  onEditSubmit: (message: Message) => void;
  /** 取消编辑 */
  onEditCancel: () => void;
}

/**
 * 消息列表组件
 *
 * 负责渲染消息列表并处理自动滚动
 */
export function MessageList({
  messages,
  conversationId,
  streamingContent,
  activeTool,
  userAvatar,
  regeneratingId,
  navLoadingId,
  editingMessageId,
  editingContent,
  getSiblingInfo,
  onNavigateBranch,
  onRegenerate,
  onStartEdit,
  onEditChange,
  onEditSubmit,
  onEditCancel,
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 消息变化时滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, streamingContent]);

  return (
    <div className="h-full overflow-y-auto scrollbar-thin pb-8">
      <div className="max-w-3xl mx-auto px-4 py-4 space-y-4">
        {/* 消息列表 */}
        {messages.map((message, index) => (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <MessageBubble
              message={message}
              siblingInfo={
                message.role === 'assistant'
                  ? getSiblingInfo(String(message.id)) ?? undefined
                  : undefined
              }
              onNavigateBranch={
                message.role === 'assistant'
                  ? (direction) => onNavigateBranch(String(message.id), direction)
                  : undefined
              }
              onRegenerate={
                message.role === 'assistant' ? () => onRegenerate(message, index) : undefined
              }
              isRegenerating={
                regeneratingId === String(message.id) || navLoadingId === String(message.id)
              }
              isStreaming={streamingContent !== '' && message.id === 'streaming'}
              onEdit={message.role === 'user' ? () => onStartEdit(message) : undefined}
              isEditing={editingMessageId === String(message.id)}
              editingContent={editingContent}
              onEditChange={onEditChange}
              onEditSubmit={() => onEditSubmit(message)}
              onEditCancel={onEditCancel}
              userAvatar={message.role === 'user' ? userAvatar : undefined}
            />
          </motion.div>
        ))}

        {/* 工具执行状态 */}
        {activeTool && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 p-4 text-sm text-muted"
            aria-live="polite"
          >
            <div
              className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin"
              aria-hidden="true"
            />
            <span className="gradient-text font-medium">
              Running {getToolDisplayName(activeTool)}...
            </span>
          </motion.div>
        )}

        {/* 流式响应内容 */}
        {streamingContent && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <MessageBubble
              message={{
                id: 'streaming',
                conversationId,
                senderId: 'ai',
                role: 'assistant',
                content: streamingContent,
                contentType: 'TEXT',
                createTime: new Date().toISOString(),
              }}
              isStreaming={true}
            />
          </motion.div>
        )}

        {/* 滚动锚点 */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
