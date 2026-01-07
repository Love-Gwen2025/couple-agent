# 架构设计: optimize-frontend-architecture

## 设计概述

本文档描述前端优化的架构决策和技术方案。优化围绕四个核心能力展开：组件架构、状态管理、无障碍访问和类型安全。

---

## 1. 组件架构重构

### 1.1 当前问题

```
ChatPanel.tsx (395行)
├── GreetingScreen (内联)
├── MessageList (内联)
├── BranchNavigation (分散)
├── MessageEditing (分散)
└── InputArea (引用 ChatInput)
```

**问题**：单一组件承担过多职责，难以测试和维护。

### 1.2 目标架构

```
components/chat/
├── ChatPanel.tsx          # 容器组件 (~100行)
│   └── 编排子组件，管理整体流程
├── GreetingScreen.tsx     # 欢迎界面 (~80行)
│   └── 建议卡片、欢迎消息
├── MessageList.tsx        # 消息列表 (~120行)
│   └── 虚拟滚动、消息渲染
├── MessageBubble.tsx      # 消息气泡 (~100行)
│   └── 仅展示，不含编辑
├── MessageEditor.tsx      # 消息编辑器 (新增 ~80行)
│   └── 编辑模式逻辑
├── BranchNavigator.tsx    # 分支导航 (现有)
├── ChatInput.tsx          # 输入框 (现有)
└── ModelSelector.tsx      # 模型选择 (现有)
```

### 1.3 组件通信模式

```
                    ┌─────────────────┐
                    │   ChatPanel     │
                    │   (Container)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│GreetingScreen │   │ MessageList   │   │  ChatInput    │
│  (展示型)      │   │  (展示型)     │   │  (受控输入)   │
└───────────────┘   └───────┬───────┘   └───────────────┘
                            │
                            ▼
                   ┌───────────────┐
                   │MessageBubble  │
                   │  (展示型)     │
                   └───────────────┘
```

**设计原则**：
- 容器组件负责状态和逻辑
- 展示组件仅接收 props，无副作用
- 回调函数向上传递事件

### 1.4 Props 设计

**MessageBubble（优化后）**：
```typescript
interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  userAvatar?: string;
  // 分支导航通过 BranchNavigator 单独处理
  // 编辑通过 MessageEditor 单独处理
}
```

**MessageEditor（新增）**：
```typescript
interface MessageEditorProps {
  initialContent: string;
  onSubmit: (content: string) => void;
  onCancel: () => void;
}
```

---

## 2. 状态管理重构

### 2.1 当前问题

```typescript
// 单一巨大的 Store
interface AppState {
  // 认证 (2)
  user, token
  // 会话 (4)
  conversations, currentConversationId, messages, currentCheckpointId
  // 模型 (3)
  models, currentModelCode, currentModelId
  // UI (5)
  sidebarOpen, isLoading, streamingContent, themeMode, accentColor
  // 导航 (2)
  currentPage, selectedKnowledgeBaseId
  // ... 共 30+ 字段
}
```

### 2.2 目标架构

```typescript
// 按领域拆分为独立 Store

// 1. 认证 Store
const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
);

// 2. 会话 Store
const useConversationStore = create<ConversationState>()((set, get) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  currentCheckpointId: null,
  // 方法...
}));

// 3. 模型 Store
const useModelStore = create<ModelState>()(
  persist(
    (set) => ({
      models: [],
      currentModelCode: null,
      currentModelId: null,
    }),
    { name: 'model-storage' }
  )
);

// 4. UI Store
const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      themeMode: 'system',
      accentColor: 'blue',
    }),
    { name: 'ui-storage' }
  )
);

// 5. 导航 Store
const useNavigationStore = create<NavigationState>()((set) => ({
  currentPage: 'chat',
  selectedKnowledgeBaseId: null,
}));
```

### 2.3 Store 依赖关系

```
┌─────────────┐
│ useAuthStore│◄──────────────────────────┐
└──────┬──────┘                           │
       │ token                            │ 401时清除
       ▼                                  │
┌─────────────────┐                       │
│useConversationStore│◄───────────────────┤
└─────────────────┘                       │
       │                                  │
       ▼                                  │
┌─────────────────┐     ┌─────────────────┐
│  useModelStore  │     │   API Client    │
└─────────────────┘     └─────────────────┘

独立：
┌─────────────┐    ┌──────────────────┐
│ useUIStore  │    │useNavigationStore│
└─────────────┘    └──────────────────┘
```

### 2.4 选择器设计

```typescript
// 细粒度选择器避免不必要的重渲染
const useCurrentConversation = () =>
  useConversationStore((state) => ({
    id: state.currentConversationId,
    messages: state.messages,
  }));

const useTheme = () =>
  useUIStore((state) => ({
    mode: state.themeMode,
    accent: state.accentColor,
  }));
```

### 2.5 迁移策略

```typescript
// 1. 版本检测
const STORAGE_VERSION = 2;

// 2. 迁移函数
const migrateFromV1 = (oldState: OldAppState) => {
  return {
    auth: { user: oldState.user, token: oldState.token },
    conversation: { conversations: oldState.conversations, ... },
    model: { models: oldState.models, ... },
    ui: { themeMode: oldState.themeMode, ... },
  };
};

// 3. 初始化时检测并迁移
if (localStorage.getItem('app-storage')) {
  const old = JSON.parse(localStorage.getItem('app-storage')!);
  if (old.version < STORAGE_VERSION) {
    const migrated = migrateFromV1(old.state);
    // 写入新 store...
    localStorage.removeItem('app-storage');
  }
}
```

---

## 3. 无障碍访问设计

### 3.1 ARIA 属性规范

