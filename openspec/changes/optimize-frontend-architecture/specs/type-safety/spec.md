# Spec: type-safety

## 概述

定义前端类型安全规范，消除类型隐患，增强代码可靠性。

---

## ADDED Requirements

### Requirement: TYPE-001 - ID 类型统一

All entity IDs MUST be unified to string type.

#### Scenario: Message ID 类型

**Given** Message 类型定义
**When** 检查 `id` 字段类型
**Then** 类型应为 `string`，不包含 `number`

#### Scenario: User ID 类型

**Given** User 类型定义
**When** 检查 `id` 字段类型
**Then** 类型应为 `string`，不包含 `number`

#### Scenario: Conversation ID 类型

**Given** Conversation 类型定义
**When** 检查 `id` 字段类型
**Then** 类型应为 `string`

#### Scenario: senderId 类型

**Given** Message 类型定义
**When** 检查 `senderId` 字段类型
**Then** 类型应为 `string`（AI 消息使用特殊值如 `"ai"` 或 `"-1"`）

---

### Requirement: TYPE-002 - 禁止 any 类型

The codebase MUST NOT use `any` type.

#### Scenario: 组件 Props 无 any

**Given** 任意组件的 Props 接口定义
**When** 检查所有字段类型
**Then** 不应包含 `any` 类型

#### Scenario: 函数参数无 any

**Given** 任意函数定义
**When** 检查参数类型
**Then** 不应使用 `any` 作为参数类型

#### Scenario: API 响应类型明确

**Given** API 响应处理代码
**When** 检查响应数据类型
**Then** 应使用具体的类型定义，不使用 `any`

---

### Requirement: TYPE-003 - 严格 null 检查

Strict null checks MUST be enabled. Values that may be null/undefined MUST be properly handled.

#### Scenario: 可选字段访问

**Given** 访问可选字段（如 `message.parentId`）
**When** 编译代码
**Then** 应进行 null 检查或使用可选链操作符

#### Scenario: 数组索引访问

**Given** 通过索引访问数组元素
**When** 编译代码
**Then** 应检查索引是否越界或使用安全访问方式

---

### Requirement: TYPE-004 - 图标组件类型

Icon components MUST use correct types instead of any.

#### Scenario: Lucide 图标类型

**Given** 接收图标作为 prop 的组件
**When** 定义图标 prop 类型
**Then** 应使用 `LucideIcon` 或 `React.ComponentType<LucideProps>` 类型

#### Scenario: 图标 prop 使用

**Given** 传递图标给组件
**When** 编译代码
**Then** 只有有效的 Lucide 图标才能通过类型检查

---

### Requirement: TYPE-005 - 事件处理器类型

Event handlers MUST have explicit type definitions.

#### Scenario: onClick 处理器类型

**Given** 按钮的 onClick 处理器
**When** 定义处理器类型
**Then** 应为 `React.MouseEventHandler<HTMLButtonElement>` 或等效类型

#### Scenario: onChange 处理器类型

**Given** 输入框的 onChange 处理器
**When** 定义处理器类型
**Then** 应为 `React.ChangeEventHandler<HTMLInputElement>` 或等效类型

---

### Requirement: TYPE-006 - TypeScript 严格模式

tsconfig MUST enable strict mode options.

#### Scenario: strict 模式启用

**Given** `tsconfig.app.json` 配置
**When** 检查 `compilerOptions.strict`
**Then** 值应为 `true`

#### Scenario: noImplicitAny 启用

**Given** `tsconfig.app.json` 配置
**When** 检查 `compilerOptions.noImplicitAny`
**Then** 值应为 `true`（或由 strict 隐含启用）

#### Scenario: strictNullChecks 启用

**Given** `tsconfig.app.json` 配置
**When** 检查 `compilerOptions.strictNullChecks`
**Then** 值应为 `true`（或由 strict 隐含启用）

---

## MODIFIED Requirements

### Requirement: TYPE-007 - 类型文件组织

Type definitions MUST be organized by domain or centrally managed.

#### Scenario: 核心类型集中定义

**Given** `frontend/src/types/index.ts` 文件
**When** 检查内容
**Then** 应包含所有共享类型定义（User, Message, Conversation 等）

#### Scenario: 类型导出完整

**Given** `types/index.ts` 文件
**When** 检查导出
**Then** 所有公共类型应被导出供其他模块使用
