#!/bin/bash
set -e

echo "=== Erudit 部署脚本 ==="
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误：Docker 未安装"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "错误：Docker Compose 未安装"
    exit 1
fi

# 创建数据目录
mkdir -p /opt/data/erudit/data
mkdir -p /opt/data/erudit/articles

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cat > .env << 'ENVEOF'
ADMIN_PASSWORD=admin123
JWT_SECRET=change-me-to-random-secret
KB_DB_PATH=/data/knowledge_base.db
KB_ARTICLES_DIR=/articles
KB_BACKUP_DIR=/data/backups
ENVEOF
    echo "请编辑 .env 文件，设置强密码！"
fi

# 启动服务
echo "启动 Erudit..."
docker compose up -d

echo ""
echo "✅ 部署完成！"
echo ""
echo "🌐 访问地址："
echo "   API:    http://$(hostname -I | awk '{print $1}'):8080"
echo "   文档:   http://$(hostname -I | awk '{print $1}'):8080/docs"
echo "   健康:   http://$(hostname -I | awk '{print $1}'):8080/api/health"
echo ""
echo "🔑 默认密码：admin123"
echo "⚠️  请先修改 .env 中的 ADMIN_PASSWORD！"
echo ""
echo "📚 GitHub: https://github.com/trencps/erudit"
