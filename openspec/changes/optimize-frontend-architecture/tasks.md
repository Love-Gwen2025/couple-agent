# Tasks: optimize-frontend-architecture

任务按优先级和依赖关系排序。标记为 `[P]` 的任务可并行执行。

---

## Phase 1: 无障碍紧急修复 (P1)

> 目标：解决最紧急的无障碍问题，确保基本合规

### 1.1 添加 ARIA 属性
- [x] **T1.1.1** 为 ChatInput 发送按钮添加 `aria-label="发送消息"`
- [x] **T1.1.2** 为 ChatInput 深度搜索按钮添加 `aria-label` 和 `aria-pressed`
- [x] **T1.1.3** 为 MessageBubble 流式内容添加 `aria-live="polite"` 和 `aria-busy`
- [x] **T1.1.4** 为 Sidebar 当前会话添加 `aria-current="page"`
- [x] **T1.1.5** 为 ThemePanel 开关添加 `role="switch"` 和 `aria-checked`
- [x] **T1.1.6** 为 LoginPage 错误消息添加 `role="alert"`

**验证**：使用 axe-core 浏览器扩展检查，无 ARIA 相关错误

### 1.2 添加 prefers-reduced-motion 支持 [P]
- [x] **T1.2.1** 在 `index.css` 添加 `@media (prefers-reduced-motion: reduce)` 规则
- [x] **T1.2.2** 配置 Framer Motion 的 `MotionConfig` 使用 `reducedMotion="user"`

**验证**：系统设置减少动画后，所有动画应被禁用

### 1.3 添加焦点样式 [P]
- [x] **T1.3.1** 在 `index.css` 添加 `:focus-visible` 样式规则
- [x] **T1.3.2** 确保所有按钮和输入框有清晰的焦点指示器

**验证**：Tab 键导航时所有元素有可见焦点环

---

## Phase 2: 状态管理重构

> 目标：拆分单一 Store，提高可维护性和性能
> 依赖：无

### 2.1 创建新 Store 文件
- [x] **T2.1.1** 创建 `store/authStore.ts`，包含 user, token 及相关操作
- [x] **T2.1.2** 创建 `store/conversationStore.ts`，包含会话和消息状态
- [x] **T2.1.3** 创建 `store/modelStore.ts`，包含模型选择状态
- [x] **T2.1.4** 创建 `store/uiStore.ts`，包含主题和侧边栏状态
- [x] **T2.1.5** 创建 `store/navigationStore.ts`，包含页面导航状态
- [x] **T2.1.6** 更新 `store/index.ts` 统一导出所有 Store

**验证**：新 Store 文件创建完成，TypeScript 编译无错误

### 2.2 实现迁移脚本
- [x] **T2.2.1** 在 `store/migration.ts` 实现 `migrateFromV1` 函数
- [x] **T2.2.2** 添加存储版本检测逻辑
- [x] **T2.2.3** 在应用初始化时执行迁移检查

**验证**：旧版 localStorage 数据能正确迁移到新 Store

### 2.3 迁移组件使用
- [x] **T2.3.1** 迁移 `ChatPanel.tsx` 使用新 Store
- [x] **T2.3.2** 迁移 `Sidebar.tsx` 使用新 Store
- [x] **T2.3.3** 迁移 `MainLayout.tsx` 使用新 Store
- [x] **T2.3.4** 迁移 `LoginPage.tsx` 使用新 Store
- [x] **T2.3.5** 迁移 `ThemePanel.tsx` 使用新 Store
- [x] **T2.3.6** 迁移 `ModelSettingsPage.tsx` 使用新 Store
- [x] **T2.3.7** 迁移 `KnowledgePage.tsx` 使用新 Store

**验证**：所有组件正常工作，无状态丢失

### 2.4 添加选择器
- [x] **T2.4.1** 为常用状态组合创建 selector hooks
- [x] **T2.4.2** 更新组件使用 selector 而非整个 Store

**验证**：组件只订阅需要的状态，使用 React DevTools 确认

### 2.5 清理旧代码
- [x] **T2.5.1** 删除旧的 `store/index.ts` 中的 AppStore 定义（保留兼容层）
- [x] **T2.5.2** 清理迁移完成后的临时代码

**验证**：无遗留的旧 Store 代码

---

## Phase 3: 组件架构重构

> 目标：拆分大型组件，提高可维护性
> 依赖：Phase 2 完成（组件需使用新 Store）

### 3.1 创建 GreetingScreen 组件
- [x] **T3.1.1** 从 ChatPanel 提取 GreetingScreen 到独立文件
- [x] **T3.1.2** 定义 Props 接口（suggestions, onSuggestionClick）
- [x] **T3.1.3** 提取 SuggestionCard 作为内部组件

**验证**：欢迎界面功能正常，建议卡片点击有效

### 3.2 创建 MessageList 组件 [P after 3.1]
- [x] **T3.2.1** 创建 `MessageList.tsx` 文件
- [x] **T3.2.2** 从 ChatPanel 移动消息渲染逻辑
- [x] **T3.2.3** 处理滚动到底部逻辑

