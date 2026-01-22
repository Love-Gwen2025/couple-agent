/**
 * Open WebUI 风格侧边栏组件
 *
 * 特性：
 * - 可拖拽调整宽度 (220px - 480px)
 * - 简洁的灰度样式
 * - 会话按时间分组（今天/昨天/过去7天/更早）
 */
import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { Plus, MessageSquare, Trash2, Menu, Settings, Pencil, type LucideIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, useConversationStore, useUIStore } from '../../store';
import { SIDEBAR_COLLAPSED_WIDTH } from '../../store/uiStore';
import { getConversations, createConversation, deleteConversation, updateConversationTitle } from '../../api';
import clsx from 'clsx';
import { UserProfileModal } from '../settings';
import type { Conversation } from '../../types';

/**
 * 时间分组类型
 */
type TimeGroup = 'today' | 'yesterday' | 'lastWeek' | 'older';

/**
 * 分组标签
 */
const TIME_GROUP_LABELS: Record<TimeGroup, string> = {
  today: '今天',
  yesterday: '昨天',
  lastWeek: '过去 7 天',
  older: '更早',
};

/**
 * 判断日期属于哪个时间分组
 */
function getTimeGroup(dateStr: string): TimeGroup {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);

  if (date >= today) {
    return 'today';
  } else if (date >= yesterday) {
    return 'yesterday';
  } else if (date >= lastWeek) {
    return 'lastWeek';
  }
  return 'older';
}

/**
 * 按时间分组会话
 */
function groupConversationsByTime(conversations: Conversation[]): Record<TimeGroup, Conversation[]> {
  const groups: Record<TimeGroup, Conversation[]> = {
    today: [],
    yesterday: [],
    lastWeek: [],
    older: [],
  };

  conversations.forEach((conv) => {
    const group = getTimeGroup(conv.updatedAt || conv.createdAt || '');
    groups[group].push(conv);
  });

  return groups;
}

/**
 * 侧边栏项目组件 - Open WebUI 简洁风格
 */
