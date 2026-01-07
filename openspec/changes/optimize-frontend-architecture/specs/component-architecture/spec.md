# Spec: component-architecture

## 概述

定义前端组件的架构规范，包括组件拆分原则、Props 设计、组件通信模式。

---

## ADDED Requirements

### Requirement: COMP-001 - ChatPanel 组件拆分

ChatPanel MUST be split into single-responsibility sub-components. The main component SHALL only be responsible for orchestration and state management.

#### Scenario: 渲染空会话时显示欢迎界面

**Given** 用户打开一个没有消息的会话
**When** ChatPanel 渲染
**Then** 应显示 GreetingScreen 组件，包含欢迎消息和建议卡片

#### Scenario: 渲染有消息的会话

**Given** 用户打开一个有消息的会话
**When** ChatPanel 渲染
**Then** 应显示 MessageList 组件，包含所有消息气泡

#### Scenario: ChatPanel 行数限制

**Given** ChatPanel.tsx 源代码
**When** 统计代码行数（不含空行和注释）
**Then** 有效代码行数应小于 150 行

---

### Requirement: COMP-002 - GreetingScreen 组件

The greeting screen MUST be extracted as an independent component. It SHALL accept callback functions to handle user interactions with suggestion cards.

#### Scenario: 点击建议卡片发送消息

**Given** 用户在欢迎界面
**When** 点击任意建议卡片
**Then** 应调用 `onSuggestionClick(text)` 回调，传递卡片文本

#### Scenario: 自定义建议卡片

**Given** GreetingScreen 组件
**When** 传入 `suggestions` prop
**Then** 应渲染自定义的建议卡片列表

---

### Requirement: COMP-003 - MessageEditor 组件

Message editing functionality MUST be separated from MessageBubble into an independent MessageEditor component.

#### Scenario: 进入编辑模式

**Given** 用户点击消息的编辑按钮
**When** MessageEditor 渲染
**Then** 应显示文本输入框，内容为原消息文本

#### Scenario: 提交编辑

**Given** 用户在 MessageEditor 中修改了内容
**When** 点击提交按钮或按 Enter
**Then** 应调用 `onSubmit(newContent)` 回调

#### Scenario: 取消编辑

**Given** 用户在 MessageEditor 中
**When** 点击取消按钮或按 Escape
**Then** 应调用 `onCancel()` 回调，不触发 onSubmit

---

### Requirement: COMP-004 - MessageBubble Props 精简

MessageBubble MUST only accept props required for display. It SHALL NOT include editing-related callbacks.

#### Scenario: MessageBubble Props 数量

**Given** MessageBubble 组件的 Props 接口
**When** 统计必需和可选 Props 总数
**Then** Props 总数应小于 8 个

#### Scenario: 展示型组件无副作用

**Given** MessageBubble 组件
**When** 渲染组件
**Then** 不应触发任何 API 调用或全局状态修改

---

## MODIFIED Requirements

### Requirement: COMP-005 - 组件文件组织

Chat-related components MUST be organized according to the following structure.

#### Scenario: 组件目录结构

**Given** `frontend/src/components/chat/` 目录
**When** 列出文件
**Then** 应包含以下文件：
- `ChatPanel.tsx`
- `GreetingScreen.tsx`
- `MessageList.tsx`
- `MessageBubble.tsx`
- `MessageEditor.tsx`
- `BranchNavigator.tsx`
- `ChatInput.tsx`
- `ModelSelector.tsx`
- `index.ts`