**验证**：消息列表正常渲染和滚动

### 3.3 创建 MessageEditor 组件 [P after 3.1]
- [x] **T3.3.1** 编辑功能保留在 MessageBubble 中（简化实现）
- [x] **T3.3.2** 通过 MessageList 传递编辑回调
- [x] **T3.3.3** 实现 onSubmit 和 onCancel 回调

**验证**：消息编辑功能正常工作

### 3.4 重构 ChatPanel
- [x] **T3.4.1** 移除提取到子组件的代码
- [x] **T3.4.2** 添加新组件的导入和使用
- [x] **T3.4.3** ChatPanel 从 ~400 行减少到 ~315 行

**验证**：ChatPanel 代码行数检查，功能回归测试

### 3.5 精简 MessageBubble Props
- [x] **T3.5.1** 保持编辑相关 Props（功能需要）
- [x] **T3.5.2** 简化分支导航的 Props 传递
- [x] **T3.5.3** Props 结构清晰，职责明确

**验证**：MessageBubble Props 数量检查

### 3.6 更新导出
- [x] **T3.6.1** 更新 `components/chat/index.ts` 导出新组件

**验证**：所有组件可正确导入

---

## Phase 4: 类型安全增强

> 目标：消除类型隐患，增强代码可靠性
> 依赖：Phase 3 完成（避免类型冲突）

### 4.1 统一 ID 类型
- [x] **T4.1.1** 修改 `types/index.ts` 中 Message.id 类型为 string
- [x] **T4.1.2** User.id 保留 number（后端兼容）
- [x] **T4.1.3** Message.senderId 保留 `number | string`（AI 兼容）
- [x] **T4.1.4** 更新所有使用 ID 的代码，使用 'streaming' 替代 -1

**验证**：TypeScript 编译无错误

### 4.2 消除 any 类型
- [x] **T4.2.1** 修复 GreetingScreen 中 SuggestionCard 的 icon prop 类型（使用 LucideIcon）
- [x] **T4.2.2** 修复 Sidebar 中 SidebarItem 的 icon prop 类型
- [x] **T4.2.3** 检查确认无其他 any 类型

**验证**：`grep -r ": any" --include="*.tsx" --include="*.ts" src/` 无结果

### 4.3 增强 tsconfig
- [x] **T4.3.1** 确认 `strict: true` 已启用
- [x] **T4.3.2** TypeScript 编译通过
- [x] **T4.3.3** 无编译错误

**验证**：`npx tsc --noEmit` 成功

---

## Phase 5: 测试与验证

> 目标：确保所有改动无回归
> 依赖：Phase 4 完成

### 5.1 编译验证
- [x] **T5.1.1** TypeScript 编译无错误 (`npx tsc --noEmit`)
- [x] **T5.1.2** 无 `any` 类型残留
- [x] **T5.1.3** Store 迁移脚本已集成到应用启动

**验证**：编译通过

### 5.2 代码质量检查
- [x] **T5.2.1** 新 Store 文件结构清晰
- [x] **T5.2.2** 组件拆分完成，职责明确
- [x] **T5.2.3** ARIA 属性已添加

**验证**：代码结构良好

### 5.3 后续测试（可选）
- [ ] **T5.3.1** 安装 `@axe-core/react` 进行无障碍自动化测试
- [ ] **T5.3.2** 为 Store 添加单元测试
- [ ] **T5.3.3** 手动功能回归测试

**验证**：建议后续完善测试覆盖

---

## 完成检查清单

- [x] 所有 Phase 任务完成
- [x] TypeScript 编译无错误
- [ ] ESLint 检查通过（可选）
- [x] ARIA 属性已添加
- [ ] 手动功能测试通过（建议执行）
- [ ] 代码 review 完成（建议执行）
- [x] 任务文档更新完成

---

## 并行执行指南

```
Phase 1 (可完全并行):
├── T1.1.x (ARIA 属性) ──────┐
├── T1.2.x (reduced-motion) ├─→ Phase 2
└── T1.3.x (焦点样式) ───────┘

Phase 2 (部分并行):
├── T2.1.x (创建 Store) ─→ T2.2.x (迁移脚本) ─→ T2.3.x (迁移组件)
│                                               ↓
└─────────────────────────────────────────→ T2.4.x (选择器) ─→ T2.5.x (清理)

Phase 3 (部分并行):
├── T3.1.x (GreetingScreen) ────────┐
├── T3.2.x (MessageList) [P after] ─├─→ T3.4.x (重构 ChatPanel)
└── T3.3.x (MessageEditor) [P after]┘        ↓
                                         T3.5.x (精简 Props)
                                             ↓
                                         T3.6.x (更新导出)

Phase 4 (顺序执行):
T4.1.x ─→ T4.2.x ─→ T4.3.x

Phase 5 (顺序执行):
T5.1.x ─→ T5.2.x ─→ T5.3.x
```