| 组件 | 必需 ARIA 属性 |
|------|----------------|
| ChatInput 发送按钮 | `aria-label="发送消息"` |
| ChatInput 深度搜索 | `aria-label`, `aria-pressed` |
| MessageBubble 流式 | `aria-live="polite"`, `aria-busy` |
| Sidebar 当前会话 | `aria-current="page"` |
| ThemePanel 开关 | `aria-checked`, `role="switch"` |
| Modal 容器 | `role="dialog"`, `aria-modal`, `aria-labelledby` |

### 3.2 键盘导航设计

```
Tab 顺序：
┌─────────────────────────────────────────────┐
│ [1] Sidebar Toggle                          │
│ [2] New Chat Button                         │
│ [3-N] Conversation Items (Arrow Up/Down)    │
├─────────────────────────────────────────────┤
│ [N+1] Model Selector                        │
│ [N+2] Message List (Arrow Up/Down)          │
│ [N+3] Chat Input                            │
│ [N+4] Send Button                           │
└─────────────────────────────────────────────┘

快捷键：
- Escape: 关闭模态框/取消编辑
- Enter: 发送消息（输入框内）
- Ctrl+Enter: 换行（输入框内）
- Ctrl+/: 切换深度搜索模式
```

### 3.3 焦点管理

```typescript
// 焦点陷阱 Hook
function useFocusTrap(ref: RefObject<HTMLElement>, isActive: boolean) {
  useEffect(() => {
    if (!isActive) return;

    const element = ref.current;
    const focusableElements = element?.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements?.[0] as HTMLElement;
    const lastElement = focusableElements?.[focusableElements.length - 1] as HTMLElement;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    element?.addEventListener('keydown', handleKeyDown);
    firstElement?.focus();

    return () => element?.removeEventListener('keydown', handleKeyDown);
  }, [ref, isActive]);
}
```

### 3.4 动画减弱支持

```css
/* index.css */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

```typescript
// Framer Motion 配置
const motionConfig = {
  reducedMotion: 'user', // 尊重系统偏好
};

<MotionConfig reducedMotion="user">
  <App />
</MotionConfig>
```

---

## 4. 类型安全设计

### 4.1 ID 类型统一

```typescript
// types/index.ts

// 所有 ID 统一为 string 类型（雪花 ID）
type ID = string;

// 品牌类型用于区分不同领域的 ID
type ConversationId = string & { readonly __brand: 'ConversationId' };
type MessageId = string & { readonly __brand: 'MessageId' };
type UserId = string & { readonly __brand: 'UserId' };

// 工厂函数
const createConversationId = (id: string): ConversationId => id as ConversationId;
const createMessageId = (id: string): MessageId => id as MessageId;
```

### 4.2 消除 any 类型

```typescript
// Before
function SuggestionCard({ icon: Icon, ... }: { icon: any, ... })

// After
import { type LucideIcon } from 'lucide-react';
function SuggestionCard({ icon: Icon, ... }: { icon: LucideIcon, ... })
```

### 4.3 严格模式增强

```json
// tsconfig.app.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

---

## 5. 权衡与决策

### 5.1 组件拆分粒度

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| 细粒度（每个功能一个文件） | 高复用、易测试 | 文件过多、导入复杂 | ❌ |
| 中粒度（按职责分组） | 平衡复用和简洁 | 需要明确职责边界 | ✅ 采用 |
| 粗粒度（保持现状） | 改动小 | 问题未解决 | ❌ |

### 5.2 Store 拆分策略

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| 完全独立 Store | 解耦彻底 | 跨 Store 通信复杂 | ❌ |
| 按领域拆分 + 共享工具 | 清晰的领域边界 | 需要定义好边界 | ✅ 采用 |
| Context + useReducer | React 原生 | 性能不如 Zustand | ❌ |

### 5.3 无障碍实现优先级

| 功能 | 影响 | 实现难度 | 优先级 |
|------|------|----------|--------|
| ARIA 属性 | 高 | 低 | P1 |
| prefers-reduced-motion | 高 | 低 | P1 |
| 键盘导航 | 中 | 中 | P2 |
| 焦点管理 | 中 | 中 | P2 |
| 颜色对比度 | 中 | 低 | P2 |

---

## 6. 实现顺序

```
Phase 1: 无障碍紧急修复 (P1)
├── 添加 ARIA 属性
├── 添加 prefers-reduced-motion
└── 添加焦点样式

Phase 2: 状态管理重构
├── 创建新 Store 文件
├── 实现迁移脚本
├── 逐步迁移组件
└── 删除旧 Store

Phase 3: 组件架构重构
├── 创建 GreetingScreen
├── 创建 MessageEditor
├── 重构 ChatPanel
└── 优化 MessageBubble

Phase 4: 类型安全增强
├── 统一 ID 类型
├── 消除 any 类型
└── 增强 tsconfig
```

---

## 7. 测试策略

### 7.1 无障碍测试

```typescript
// 使用 @axe-core/react 自动化测试
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('ChatPanel 无障碍检查', async () => {
  const { container } = render(<ChatPanel />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### 7.2 Store 测试

```typescript
// Zustand store 测试
import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from './authStore';

test('logout 清除用户和 token', () => {
  const { result } = renderHook(() => useAuthStore());

  act(() => {
    result.current.setUser({ id: 1, userCode: 'test' });
    result.current.setToken('token123');
  });

  act(() => {
    result.current.logout();
  });

  expect(result.current.user).toBeNull();
  expect(result.current.token).toBeNull();
});
```

---

## 8. 回滚计划

如果优化导致严重问题：

1. **Store 迁移问题**：保留旧 `app-storage` key，可快速回退
2. **组件拆分问题**：保留原 ChatPanel 代码在 `_legacy` 分支
3. **类型变更问题**：可通过 `as any` 临时绕过（不推荐长期使用）
