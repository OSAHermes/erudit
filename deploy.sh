#!/bin/bash
set -e

echo "=== 个人知识库系统部署脚本 ==="

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
mkdir -p /opt/data/knowledge-base/data
mkdir -p /opt/data/knowledge-base/articles

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cat > .env << 'ENVEOF'
ADMIN_PASSWORD=admin123
JWT_SECRET=change-me-to-random-secret
KB_DB_PATH=/data/knowledge_base.db
KB_ARTICLES_DIR=/articles
ENVEOF
    echo "请编辑 .env 文件，设置强密码！"
fi

# 启动服务
echo "启动服务..."
docker compose up -d

echo ""
echo "部署完成！"
echo "访问地址：http://$(hostname -I | awk '{print $1}'):8080"
echo "API 文档：http://$(hostname -I | awk '{print $1}'):8080/docs"
echo ""
echo "默认管理员密码：admin123"
echo "请先修改 .env 中的 ADMIN_PASSWORD！"
