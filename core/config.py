"""
核心配置和工具函数
"""
import os
import sqlite3
import json
import secrets
import bcrypt
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager

# 配置
DB_PATH = os.environ.get("KB_DB_PATH", "/data/knowledge_base.db")
ARTICLES_DIR = os.environ.get("KB_ARTICLES_DIR", "/data/articles")
BACKUP_DIR = os.environ.get("KB_BACKUP_DIR", "/data/backups")
UPLOAD_DIR = os.environ.get("KB_UPLOAD_DIR", "/data/uploads")
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "7"))

# 确保目录存在
for d in [ARTICLES_DIR, BACKUP_DIR, UPLOAD_DIR]:
    os.makedirs(d, exist_ok=True)


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库"""
    with get_db() as conn:
        c = conn.cursor()
        # 文章表
        c.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                category_id INTEGER,
                tags TEXT,
                is_public INTEGER DEFAULT 1,
                is_encrypted INTEGER DEFAULT 0,
                encryption_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 分类表
        c.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Token 表
        c.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # FTS5 全文搜索
        c.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title, content, content='articles', content_rowid='rowid'
            )
        ''')
        # 触发器
        c.execute('''
            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles
            BEGIN
                INSERT INTO articles_fts(rowid, title, content)
                VALUES (new.rowid, new.title, new.content);
            END
        ''')
        c.execute('''
            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles
            BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, content)
                VALUES('delete', old.rowid, old.title, old.content);
            END
        ''')
        c.execute('''
            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles
            BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, content)
                VALUES('delete', old.rowid, old.title, old.content);
                INSERT INTO articles_fts(rowid, title, content)
                VALUES (new.rowid, new.title, new.content);
            END
        ''')
        # 版本历史表
        c.execute('''
            CREATE TABLE IF NOT EXISTS article_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                version INTEGER,
                title TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        ''')
        # 索引
        c.execute("CREATE INDEX IF NOT EXISTS idx_articles_slug ON articles(slug)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens(token)")


def generate_slug(title: str) -> str:
    """生成文章 slug"""
    slug = title.lower().strip()
    slug = slug.replace(" ", "-")
    slug = slug.replace("/", "-")
    slug = slug.replace(".", "-")
    slug = slug.replace(",", "-")
    slug = slug.replace("，", "-")
    slug = slug.replace("。", "-")
    slug = slug.replace("、", "-")
    slug = slug.replace(":", "-")
    slug = slug.replace("：", "-")
    # 移除特殊字符
    import re
    slug = re.sub(r'[^\w\u4e00-\u9fff-]', '', slug)
    slug = slug[:50]
    # 确保唯一
    with get_db() as conn:
        cursor = conn.execute("SELECT slug FROM articles WHERE slug = ?", (slug,))
        if cursor.fetchone():
            slug = f"{slug}-{secrets.token_hex(4)}"
    return slug


def verify_password(password: str) -> bool:
    """验证密码"""
    if not ADMIN_PASSWORD_HASH:
        # ⚠️ 安全警告：未设置密码哈希时使用默认密码
        # 请通过环境变量 ADMIN_PASSWORD_HASH 设置安全的密码哈希
        import warnings
        warnings.warn("使用默认密码 'admin123'，请在生产环境中设置 ADMIN_PASSWORD_HASH", UserWarning)
        return password == "admin123"
    return bcrypt.checkpw(password.encode(), ADMIN_PASSWORD_HASH.encode())


def validate_token(token: str) -> dict:
    """验证 Token"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tokens WHERE token = ? AND expires_at > ?",
            (token, datetime.utcnow().isoformat())
        ).fetchone()
    return dict(row) if row else None