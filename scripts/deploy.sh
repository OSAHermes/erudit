# Erudit 快速部署脚本

## 部署脚本

```bash
#!/bin/bash
set -e

PROJECT_DIR="/opt/data/knowledge-base"

echo "=== Erudit 部署脚本 ==="

# 1. 进入项目目录
cd $PROJECT_DIR

# 2. 停止现有容器
docker-compose down 2>/dev/null || true

# 3. 重新构建并启动
docker-compose up -d --build

# 4. 等待服务启动
sleep 5

# 5. 验证服务
echo "检查服务状态..."
curl -s http://localhost:8000/api/health || echo "服务未响应"

echo "=== 部署完成 ==="
echo "访问地址: http://localhost:8000/"
echo "默认密码: admin123"
```