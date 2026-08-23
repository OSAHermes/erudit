"""
备份模块
"""
import os
import tarfile
import io
import shutil
from datetime import datetime, timedelta
from core.config import DB_PATH, BACKUP_DIR, ARTICLES_DIR, get_db


def create_backup() -> dict:
    """创建数据库备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.tar.gz"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    with tarfile.open(backup_path, "w:gz") as tar:
        # 添加数据库
        if os.path.exists(DB_PATH):
            tar.add(DB_PATH, arcname="knowledge_base.db")
        
        # 添加文章文件
        if os.path.exists(ARTICLES_DIR):
            tar.add(ARTICLES_DIR, arcname="articles")
    
    return {"message": "备份创建成功", "filename": backup_filename}


def get_backups() -> list:
    """获取备份列表"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backups = []
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".tar.gz"):
            filepath = os.path.join(BACKUP_DIR, f)
            stat = os.stat(filepath)
            backups.append({
                "filename": f,
                "size": stat.st_size,
                "size_readable": format_size(stat.st_size),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    return sorted(backups, key=lambda x: x["created_at"], reverse=True)


def download_backup(filename: str) -> tuple:
    """下载备份文件"""
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return None, 404
    
    with open(filepath, "rb") as f:
        content = f.read()
    
    return content, 200


def delete_backup(filename: str) -> dict:
    """删除备份"""
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": "备份不存在"}
    
    os.remove(filepath)
    return {"message": "备份删除成功"}


def clean_old_backups(retention_days: int = 7) -> dict:
    """清理旧备份"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".tar.gz"):
                filepath = os.path.join(BACKUP_DIR, f)
                if datetime.fromtimestamp(os.path.getmtime(filepath)) < cutoff:
                    os.remove(filepath)
                    deleted += 1
    
    return {"message": f"清理了 {deleted} 个旧备份", "deleted": deleted}



def restore_backup(filename: str, target_db_path: str = None) -> dict:
    """从备份恢复数据库"""
    import tarfile
    import shutil
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(backup_path):
        return {"error": "备份文件不存在"}
    
    # 创建备份以防万一
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    emergency_backup = os.path.join(BACKUP_DIR, f"emergency_{timestamp}.tar.gz")
    if os.path.exists(DB_PATH):
        with tarfile.open(emergency_backup, "w:gz") as tar:
            tar.add(DB_PATH, arcname="knowledge_base.db")
    
    # 恢复
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall()
        
        restored_db = os.path.join(".", "knowledge_base.db")
        if os.path.exists(restored_db):
            target = target_db_path or DB_PATH
            shutil.move(restored_db, target)
            return {"message": f"恢复成功，目标: {target}", "emergency_backup": emergency_backup}
        return {"error": "恢复失败: 未找到数据库文件"}
    except Exception as e:
        return {"error": f"恢复失败: {str(e)}"}


def format_size(bytes_size: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"