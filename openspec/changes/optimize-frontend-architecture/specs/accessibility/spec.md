# Spec: accessibility

## 概述

定义前端无障碍访问（A11y）规范，确保应用符合 WCAG 2.1 AA 标准。

---

## ADDED Requirements

### Requirement: A11Y-001 - ARIA 属性

All interactive elements MUST have appropriate ARIA attributes.

#### Scenario: 图标按钮具有 aria-label

**Given** 一个仅包含图标的按钮（如发送按钮）
**When** 渲染该按钮
**Then** 应具有 `aria-label` 属性，描述按钮功能

#### Scenario: 切换按钮具有 aria-pressed

**Given** 一个切换状态的按钮（如深度搜索开关）
**When** 渲染该按钮
**Then** 应具有 `aria-pressed` 属性，值为 `true` 或 `false`

#### Scenario: 流式内容具有 aria-live

**Given** AI 正在流式输出回复内容
**When** 渲染消息气泡
**Then** 应具有 `aria-live="polite"` 和 `aria-busy="true"`

#### Scenario: 流式完成后移除 aria-busy

**Given** AI 流式输出完成
**When** 更新消息气泡
**Then** `aria-busy` 应变为 `false`

#### Scenario: 当前会话具有 aria-current

**Given** 侧边栏显示会话列表
**When** 某会话为当前活动会话
**Then** 该会话项应具有 `aria-current="page"`

---

### Requirement: A11Y-002 - 键盘导航

All functionality MUST be accessible via keyboard.

#### Scenario: Tab 顺序合理

**Given** 用户使用 Tab 键导航
**When** 按 Tab 键
**Then** 焦点应按逻辑顺序移动：侧边栏 → 模型选择 → 消息列表 → 输入框

#### Scenario: Escape 关闭模态框

**Given** 用户打开了模态框（如主题设置）
**When** 按 Escape 键
**Then** 模态框应关闭，焦点返回到触发元素

#### Scenario: Enter 发送消息

**Given** 焦点在输入框内
**When** 按 Enter 键
**Then** 应发送消息（除非按 Shift+Enter 换行）

#### Scenario: 方向键导航列表

**Given** 焦点在会话列表或消息列表
**When** 按上下方向键
**Then** 焦点应在列表项之间移动

---

### Requirement: A11Y-003 - 焦点管理

Modals and dynamic content MUST properly manage focus.

#### Scenario: 模态框焦点陷阱

**Given** 模态框打开
**When** 用户按 Tab 键
**Then** 焦点应限制在模态框内循环

#### Scenario: 模态框打开时自动聚焦

**Given** 模态框即将打开
**When** 模态框完成渲染
**Then** 焦点应自动移动到模态框内的第一个可聚焦元素

#### Scenario: 模态框关闭时恢复焦点

**Given** 模态框打开时焦点从某按钮触发
**When** 模态框关闭
**Then** 焦点应返回到原触发按钮

---

### Requirement: A11Y-004 - 焦点可见性

Focus state MUST be clearly visible.

#### Scenario: 键盘焦点样式

**Given** 用户使用键盘导航
**When** 元素获得焦点
**Then** 应显示清晰的焦点指示器（focus-visible 样式）

#### Scenario: 鼠标点击不显示焦点环

**Given** 用户使用鼠标点击按钮
**When** 按钮获得焦点
**Then** 不应显示焦点环（仅对 :focus-visible 应用样式）

---

### Requirement: A11Y-005 - 动画减弱

The application MUST respect user's animation preference settings.

#### Scenario: 系统设置减少动画

**Given** 用户系统设置了 `prefers-reduced-motion: reduce`
**When** 页面加载
**Then** 所有动画应被禁用或缩短至近乎瞬时

#### Scenario: Framer Motion 尊重偏好

**Given** 用户系统设置了减少动画
**When** 使用 Framer Motion 组件
**Then** 动画应自动降级为即时过渡

---

### Requirement: A11Y-006 - 颜色对比度

Text-to-background contrast ratio MUST meet WCAG AA standards.

#### Scenario: 正常文本对比度

**Given** 任意正常大小文本（< 18px 或 < 14px bold）
**When** 计算与背景的对比度
**Then** 对比度应大于等于 4.5:1

#### Scenario: 大文本对比度

**Given** 任意大文本（>= 18px 或 >= 14px bold）
**When** 计算与背景的对比度
**Then** 对比度应大于等于 3:1

#### Scenario: 深色模式对比度

**Given** 应用处于深色模式
**When** 检查文本与背景对比度
**Then** 所有文本对比度应符合 AA 标准

---

### Requirement: A11Y-007 - 错误提示

Error messages MUST be accessible to assistive technologies.

#### Scenario: 错误消息具有 role=alert

**Given** 表单验证失败或 API 请求失败
**When** 显示错误消息
**Then** 错误消息容器应具有 `role="alert"`

#### Scenario: 表单错误关联

**Given** 输入框验证失败
**When** 显示错误消息
**Then** 输入框应通过 `aria-describedby` 关联到错误消息
