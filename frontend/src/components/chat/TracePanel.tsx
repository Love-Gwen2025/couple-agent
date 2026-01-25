/**
 * 过程展示面板（Gemini 风格，可折叠）
 */
import type { ReactNode } from 'react';
import { ChevronDown, Hammer, Sparkles, Wrench } from 'lucide-react';
import clsx from 'clsx';
import type { TraceItem } from '../../types';

function formatTime(ts: number): string {
  try {
    return new Date(ts).toLocaleTimeString('zh-CN', { hour12: false });
  } catch {
    return '';
  }
}

function renderLine(event: TraceItem): { icon: ReactNode; title: string; detail?: string } {
  if (event.type === 'agent_start') {
    return {
      icon: <Sparkles className="w-4 h-4 text-primary" />,
      title: `${event.agentName || 'Agent'} 开始执行`,
      detail: [event.role, event.agentKind].filter(Boolean).join(' · ') || undefined,
    };
  }
  if (event.type === 'agent_end') {
    return {
      icon: <Sparkles className="w-4 h-4 text-muted" />,
      title: `${event.agentName || 'Agent'} 执行结束`,
      detail: [event.role, event.status].filter(Boolean).join(' · ') || undefined,
    };
  }
  if (event.type === 'agent_output') {
    return {
      icon: <Hammer className="w-4 h-4 text-muted" />,
      title: `${event.agentName || 'Agent'} 输出`,
      detail: event.content ? event.content.slice(0, 120) : undefined,
    };
  }
  if (event.type === 'tool_start') {
    return {
      icon: <Wrench className="w-4 h-4 text-primary" />,
      title: `调用工具：${event.toolDisplayName || event.toolRef || event.tool || 'tool'}`,
      detail: event.agentName ? `by ${event.agentName}` : undefined,
    };
  }
  if (event.type === 'tool_end') {
    return {
      icon: <Wrench className="w-4 h-4 text-muted" />,
      title: `工具完成：${event.toolDisplayName || event.toolRef || event.tool || 'tool'}`,
      detail: event.agentName ? `by ${event.agentName}` : undefined,
    };
  }
  if (event.type === 'error') {
    return {
      icon: <Wrench className="w-4 h-4 text-red-400" />,
      title: '执行出错',
      detail: event.error || '未知错误',
    };
  }
  return {
    icon: <Wrench className="w-4 h-4 text-muted" />,
    title: event.type,
  };
}

export function TracePanel({ events, defaultOpen = false }: { events: TraceItem[]; defaultOpen?: boolean }) {
  if (!events || events.length === 0) return null;

  return (
    <details
      className="group rounded-xl border border-border/20 bg-surface/30 overflow-hidden"
      open={defaultOpen}
    >
      <summary className="cursor-pointer list-none flex items-center justify-between gap-3 px-4 py-3 hover:bg-surface-highlight/10 transition-colors">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-semibold text-foreground">过程</span>
          <span className="text-xs text-muted">({events.length})</span>
        </div>
        <ChevronDown className={clsx('w-4 h-4 text-muted transition-transform', 'group-open:rotate-180')} />
      </summary>

      <div className="px-4 pb-4 pt-1 space-y-2">
        {events.map((e, idx) => {
          const line = renderLine(e);
          return (
            <div key={`${e.type}-${e.receivedAt}-${idx}`} className="flex gap-3 items-start">
              <div className="mt-0.5">{line.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <div className="text-sm text-foreground font-medium">{line.title}</div>
                  <div className="text-[11px] text-muted">{formatTime(e.receivedAt)}</div>
                </div>
                {line.detail && <div className="text-xs text-muted mt-0.5 break-words">{line.detail}</div>}
              </div>
            </div>
          );
        })}
      </div>
    </details>
  );
}
