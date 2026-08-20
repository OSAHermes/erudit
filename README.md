# 个人知识库系统

单用户知识管理平台，支持：
- 分类和标签
- 文章加密
- 公开/私密文章
- Docker 部署
- GitHub 同步

## 功能特性

### 1. 文章管理
- 创建、编辑、删除文章
- Markdown 格式支持
- 分类管理
- 标签系统

### 2. 隐私控制
- 公开文章：任何人可访问
- 加密文章：需要密码解密
- 私密文章：仅登录用户可访问

### 3. 用户认证
- 管理员登录
- API Token 认证
- JWT 支持

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/trencps/knowledge-base.git
cd knowledge-base

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置密码等

# 启动服务
docker-compose up -d

# 访问
# Web UI: http://NAS_IP:8080
# API: http://NAS_IP:8080/api
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

## API 文档

### 认证

```bash
# 登录
POST /api/auth/login
Content-Type: application/json

{
  "password": "your_password"
}

# 响应
{
  "token": "xxx",
  "username": "admin"
}
```

### 文章

```bash
# 获取所有文章（公开）
GET /api/articles?public_only=true

# 获取单篇文章
GET /api/articles/{slug}?password=xxx

# 创建文章
POST /api/articles
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "文章标题",
  "content": "# Markdown 内容",
  "category_id": 1,
  "tags": ["docker", "教程"],
  "is_public": true,
  "is_encrypted": false
}

# 更新文章
PUT /api/articles/{slug}
Authorization: Bearer {token}

# 删除文章
DELETE /api/articles/{slug}
Authorization: Bearer {token}
```

### 分类

```bash
# 获取分类
GET /api/categories

# 创建分类
POST /api/categories
Authorization: Bearer {token}

{
  "name": "Docker",
  "description": "Docker 部署教程"
}

# 删除分类
DELETE /api/categories/{id}
Authorization: Bearer {token}
```

### 标签

```bash
# 获取所有标签
GET /api/tags

# 按标签筛选文章
GET /api/articles?tag=docker
```

### 统计

```bash
GET /api/stats
Authorization: Bearer {token}
```

## 加密功能

### 加密文章

```bash
POST /api/articles
Authorization: Bearer {token}

{
  "title": "加密文章",
  "content": "这是加密的内容",
  "is_encrypted": true,
  "encryption_key": "my-secret-key"
}
```

### 解密文章

```bash
# 使用密码访问
GET /api/articles/{slug}?password=my-secret-key

# 或使用 API Token
GET /api/articles/{slug}
Authorization: Bearer {token}
```

## GitHub 同步

### 自动推送文章到 GitHub

系统支持将文章同步到 GitHub 仓库：

```bash
# 配置 GitHub
export GITHUB_TOKEN=your_token
export GITHUB_REPO=trencps/knowledge-base
export GITHUB_BRANCH=main

# 同步
python sync.py --push
```

### 目录结构

```
knowledge-base/
├── app.py              # 主应用
├── sync.py             # GitHub 同步脚本
├── requirements.txt    # Python 依赖
├── docker-compose.yml  # Docker 配置
├── .env.example        # 环境变量模板
├── articles/           # 文章存储
│   ├── public/         # 公开文章
│   └── private/        # 私密文章
└── data/               # 数据库
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| ADMIN_PASSWORD | 管理员密码 | admin123 |
| JWT_SECRET | JWT 密钥 | 自动生成 |
| KB_DB_PATH | 数据库路径 | /data/knowledge_base.db |
| KB_ARTICLES_DIR | 文章目录 | /data/articles |

## 安全建议

1. **使用强密码**
   ```bash
   ADMIN_PASSWORD=your-strong-password
   ```

2. **启用 HTTPS**
   ```yaml
   # docker-compose.yml
   nginx:
     image: nginx:latest
     volumes:
       - ./nginx.conf:/etc/nginx/nginx.conf
       - ./certs:/certs
   ```

3. **限制访问 IP**
   ```yaml
   nginx:
     # 配置 IP 白名单
   ```

4. **定期备份**
   ```bash
   docker exec -v knowledge-base:/data backup
   ```

## 许可证

MIT License
