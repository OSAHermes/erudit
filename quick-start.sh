#!/bin/bash
# Erudit - 快速开始

set -e

# 克隆仓库
if [ ! -d "erudit" ]; then
    echo "克隆 Erudit 仓库..."
    git clone https://github.com/trencps/erudit.git
    cd erudit
else
    cd erudit
    git pull
fi

# 设置环境变量
if [ ! -f .env ]; then
    cp .env.example .env
    echo "请编辑 .env 文件，设置 ADMIN_PASSWORD"
fi

# 启动服务
echo "启动 Erudit..."
docker compose up -d

echo ""
echo "======================================"
echo "  Erudit 部署完成！"
echo "======================================"
echo ""
echo "🌐 访问地址："
echo "   API:    http://$(hostname -I | awk '{print $1}'):8080"
echo "   文档:   http://$(hostname -I | awk '{print $1}'):8080/docs"
echo ""
echo "🔑 认证："
echo "   GET /api/auth/login?password=your_password"
echo ""
echo "📚 GitHub: https://github.com/trencps/erudit"
echo "======================================"
