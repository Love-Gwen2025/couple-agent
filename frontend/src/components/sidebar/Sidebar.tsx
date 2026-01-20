/**
 * Gemini Sidebar - Premium Colorful Edition
 *
 * 侧边栏组件，显示会话列表和用户信息
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { Plus, MessageSquare, Trash2, Menu, Settings, Pencil, type LucideIcon } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuthStore, useConversationStore, useUIStore } from '../../store';
import { getConversations, createConversation, deleteConversation, updateConversationTitle } from '../../api';
import clsx from 'clsx';
import { UserProfileModal } from '../settings';


function SidebarItem({
  icon: Icon,
  label,
  isActive,
  onClick,
  onEdit,
  onDelete,
  isCollapsed,
  colorClass = "text-muted"
}: {
  icon: LucideIcon;
  label: string;
  isActive?: boolean;
  onClick: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  isCollapsed: boolean;
  colorClass?: string;
}) {
  return (
    <motion.div
      whileHover={{ scale: 1.01, x: 2, backgroundColor: "rgba(255, 255, 255, 0.05)" }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className={clsx(
        "flex items-center gap-3 px-4 py-3 rounded-[20px] cursor-pointer transition-all duration-300 group relative",
        isActive
          ? "bg-gradient-to-br from-purple-500/15 to-pink-500/5 text-foreground shadow-lg shadow-purple-500/5 border border-purple-500/20"
          : "text-muted hover:text-foreground hover:bg-surface-highlight/10",
        isCollapsed ? "justify-center w-12 h-12 px-0 mx-auto" : "w-full"
      )}
      title={isCollapsed ? label : undefined}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon className={clsx(
        "w-5 h-5 flex-shrink-0 transition-all duration-300",
        isActive ? "text-purple-400 scale-110" : `${colorClass} group-hover:text-purple-400 group-hover:scale-105`
      )} />

      {!isCollapsed && (
        <span className={clsx(
          "text-sm truncate flex-1 transition-colors duration-300",
          isActive ? "font-bold text-foreground" : "font-medium"
        )}>
          {label}
        </span>
      )}

      {/* 编辑和删除按钮 */}
      {!isCollapsed && (onEdit || onDelete) && (
        <div className="opacity-0 group-hover:opacity-100 absolute right-2 flex items-center gap-1 transition-opacity duration-200">
          {onEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(); }}
              className="p-1.5 hover:bg-primary/20 hover:text-primary rounded-full transition-all duration-200"
              title="重命名"
              aria-label="重命名会话"
            >
              <Pencil className="w-4 h-4" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="p-1.5 hover:bg-red-500/20 hover:text-red-500 rounded-full transition-all duration-200"
              title="删除"
              aria-label="删除会话"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}

