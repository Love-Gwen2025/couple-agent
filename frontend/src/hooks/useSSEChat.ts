/**
 * SSE 流式聊天 Hook
 *
 * 处理服务端推送的流式响应
 */
import { useState, useCallback, useRef } from 'react';
import type { StreamChatRequest, StreamChatEvent } from '../types';
import { API_BASE_URL, handleUnauthorized } from '../api/client';

interface UseSSEChatOptions {
  /** 收到内容片段时的回调 */
  onChunk?: (content: string) => void;
  /** 流式完成时的回调 */
  onComplete?: (event: StreamChatEvent, finalContent: string) => void;
  /** 发生错误时的回调 */
  onError?: (error: string) => void;
  /** 收到任意 SSE 事件时的回调（包含 agent/tool 事件） */
  onEvent?: (event: StreamChatEvent) => void;
  /** 工具开始调用时的回调 */
  onToolStart?: (toolName: string) => void;
  /** 工具调用结束时的回调 */
  onToolEnd?: (toolName: string) => void;
}

interface UseSSEChatReturn {
  /** 是否正在加载 */
  isLoading: boolean;
  /** 当前累积的响应内容 */
  content: string;
  /** 当前正在执行的工具名称（null 表示没有工具在执行） */
  activeTool: string | null;
  /** 发送消息 */
  sendMessage: (request: StreamChatRequest) => void;
  /** 中止当前请求 */
  abort: () => void;
  /** 重置状态 */
  reset: () => void;
}

/**
 * SSE 流式聊天 Hook
 *
 * @param options 配置选项
 * @returns SSE 聊天控制器
 */
export function useSSEChat(options: UseSSEChatOptions = {}): UseSSEChatReturn {
  const { onChunk, onComplete, onError, onEvent, onToolStart, onToolEnd } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [content, setContent] = useState('');
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setContent('');
    setIsLoading(false);
    setActiveTool(null);
  }, []);

  /**
   * 中止当前请求
   */
  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setActiveTool(null);
  }, []);

  /**
   * 发送流式聊天请求
   */
  const sendMessage = useCallback(
    async (request: StreamChatRequest) => {
      // 1. 中止之前的请求，避免多个流竞争
      abort();
      reset();
      setIsLoading(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { token } : {}),
          },
          body: JSON.stringify(request),
          signal: controller.signal,
        });

        /**
         * 1. 检测 401 未授权时立即清理本地状态并跳转登录
         * 2. 仅在授权通过后继续读取 SSE 数据流
         */
        if (response.status === 401) {
          handleUnauthorized();
          throw new Error('未授权，请重新登录');
        }

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('Response body is not readable');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            // 1. 跳过空行和注释
            if (!line.trim() || line.startsWith(':')) continue;

            // 2. 解析 SSE 数据
            if (line.startsWith('data:')) {
              const jsonStr = line.slice(5).trim();
              if (!jsonStr) continue;

              try {
                const event: StreamChatEvent = JSON.parse(jsonStr);
                onEvent?.(event);

                if (event.type === 'chunk' && event.content) {
                  accumulatedContent += event.content;
                  setContent(accumulatedContent);
                  onChunk?.(event.content);
                } else if (event.type === 'done') {
                  setIsLoading(false);
                  setActiveTool(null);
                  // done 事件使用当前累积内容作为最终内容传递
                  onComplete?.(event, accumulatedContent);
                } else if (event.type === 'error') {
                  setIsLoading(false);
                  setActiveTool(null);
                  onError?.(event.error || '未知错误');
                } else if (event.type === 'tool_start' && event.tool) {
                  // 工具开始调用
                  const toolName = event.toolDisplayName || event.toolRef || event.tool;
                  setActiveTool(toolName);
                  onToolStart?.(toolName);
                } else if (event.type === 'tool_end' && event.tool) {
                  // 工具调用结束
                  setActiveTool(null);
                  const toolName = event.toolDisplayName || event.toolRef || event.tool;
                  onToolEnd?.(toolName);
                }
              } catch {
                console.warn('Failed to parse SSE data:', jsonStr);
              }
            }
          }
        }
      } catch (error) {
        if ((error as Error).name === 'AbortError') {
          console.log('Request aborted');
        } else {
          const errorMessage =
            error instanceof Error ? error.message : '请求失败';
          onError?.(errorMessage);
        }
        setIsLoading(false);
        setActiveTool(null);
      }
    },
    [abort, reset, onChunk, onComplete, onError, onToolStart, onToolEnd]
  );

  return {
    isLoading,
    content,
    activeTool,
    sendMessage,
    abort,
    reset,
  };
}

