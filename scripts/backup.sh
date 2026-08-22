# Erudit 备份脚本

```bash
#!/bin/bash
# Erudit 备份脚本
# 使用方法: ./backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/data/knowledge-base/backups"
DB_PATH="/opt/data/knowledge-base/data/knowledge_base.db"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
if [ -f "$DB_PATH" ]; then
    cp $DB_PATH $BACKUP_DIR/knowledge_base_$DATE.db
    echo "✅ 数据库备份完成: knowledge_base_$DATE.db"
else
    echo "⚠️  数据库文件不存在: $DB_PATH"
fi

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
echo "🧹 已清理7天前的备份"

echo "=== 备份完成 ==="
```