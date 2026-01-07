/**
 * 聊天面板组件
 *
 * 主聊天界面，整合消息列表、输入框和模型选择器
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { useAuthStore, useConversationStore, useModelStore } from '../../store';
import { useSSEChat, useMessageTree } from '../../hooks';
import { getConversationHistory } from '../../api';
import { setCurrentMessage } from '../../api/branch';
import { MessageList } from './MessageList';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { ModelSelector } from './ModelSelector';
import { GreetingScreen } from './GreetingScreen';
import type { Message } from '../../types';

/**
 * 聊天面板组件
 */
export function ChatPanel() {
  // 认证状态
  const { user } = useAuthStore();

  // 会话状态
  const {
    currentConversationId,
    streamingContent,
    setStreamingContent,
    clearStreamingContent,
    setCurrentCheckpointId,
    updateConversation,
  } = useConversationStore();

  // 模型状态
  const { currentModelCode, currentModelId } = useModelStore();

  // 消息树管理
  const {
    displayMessages,
    setMessageTree,
    switchBranch,
    getSiblingInfo,
    addMessage,
    replaceMessageId,
  } = useMessageTree({
    onSaveCurrentMessage: async (messageId) => {
      if (currentConversationId) {
        await setCurrentMessage(currentConversationId, messageId);
      }
    },
  });

  // 本地状态
  const latestStreamingRef = useRef<string>('');
  const latestMessageIdRef = useRef<number | string | null>(null);
  const pendingTempUserIdRef = useRef<string | null>(null);
  const [navLoadingId, setNavLoadingId] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const regeneratingIdRef = useRef<string | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState<string>('');

  // SSE 聊天钩子
  const { isLoading, sendMessage, abort, activeTool } = useSSEChat({
    onChunk: (chunk) => {
      latestStreamingRef.current = `${latestStreamingRef.current}${chunk}`;
      setStreamingContent(latestStreamingRef.current);
    },
    onComplete: async (event, finalContent) => {
      const contentToSave = finalContent || latestStreamingRef.current;
      if (contentToSave) {
        latestMessageIdRef.current = event.messageId ?? null;

        // 替换临时用户消息 ID 为服务器返回的真实 ID
        if (pendingTempUserIdRef.current && event.userMessageId) {
          replaceMessageId(pendingTempUserIdRef.current, String(event.userMessageId));
          pendingTempUserIdRef.current = null;
        }

        // 静默刷新历史，实现平滑过渡
        await loadHistory();
        setRegeneratingId(null);
        setNavLoadingId(null);
      }

      // 更新会话标题
      if (event.title && event.conversationId) {
        updateConversation(event.conversationId, { title: event.title });
      }

      latestStreamingRef.current = '';
      clearStreamingContent();
    },
    onError: (error) => {
      console.error('Chat Error:', error);
      latestStreamingRef.current = '';
      clearStreamingContent();
      setRegeneratingId(null);
      setNavLoadingId(null);
    },
  });

  // 加载会话历史
  useEffect(() => {
    if (currentConversationId) loadHistory();
  }, [currentConversationId]);

  async function loadHistory() {
    if (!currentConversationId) return;
    try {
      const data = await getConversationHistory(currentConversationId);
      setMessageTree(data.messages, data.currentMessageId);
      const lastCheckpoint =
        [...data.messages].reverse().find((item) => item.checkpointId)?.checkpointId || null;
      setCurrentCheckpointId(lastCheckpoint);
      setNavLoadingId(null);
      setRegeneratingId(null);
      setEditingMessageId(null);
      setEditingContent('');
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  }

  // 分支导航
  const handleNavigateBranch = useCallback(
    (messageId: string, direction: 'prev' | 'next') => {
      if (!currentConversationId || navLoadingId) return;
      setNavLoadingId(messageId);
      try {
        const info = getSiblingInfo(messageId);
        if (!info || info.total <= 1) return;
        const nextIndex = direction === 'prev' ? info.current - 1 : info.current + 1;
        if (nextIndex < 0 || nextIndex >= info.total) return;
        switchBranch(info.siblings[nextIndex]);
      } catch (error) {
        console.error('Branch switch failed:', error);
      } finally {
        setNavLoadingId(null);
      }
    },
    [currentConversationId, navLoadingId, getSiblingInfo, switchBranch]
  );

  // 重新生成回复
  const handleRegenerate = useCallback(
    (message: Message, index: number) => {
      if (!currentConversationId || !user) return;
      const lastUser = [...displayMessages]
        .slice(0, index)
        .reverse()
        .find((item) => item.role === 'user');
      if (!lastUser) return;

      const parentMessageId = String(lastUser.id);
      setRegeneratingId(String(message.id));
      regeneratingIdRef.current = String(message.id);
      latestStreamingRef.current = '';
      clearStreamingContent();

      sendMessage({
        conversationId: currentConversationId,
        content: lastUser.content,
        modelCode: currentModelCode || undefined,
        modelId: currentModelId || undefined,
        parentMessageId,
        regenerate: true,
      });
    },
    [
      clearStreamingContent,
      currentConversationId,
      currentModelCode,
      currentModelId,
      displayMessages,
      sendMessage,
      user,
    ]
  );

  // 编辑消息
  const startEditMessage = useCallback((message: Message) => {
    setEditingMessageId(String(message.id));
    setEditingContent(message.content);
  }, []);

  const submitEditMessage = useCallback(
    async (message: Message) => {
      if (!currentConversationId || !user) return;
      try {
        latestStreamingRef.current = '';
        clearStreamingContent();
        sendMessage({
          conversationId: currentConversationId,
          content: editingContent,
          modelCode: currentModelCode || undefined,
          modelId: currentModelId || undefined,
          parentMessageId: message.parentId || undefined,
        });
      } catch (error) {
        console.error('Edit failed:', error);
      } finally {
        setEditingMessageId(null);
        setEditingContent('');
      }
    },
    [
      clearStreamingContent,
      currentConversationId,
      currentModelCode,
      currentModelId,
      editingContent,
      sendMessage,
      user,
    ]
  );

  const cancelEdit = useCallback(() => {
    setEditingMessageId(null);
    setEditingContent('');
  }, []);

  // 发送消息
  const handleSend = useCallback(
    (content: string, mode?: string) => {
      if (!currentConversationId || !user) return;

      const lastMessage = displayMessages.length > 0 ? displayMessages[displayMessages.length - 1] : null;
      const parentMessageId = lastMessage ? String(lastMessage.id) : undefined;

      // 乐观更新：立即显示用户消息
      const tempId = `temp-${Date.now()}`;
      const tempUserMessage: Message = {
        id: tempId,
        conversationId: currentConversationId,
        senderId: user.id,
        role: 'user',
        content,
        contentType: 'TEXT',
        createTime: new Date().toISOString(),
        parentId: parentMessageId,
      };
      addMessage(tempUserMessage);
      pendingTempUserIdRef.current = tempId;

      latestStreamingRef.current = '';
      clearStreamingContent();
      sendMessage({
        conversationId: currentConversationId,
        content,
        modelCode: currentModelCode || undefined,
        modelId: currentModelId || undefined,
        parentMessageId,
        mode: mode || 'chat',
      });
    },
    [
      currentConversationId,
      currentModelCode,
      currentModelId,
      user,
      displayMessages,
      sendMessage,
      clearStreamingContent,
      addMessage,
    ]
  );

  // 无会话时显示欢迎界面
  if (!currentConversationId) {
    return <GreetingScreen userName={user?.userName || 'Traveler'} onSuggestionClick={handleSend} />;
  }

  return (
    <div className="flex-1 flex flex-col h-full relative bg-background ml-0 lg:ml-2">
      {/* 模型选择器 */}
      <div className="absolute top-0 left-0 right-0 p-4 z-10 flex justify-between items-start pointer-events-none">
        <div className="pointer-events-auto">
          <ModelSelector />
        </div>
      </div>

      {/* 消息区域 */}
      <div className="flex-1 overflow-hidden w-full pt-16">
        {displayMessages.length === 0 && !streamingContent ? (
          <GreetingScreen userName={user?.userName || 'User'} onSuggestionClick={handleSend} />
        ) : (
          <MessageList
            messages={displayMessages}
            conversationId={currentConversationId}
            streamingContent={streamingContent}
            activeTool={activeTool}
            userAvatar={user?.avatar}
            regeneratingId={regeneratingId}
            navLoadingId={navLoadingId}
            editingMessageId={editingMessageId}
            editingContent={editingContent}
            getSiblingInfo={getSiblingInfo}
            onNavigateBranch={handleNavigateBranch}
            onRegenerate={handleRegenerate}
            onStartEdit={startEditMessage}
            onEditChange={setEditingContent}
            onEditSubmit={submitEditMessage}
            onEditCancel={cancelEdit}
          />
        )}
      </div>

      {/* 输入区域 */}
      <ChatInput isLoading={isLoading} onSend={handleSend} onAbort={abort} />
    </div>
  );
}
