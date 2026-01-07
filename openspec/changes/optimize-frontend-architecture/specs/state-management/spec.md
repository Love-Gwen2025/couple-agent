# Spec: state-management

## 概述

定义前端状态管理的架构规范，包括 Store 拆分、选择器设计、持久化策略和迁移机制。

---

## ADDED Requirements

### Requirement: STATE-001 - Store 拆分

Global state MUST be split into independent Zustand stores by domain.

#### Scenario: 认证 Store 独立

**Given** `useAuthStore`
**When** 访问认证相关状态
**Then** 应只包含 `user`、`token` 及其操作方法

#### Scenario: 会话 Store 独立

**Given** `useConversationStore`
**When** 访问会话相关状态
**Then** 应只包含 `conversations`、`currentConversationId`、`messages`、`currentCheckpointId` 及其操作方法

#### Scenario: 模型 Store 独立

**Given** `useModelStore`
**When** 访问模型相关状态
**Then** 应只包含 `models`、`currentModelCode`、`currentModelId` 及其操作方法

#### Scenario: UI Store 独立

**Given** `useUIStore`
**When** 访问 UI 相关状态
**Then** 应只包含 `sidebarOpen`、`themeMode`、`accentColor` 及其操作方法

#### Scenario: 导航 Store 独立

**Given** `useNavigationStore`
**When** 访问导航相关状态
**Then** 应只包含 `currentPage`、`selectedKnowledgeBaseId` 及其操作方法

---

### Requirement: STATE-002 - 单个 Store 状态数量限制

Each store's state field count MUST be kept within a reasonable range.

#### Scenario: Store 状态数量上限

**Given** 任意 Store 的状态接口
**When** 统计状态字段数量（不含方法）
**Then** 状态字段数量应小于等于 10 个

---

### Requirement: STATE-003 - 选择器设计

Components MUST use fine-grained selectors to access stores. Components SHALL NOT subscribe to the entire store.

#### Scenario: 使用选择器获取单个字段

**Given** 组件只需要 `currentConversationId`
**When** 使用 Store
**Then** 应使用 `useConversationStore((s) => s.currentConversationId)` 形式

#### Scenario: 选择器返回稳定引用

**Given** 选择器返回对象
**When** Store 中其他无关字段变化
**Then** 选择器返回的引用应保持不变（浅比较）

---

### Requirement: STATE-004 - 持久化策略

States that need to be persisted MUST be explicitly configured. Non-essential states SHALL NOT be persisted.

#### Scenario: 认证状态持久化

**Given** 用户登录成功
**When** 刷新页面
**Then** `token` 和 `user` 应从 localStorage 恢复

#### Scenario: 会话状态不持久化

**Given** 用户在某个会话中
**When** 刷新页面
**Then** `currentConversationId` 和 `messages` 应重置为初始值

#### Scenario: 主题设置持久化

**Given** 用户切换主题为深色模式
**When** 刷新页面
**Then** `themeMode` 应保持为深色模式

---

### Requirement: STATE-005 - 迁移机制

When migrating from the old single store to the new split stores, data MUST NOT be lost.

#### Scenario: 检测旧版存储

**Given** localStorage 中存在 `app-storage` key
**When** 应用初始化
**Then** 应检测到旧版存储并触发迁移

#### Scenario: 迁移后清理旧存储

**Given** 旧版存储已成功迁移到新 Store
**When** 迁移完成
**Then** 应删除 `app-storage` key

#### Scenario: 迁移失败回退

**Given** 迁移过程中发生错误
**When** 捕获到错误
**Then** 应保留旧存储，记录错误日志，不影响用户使用

---

## MODIFIED Requirements

### Requirement: STATE-006 - Store 文件组织

Store files MUST be split into independent files by domain.

#### Scenario: Store 目录结构

**Given** `frontend/src/store/` 目录
**When** 列出文件
**Then** 应包含以下文件：
- `authStore.ts`
- `conversationStore.ts`
- `modelStore.ts`
- `uiStore.ts`
- `navigationStore.ts`
- `index.ts`（统一导出）