export function Sidebar() {
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  // 编辑状态
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  // 滚动容器ref
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  // 分页状态
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

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
  const { sidebarOpen, toggleSidebar } = useUIStore();

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


  return (
    <motion.div
      initial={false}
      animate={{ width: sidebarOpen ? 300 : 80 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="glass-premium dual-stroke shadow-premium h-[calc(100vh-24px)] m-3 rounded-[32px] flex flex-col pt-6 pb-6 z-20 flex-shrink-0 overflow-hidden"
    >
      {/* Header with Menu */}
      <div className={clsx("px-6 mb-6 flex items-center", sidebarOpen ? "justify-between" : "justify-center")}>
        <motion.button
          whileHover={{ scale: 1.1, rotate: 90 }}
          whileTap={{ scale: 0.9 }}
          onClick={toggleSidebar}
          className="p-3 bg-white/[0.03] hover:bg-surface-highlight/20 rounded-2xl transition-all text-muted hover:text-purple-400"
          aria-label={sidebarOpen ? "收起侧边栏" : "展开侧边栏"}
          aria-expanded={sidebarOpen}
        >
          <Menu className="w-5 h-5" />
        </motion.button>
      </div>

      {/* ★★★ NEW CHAT BUTTON - Big, Colorful, Obvious ★★★ */}
      <div className={clsx("px-3 mb-6", sidebarOpen ? "" : "flex justify-center")}>
        <motion.button
          whileHover={{ scale: 1.05, boxShadow: "0 0 30px rgba(168, 85, 247, 0.4)" }}
          whileTap={{ scale: 0.95 }}
          onClick={handleCreateConversation}
          className={clsx(
            "flex items-center justify-center gap-3 cursor-pointer transition-all duration-300",
            "bg-gradient-to-r from-purple-600 via-purple-500 to-pink-500",
            "hover:from-purple-700 hover:via-purple-600 hover:to-pink-600",
            "rounded-2xl text-white font-bold shadow-lg",
            "border-2 border-border/20",
            sidebarOpen ? "w-full px-5 py-4" : "w-14 h-14 p-0"
          )}
          title="New Chat"
        >
          <Plus className={clsx("transition-transform", sidebarOpen ? "w-5 h-5" : "w-6 h-6")} />
          {sidebarOpen && <span className="text-base tracking-[0.1em] uppercase italic">New Chat</span>}
        </motion.button>
      </div>

      {/* Recent Section Label */}
      {sidebarOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="px-6 mb-2 text-xs font-semibold text-transparent bg-gradient-to-r from-primary to-secondary bg-clip-text uppercase tracking-wider"
        >
          Recent Chats
        </motion.div>
      )}

      {/* Conversation List */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-2 space-y-1 scrollbar-none"
      >
        {conversations.map((conv, index) => (
          <motion.div
            key={conv.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.03 }}
          >
            {editingId === conv.id ? (
              /* 编辑模式 - 显示输入框 */
              <div className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-surface-container-high">
                <MessageSquare className="w-5 h-5 text-indigo-400 flex-shrink-0" />
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
                  className="flex-1 bg-transparent text-sm font-medium outline-none border-b-2 border-primary/50 focus:border-primary py-0.5 text-foreground"
                  placeholder="输入会话标题..."
                />
              </div>
            ) : (
              /* 正常模式 - 显示标题 */
              <SidebarItem
                icon={MessageSquare}
                label={conv.title || 'Chat'}
                isActive={conv.id === currentConversationId}
                onClick={() => setCurrentConversationId(conv.id)}
                onEdit={() => handleEditConversation(conv.id, conv.title || '')}
                onDelete={() => handleDeleteConversation(conv.id)}
                isCollapsed={!sidebarOpen}
                colorClass="text-purple-400"
              />
            )}
          </motion.div>
        ))}
        {/* 加载更多提示 */}
        {isLoadingMore && (
          <div className="py-2 text-center text-xs text-muted">加载中...</div>
        )}
      </div>

      {/* Bottom Section - Settings Only */}
      <div className="mt-auto px-2 space-y-1 pt-4 border-t border-border/10">
        {/* Unified Settings Button */}
        <SidebarItem
          icon={Settings}
          label="System Settings"
          onClick={() => {
            setIsProfileModalOpen(true);
          }}
          isCollapsed={!sidebarOpen}
          colorClass="text-purple-400"
        />

        {/* User Profile - Colorful Avatar */}
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => setIsProfileModalOpen(true)}
            className="mt-3 mx-2 pt-3 border-t border-border/10 flex items-center gap-3 px-2 py-2 cursor-pointer hover:bg-surface-highlight/20 rounded-2xl transition-all active:scale-95"
          >
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500 via-pink-500 to-purple-800 rounded-full blur-sm opacity-40"></div>
              <div className="relative w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center text-white text-xs font-black shadow-lg overflow-hidden border border-border/20">
                {user?.avatar ? (
                  <img src={user.avatar} alt="avatar" className="w-full h-full object-cover" />
                ) : (
                  user?.userName?.charAt(0).toUpperCase()
                )}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-black text-foreground truncate uppercase tracking-tight">{user?.userName}</div>
              <div className="text-[10px] bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent font-black uppercase tracking-widest">Online</div>
            </div>
          </motion.div>
        )}
      </div>

      <UserProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
      />
    </motion.div>
  );
}