function SidebarItem({
  icon: Icon,
  label,
  isActive,
  onClick,
  onEdit,
  onDelete,
  isCollapsed,
}: {
  icon: LucideIcon;
  label: string;
  isActive?: boolean;
  onClick: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  isCollapsed: boolean;
}) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'sidebar-item group relative',
        isActive && 'active',
        isCollapsed && 'justify-center !w-10 !h-10 !p-0 mx-auto'
      )}
      title={isCollapsed ? label : undefined}
      aria-current={isActive ? 'page' : undefined}
    >
      <Icon
        className={clsx(
          'w-5 h-5 flex-shrink-0 transition-colors',
          isActive ? 'text-foreground' : 'text-muted group-hover:text-foreground'
        )}
      />

      {!isCollapsed && (
        <span
          className={clsx(
            'text-sm truncate flex-1 transition-colors',
            isActive ? 'font-medium text-foreground' : 'text-muted group-hover:text-foreground'
          )}
        >
          {label}
        </span>
      )}

      {/* 编辑和删除按钮 - hover 时显示 */}
      {!isCollapsed && (onEdit || onDelete) && (
        <div className="opacity-0 group-hover:opacity-100 absolute right-2 flex items-center gap-0.5 transition-opacity">
          {onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              className="btn-icon p-1"
              title="重命名"
              aria-label="重命名会话"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="btn-icon p-1 hover:!bg-red-500/10 hover:!text-red-500"
              title="删除"
              aria-label="删除会话"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  // 编辑状态
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  // 滚动容器 ref
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  // 侧边栏容器 ref（用于拖拽）
  const sidebarRef = useRef<HTMLDivElement>(null);
  // 分页状态
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  // 拖拽状态
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);

  // 认证状态
  const { token, user } = useAuthStore();

  // 会话状态
  const {
    conversations,
    currentConversationId,
    setConversations,
    addConversation,
    removeConversation,
    updateConversation,
    setCurrentConversationId,
  } = useConversationStore();

  // UI 状态
  const { sidebarOpen, sidebarWidth, toggleSidebar, setSidebarWidth } = useUIStore();

  // 按时间分组的会话
  const groupedConversations = useMemo(() => {
    return groupConversationsByTime(conversations);
  }, [conversations]);

  // 计算实际显示宽度
  const displayWidth = sidebarOpen ? sidebarWidth : SIDEBAR_COLLAPSED_WIDTH;

  useEffect(() => {
    if (token) loadConversations();
  }, [token]);

  // 编辑时自动聚焦
  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  // 拖拽调整宽度的事件处理
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - resizeStartX.current;
      const newWidth = resizeStartWidth.current + deltaX;
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, setSidebarWidth]);

  /**
   * 开始拖拽调整宽度
   */
  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      if (!sidebarOpen) return;
      e.preventDefault();
      setIsResizing(true);
      resizeStartX.current = e.clientX;
      resizeStartWidth.current = sidebarWidth;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [sidebarOpen, sidebarWidth]
  );

  async function loadConversations() {
    try {
      const { items, hasMore: more } = await getConversations(1, 20);
      setConversations(items);
      setHasMore(more);
      setCurrentPage(1);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  // 加载更多会话
  async function loadMoreConversations() {
    if (isLoadingMore || !hasMore) return;
    setIsLoadingMore(true);
    try {
      const nextPage = currentPage + 1;
      const { items, hasMore: more } = await getConversations(nextPage, 20);
      setConversations([...conversations, ...items]);
      setHasMore(more);
      setCurrentPage(nextPage);
    } catch (error) {
      console.error('Failed to load more conversations:', error);
    } finally {
      setIsLoadingMore(false);
    }
  }

  // 滚动到底部时加载更多
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container || isLoadingMore || !hasMore) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    if (scrollHeight - scrollTop - clientHeight < 100) {
      loadMoreConversations();
    }
  }, [isLoadingMore, hasMore, conversations.length]);

  async function handleCreateConversation() {
    try {
      const newConversation = await createConversation({ title: 'New chat' });
      addConversation(newConversation);
      setCurrentConversationId(newConversation.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  }

  async function handleDeleteConversation(id: string) {
    try {
      await deleteConversation(id);
      removeConversation(id);
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  }

  // 开始编辑会话标题
  function handleEditConversation(id: string, currentTitle: string) {
    setEditingId(id);
    setEditingTitle(currentTitle || '');
  }

  // 保存编辑的标题
  async function handleSaveTitle() {
    if (!editingId || !editingTitle.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await updateConversationTitle(editingId, editingTitle.trim());
      updateConversation(editingId, { title: editingTitle.trim() });
    } catch (error) {
      console.error('Failed to update conversation title:', error);
    } finally {
      setEditingId(null);
    }
  }

  // 取消编辑
  function handleCancelEdit() {
    setEditingId(null);
    setEditingTitle('');
  }

  /**
   * 渲染会话项
   */
  const renderConversationItem = (conv: Conversation) => {
    if (editingId === conv.id) {
      // 编辑模式 - 显示输入框
      return (
        <div
          key={conv.id}
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-surface-container-high"
        >
          <MessageSquare className="w-4 h-4 text-muted flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={editingTitle}
            onChange={(e) => setEditingTitle(e.target.value)}
            onBlur={handleSaveTitle}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveTitle();
              if (e.key === 'Escape') handleCancelEdit();
            }}
            className="flex-1 bg-transparent text-sm outline-none border-b border-primary/50 focus:border-primary py-0.5 text-foreground"
            placeholder="输入会话标题..."
          />
        </div>
      );
    }

    // 正常模式 - 显示标题
    return (
      <SidebarItem
        key={conv.id}
        icon={MessageSquare}
        label={conv.title || 'Chat'}
        isActive={conv.id === currentConversationId}
        onClick={() => setCurrentConversationId(conv.id)}
        onEdit={() => handleEditConversation(conv.id, conv.title || '')}
        onDelete={() => handleDeleteConversation(conv.id)}
        isCollapsed={!sidebarOpen}
      />
    );
  };

  return (
    <motion.div
      ref={sidebarRef}
      initial={false}
      animate={{ width: displayWidth }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="relative h-screen flex flex-col bg-surface border-r border-border/30 flex-shrink-0 overflow-hidden"
    >
      {/* 拖拽调整宽度的 resizer */}
      {sidebarOpen && (
        <div
          onMouseDown={handleResizeStart}
          className={clsx(
            'absolute right-0 top-0 bottom-0 w-1 cursor-col-resize z-50',
            'hover:bg-primary/30 transition-colors',
            isResizing && 'bg-primary/50'
          )}
        />
      )}

      {/* Header */}
      <div className={clsx(
        'py-3 flex items-center gap-2',
        sidebarOpen ? 'px-3 justify-between' : 'px-1 justify-center'
      )}>
        <button
          onClick={toggleSidebar}
          className="btn-icon"
          aria-label={sidebarOpen ? '收起侧边栏' : '展开侧边栏'}
          aria-expanded={sidebarOpen}
        >
          <Menu className="w-5 h-5" />
        </button>

        {sidebarOpen && (
          <span className="text-sm font-semibold text-foreground">MyAgent</span>
        )}

        {sidebarOpen && <div className="w-9" />}
      </div>

      {/* New Chat Button */}
      <div className={clsx(sidebarOpen ? 'px-3 mb-4' : 'px-1 mb-3 flex justify-center')}>
        <button
          onClick={handleCreateConversation}
          className={clsx(
            'flex items-center justify-center gap-2 transition-colors',
            'bg-gray-900 dark:bg-white text-white dark:text-gray-900',
            'hover:bg-gray-800 dark:hover:bg-gray-100',
            'font-medium rounded-xl',
            sidebarOpen ? 'w-full px-4 py-2.5' : 'w-10 h-10 p-0'
          )}
          title="New Chat"
        >
          <Plus className={clsx(sidebarOpen ? 'w-4 h-4' : 'w-5 h-5')} />
          {sidebarOpen && <span className="text-sm">New Chat</span>}
        </button>
      </div>

      {/* Conversation List */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className={clsx('flex-1 overflow-y-auto scrollbar-hidden', sidebarOpen ? 'px-2' : 'px-1')}
      >
        <AnimatePresence>
          {/* 按时间分组渲染会话 */}
          {(['today', 'yesterday', 'lastWeek', 'older'] as TimeGroup[]).map((group) => {
            const groupConvs = groupedConversations[group];
            if (groupConvs.length === 0) return null;

            return (
              <div key={group} className="mb-2">
                {/* 分组标签 */}
                {sidebarOpen && (
                  <div className="sidebar-time-group">{TIME_GROUP_LABELS[group]}</div>
                )}
                {/* 会话列表 */}
                <div className="space-y-0.5">
                  {groupConvs.map(renderConversationItem)}
                </div>
              </div>
            );
          })}
        </AnimatePresence>

        {/* 加载更多提示 */}
        {isLoadingMore && (
          <div className="py-3 text-center text-xs text-muted">加载中...</div>
        )}

        {/* 空状态 */}
        {conversations.length === 0 && (
          <div className="py-8 text-center text-sm text-muted">
            {sidebarOpen ? '暂无会话' : ''}
          </div>
        )}
      </div>

      {/* Bottom Section */}
      <div className={clsx('mt-auto py-3 border-t border-border/30 space-y-1', sidebarOpen ? 'px-2' : 'px-1')}>
        {/* Settings Button */}
        <SidebarItem
          icon={Settings}
          label="设置"
          onClick={() => setIsProfileModalOpen(true)}
          isCollapsed={!sidebarOpen}
        />

        {/* User Profile */}
        {sidebarOpen && user && (
          <div
            onClick={() => setIsProfileModalOpen(true)}
            className="sidebar-item mt-2 cursor-pointer"
          >
            <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-700 dark:text-gray-200 text-xs font-medium overflow-hidden">
              {user.avatar ? (
                <img src={user.avatar} alt="avatar" className="w-full h-full object-cover" />
              ) : (
                user.userName?.charAt(0).toUpperCase()
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-foreground truncate">{user.userName}</div>
            </div>
          </div>
        )}
      </div>

      <UserProfileModal isOpen={isProfileModalOpen} onClose={() => setIsProfileModalOpen(false)} />
    </motion.div>
  );
}
