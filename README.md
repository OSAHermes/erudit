# Erudit - 个人知识管理系统

<div align="center">

![Erudit](https://img.shields.io/badge/Erudit-v2.0-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-purple)
![SQLite](https://img.shields.io/badge/SQLite-3-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**优雅的知识沉淀平台**

[文档](#api-文档) · [部署](#快速开始) · [GitHub](https://github.com/trencps/erudit)

</div>

---

## ✨ 功能特性

### 📚 知识管理
- **分类管理** - 自由创建知识分类体系
- **标签系统** - 多维度标记，灵活检索
- **全文搜索** - SQLite FTS5 智能检索
- **分页浏览** - 高效分页，流畅体验

### 🔐 隐私安全
- **公开文章** - 分享给他人
- **私密文章** - 仅登录用户可见
- **加密文章** - AES-256 端到端加密
- **API 认证** - Bearer Token 安全机制

### ☁️ 云同步
- **GitHub 同步** - 自动备份到云端
- **增量同步** - 仅推送变更内容
- **加密保护** - 敏感内容不上传
- **定时任务** - GitHub Actions 自动执行

### 💾 备份恢复
- **一键备份** - 数据库 + 文件归档
- **历史版本** - 保留时间戳备份
- **在线下载** - 随时恢复数据

---

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/trencps/erudit.git
cd erudit

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置管理员密码

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps
```

### 方式二：手动部署

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行服务
python app.py
```

---

## 🌐 访问地址

| 服务 | 地址 |
|------|------|
| API | http://localhost:8080 |
| API 文档 | http://localhost:8080/docs |
| 健康检查 | http://localhost:8080/api/health |

---

## 📖 API 文档

### 认证

```bash
# 登录获取 Token
curl -X GET "http://localhost:8080/api/auth/login?password=your_password"
# 响应: {"token": "xxx", "username": "admin"}
```

### 文章

```bash
# 获取文章列表（分页）
curl "http://localhost:8080/api/articles?page=1&page_size=10" \
  -H "Authorization: Bearer ***"

# 全文搜索
curl "http://localhost:8080/api/search?keyword=AI" \
  -H "Authorization: Bearer ***"

# 创建文章
curl -X POST "http://localhost:8080/api/articles" \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "文章标题",
    "content": "# Markdown 内容",
    "tags": ["docker", "教程"],
    "is_public": true
  }'

# 加密文章
curl -X POST "http://localhost:8080/api/articles" \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "加密文章",
    "content": "敏感内容",
    "is_encrypted": true,
    "encryption_key": "my-secret-key"
  }'
```

### 分类

```bash
# 获取分类列表
curl "http://localhost:8080/api/categories" \
  -H "Authorization: Bearer ***"

# 创建分类
curl -X POST "http://localhost:8080/api/categories" \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{"name": "技术", "description": "技术文章"}'
```

### 备份

```bash
# 创建备份
curl -X POST "http://localhost:8080/api/backup" \
  -H "Authorization: Bearer ***"

# 查看备份列表
curl "http://localhost:8080/api/backups" \
  -H "Authorization: Bearer ***"

# 下载备份
curl "http://localhost:8080/api/backups/backup_20260821_100000.tar.gz" \
  -H "Authorization: Bearer ***" -o backup.tar.gz
```

---

## ⚙️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ADMIN_PASSWORD` | 管理员密码 | `admin123` |
| `JWT_SECRET` | JWT 密钥 | `change-me` |
| `KB_DB_PATH` | 数据库路径 | `/data/knowledge_base.db` |
| `KB_ARTICLES_DIR` | 文章目录 | `/articles` |
| `KB_BACKUP_DIR` | 备份目录 | `/data/backups` |

---

## 🔄 GitHub 同步

### 配置

```bash
# 创建 GitHub Personal Access Token
# Settings → Developer settings → Personal access tokens → Tokens (classic)
# 勾选 repo 权限

# 配置环境变量
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
export GITHUB_REPO=yourusername/erudit
export GITHUB_BRANCH=main
```

### 手动同步

```bash
# 执行同步
python sync.py

# 模拟运行（不提交）
python sync.py --dry-run

# 详细日志
python sync.py --log-level DEBUG
```

### GitHub Actions

仓库已配置自动同步，支持：
- **推送触发** - 推送到 main 分支时自动执行
- **定时触发** - 每天 UTC 00:00 自动同步
- **手动触发** - Actions 页面点击运行

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    Erudit API                        │
│              FastAPI + SQLite (FTS5)                │
├─────────────────────────────────────────────────────┤
│  Articles  │  Categories  │  Tags  │  Backups      │
│  (Markdown)│  (分类体系)   │ (标签) │  (归档)       │
├─────────────────────────────────────────────────────┤
│           Docker Container (Port 8080)              │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   GitHub Repository   │
              │   (云端备份 + 同步)    │
              └───────────────────────┘
```

---

## 🔒 安全特性

1. **密码哈希** - bcrypt 算法加密存储
2. **JWT 认证** - 无状态 Token 验证
3. **端到端加密** - AES-256 加密文章内容
4. **路径安全** - 防止备份文件路径遍历
5. **敏感过滤** - 备份时自动过滤密码字段

---

## 📝 许可证

MIT License - 自由使用、修改和分发

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

<div align="center">

**Erudit** - 让知识更有价值

</div>
