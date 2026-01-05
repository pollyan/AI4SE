# 前端组件清单 (Component Inventory)

> **生成日期**: {{date}}
> **框架**: React 19 + Tailwind CSS
> **位置**: `tools/frontend/src/components`

本项目的 UI 采用原子化设计，主要组件库位于 `tools/frontend`，旨在为所有子应用提供统一的视觉风格。

## 1. 布局组件 (Layout)

负责页面的整体结构和导航。

- **Layout.tsx**: 通用布局容器，包含 `Navbar` 和 `Footer`，处理全局的 Padding 和 Max-width。
- **Navbar.tsx**: 顶部导航栏。
  - **特性**: 响应式设计（移动端折叠菜单），支持路由高亮。
  - **链接**: 意图测试、AI 智能体、文档、GitHub。
- **Footer.tsx**: 底部版权和链接区域。

## 2. 页面级组件 (Pages)

### Home (`src/pages/Home`)
着陆页 (Landing Page)，由多个 Section 组成：

- **HeroSection**: 首屏大图，包含 Slogan 和 CTA 按钮。
- **FeaturesSection**: 核心特性展示网格。
- **UseCasesSection**: 应用场景轮播/列表。
- **VideoSection**: 演示视频嵌入组件。
- **QuickLinks**: 快速访问入口。

### Profile (`src/pages/Profile`)
用户个人中心页面。

- **UserProfile**: 展示用户基本信息。
- **SettingsForm**: 用户偏好设置表单（如 AI Key 配置）。

## 3. 设计规范 (Design Tokens)

基于 Tailwind CSS 的配置 (`tailwind.config.js`)：

- **Colors**: 使用自定义的 Primary/Secondary 色板，支持 Dark Mode。
- **Typography**: 统一的字体栈 (Inter/System UI)。
- **Spacing**: 标准化的间距系统 (4px grid)。

## 4. 组件复用策略

目前 `tools/frontend` 作为一个独立的 React 应用运行。未来计划将其中的通用组件 (`Navbar`, `Footer`, `Button`) 提取为独立的 NPM 包 (`@ai4se/ui`)，以便 `intent-tester` 和 `ai-agents` 的前端也能直接引用，进一步统一全栈的 UI 体验。
