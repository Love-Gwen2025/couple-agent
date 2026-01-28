/**
 * 主布局组件
 *
 * 包含侧边栏和主内容区域
 */
import { Sidebar } from '../sidebar';
import { ChatPanel } from '../chat';
import { useNavigationStore } from '../../store';
import { KnowledgePage, KnowledgeDetailPage } from '../knowledge';
import { ModelSettingsPage } from '../settings';
import { AgentsPage, AgentWorkflowDesignerPage } from '../agents';
import { ToolsPage } from '../tools';
import { Bot, Database, Users, Wrench } from 'lucide-react';

/**
 * 主布局组件
 *
 * Gemini Layout:
 * - Sidebar: Collapsible, #f0f4f9 (light) / #1e1f20 (dark)
 * - Main: White (light) / #131314 (dark), rounded corners
 */
export function MainLayout() {
  const { currentPage, setCurrentPage } = useNavigationStore();

  return (
    <div className="h-screen flex bg-background text-foreground overflow-hidden selection:bg-primary/20">
      {/* Sidebar is always visible in Chat view, maybe hide it in others or keep it? 
          For full page views like Knowledge/Models, usually sidebar is less relevant or should be collapsed.
          But let's keep it for now as "Chat" is the main view. 
          Actually, KnowledgePage and ModelSettingsPage have their own full page layout with back buttons.
          So if currentPage !== 'chat', we might not need the Sidebar or ChatPanel.
      */}

      {currentPage === 'chat' && <Sidebar />}

      <main className="flex-1 flex flex-col relative z-0 overflow-hidden bg-background">
        {currentPage === 'chat' && <ChatPanel />}
        {currentPage === 'knowledge' && <KnowledgePage />}
        {currentPage === 'knowledge-detail' && <KnowledgeDetailPage />}
        {currentPage === 'model-settings' && <ModelSettingsPage />}
        {currentPage === 'agents' && <AgentsPage />}
        {currentPage === 'agent-workflow' && <AgentWorkflowDesignerPage />}
        {currentPage === 'tools' && <ToolsPage />}
      </main>

      {/* Top Right Navigation - Only visible in Chat view to switch to others */}
      {currentPage === 'chat' && (
        <div className="absolute top-4 right-4 z-20 flex items-center gap-2">
          <button
            onClick={() => setCurrentPage('agents')}
            className="p-2.5 rounded-xl bg-surface-container-high/50 hover:bg-surface-container-high border border-border/10 text-muted hover:text-foreground transition-all backdrop-blur-md"
            title="Agents"
          >
            <Users className="w-5 h-5" />
          </button>
          <button
            onClick={() => setCurrentPage('tools')}
            className="p-2.5 rounded-xl bg-surface-container-high/50 hover:bg-surface-container-high border border-border/10 text-muted hover:text-foreground transition-all backdrop-blur-md"
            title="Tools"
          >
            <Wrench className="w-5 h-5" />
          </button>
          <button
            onClick={() => setCurrentPage('knowledge')}
            className="p-2.5 rounded-xl bg-surface-container-high/50 hover:bg-surface-container-high border border-border/10 text-muted hover:text-foreground transition-all backdrop-blur-md"
            title="Knowledge Base"
          >
            <Database className="w-5 h-5" />
          </button>
          <button
            onClick={() => setCurrentPage('model-settings')}
            className="p-2.5 rounded-xl bg-surface-container-high/50 hover:bg-surface-container-high border border-border/10 text-muted hover:text-foreground transition-all backdrop-blur-md"
            title="Model Settings"
          >
            <Bot className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}

