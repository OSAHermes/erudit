#!/bin/bash
# 个人知识库系统 - 快速开始

set -e

# 克隆仓库
if [ ! -d "knowledge-base" ]; then
    echo "克隆仓库..."
    git clone https://github.com/trencps/knowledge-base.git
    cd knowledge-base
else
    cd knowledge-base
    git pull
fi

# 设置环境变量
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 文件，设置 ADMIN_PASSWORD"
fi

# 启动服务
echo "启动服务..."
docker compose up -d

echo ""
echo "✅ 部署完成！"
echo ""
echo "📍 访问地址："
echo "   Web UI: http://$(hostname -I | awk '{print $1}'):8080"
echo "   API 文档: http://$(hostname -I | awk '{print $1}'):8080/docs"
echo ""
echo "🔑 认证方式："
echo "   POST /api/auth/login"
echo "   {\"password\": \"your-password\"}"
echo ""
echo "📚 GitHub 仓库："
echo "   https://github.com/trencps/knowledge-base"
