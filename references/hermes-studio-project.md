# Hermes Studio 项目介绍

## 基本信息

| 项目 | 信息 |
|------|------|
| **名称** | Hermes Studio |
| **仓库** | https://github.com/EKKOLearnAI/hermes-studio |
| **语言** | TypeScript |
| **Stars** | 10512+ |
| **Forks** | 1280+ |
| **许可证** | MIT |
| **文档** | https://hermes-studio.ai |

---

## 项目简介

Hermes Studio 是 Hermes Agent 的桌面应用、本地运行时和 Web 控制台。提供了一个统一的可视化界面，用于管理 AI Agent 会话、构建可视化工作流、管理模型和配置，同时保持所有数据本地运行。

---

## 核心功能

### 1. AI 聊天
- 实时流式对话（Socket.IO）
- 多会话管理
- Markdown 渲染与代码复制
- 工具调用详情展开
- 文件上传/下载
- 内联预览（HTML/PDF/图片等）

### 2. 平台渠道
支持 10 个平台统一管理：
- Telegram、Discord、Slack
- WhatsApp、Matrix
- 飞书、钉钉、QQBot
- 微信、企业微信

### 3. 使用分析
- Token 使用统计
- 会话数量与日均值
- 成本追踪
- 模型分布图
- 30 天趋势分析

### 4. 定时任务
- Cron 表达式管理
- 立即触发执行
- 预设模板

### 5. 看板
- 任务创建与跟踪
- 状态移动
- 与 Web UI 状态共享

---

## 安装方式

### 桌面应用
从 [Releases](https://github.com/EKKOLearnAI/hermes-studio/releases/latest) 下载。

### npm 全局安装
```bash
npm install -g hermes-web-ui
hermes-web-ui start
```

### Docker 部署
```bash
docker run -d -p 6060:6060 -v ~/.hermes:/root/.hermes ghcr.io/eKKOLearnAI/hermes-studio:latest
```

---

## 技术架构

```
┌─────────────────────────────────────────┐
│           Hermes Studio                 │
│      Electron + React + Socket.IO       │
├─────────────────────────────────────────┤
│  Chat │ Workflows │ Kanban │ Jobs      │
├─────────────────────────────────────────┤
│      Hermes Agent Bridge (Local)        │
├─────────────────────────────────────────┤
│  SQLite │ Config.yaml │ .env            │
└─────────────────────────────────────────┘
              │
              ▼
    ┌─────────────────┐
    │ Hermes Agent    │
    │  (Python/FastAPI)│
    └─────────────────┘
```

---

## 与 Erudit 集成

```bash
# Erudit API 示例
curl -X POST "http://localhost:8000/api/articles" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"AI 项目记录","content":"# Hermes Studio 介绍..."}'
```

---

## 总结

Hermes Studio 是 Hermes Agent 的必备管理工具，提供：
1. 统一界面管理所有平台渠道
2. 本地优先，数据存储在本地
3. 可视化工作流构建
4. 丰富的工作空间工具
5. 多平台分发（桌面/npm/Docker）

---

*项目地址：https://github.com/EKKOLearnAI/hermes-studio*
*文档地址：https://hermes-studio.ai*