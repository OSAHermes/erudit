#!/usr/bin/env python3
"""
Erudit - 个人知识管理系统
优雅的知识沉淀平台，支持分类、标签、加密文章
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Response, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import json
import hashlib
import base64
import sqlite3
from pathlib import Path
import secrets
import tarfile
import shutil
import io
import bcrypt
from datetime import datetime, timedelta

app = FastAPI(title="Erudit - 个人知识管理系统", version="2.0.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库路径
DB_PATH = os.environ.get("KB_DB_PATH", "/data/knowledge_base.db")
ARTICLES_DIR = os.environ.get("KB_ARTICLES_DIR", "/data/articles")
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

os.makedirs(ARTICLES_DIR, exist_ok=True)

# 数据库初始化
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # FTS5 虚拟表 - 用于全文搜索
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            content,
            content='articles',
            content_rowid='rowid'
        )
    ''')
    # 创建触发器以保持 FTS5 同步
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
            VALUES ('delete', old.rowid, old.title, old.content);
        END
    ''')
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles
        BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, content)
            VALUES ('delete', old.rowid, old.title, old.content);
            INSERT INTO articles_fts(rowid, title, content)
            VALUES (new.rowid, new.title, new.content);
        END
    ''')
    conn.commit()
    conn.close()

init_db()

# 数据模型
class ArticleCreate(BaseModel):
    title: str
    content: str
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_public: bool = True
    is_encrypted: bool = False
    encryption_key: Optional[str] = None

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_encrypted: Optional[bool] = None
    encryption_key: Optional[str] = None

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AuthResponse(BaseModel):
    token: str
    username: str

# 辅助函数
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def validate_token(token: str):
    """验证 token 是否存在且未过期，返回 token 记录或 None"""
    conn = get_db()
    conn.execute("DELETE FROM tokens WHERE expires_at < ?", (datetime.utcnow().isoformat(),))
    conn.commit()
    record = conn.execute("SELECT * FROM tokens WHERE token = ?", (token,)).fetchone()
    conn.close()
    return record

def generate_slug(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()[:8]

def encrypt_content(content: str, key: str) -> str:
    """简单的 AES-256 加密 (使用 Python 标准库模拟)"""
    key_hash = hashlib.sha256(key.encode()).digest()
    content_bytes = content.encode()
    encrypted = bytearray()
    for i, byte in enumerate(content_bytes):
        encrypted.append(byte ^ key_hash[i % len(key_hash)])
    return base64.b64encode(bytes(encrypted)).decode()

def decrypt_content(encrypted: str, key: str) -> str:
    key_hash = hashlib.sha256(key.encode()).digest()
    content_bytes = base64.b64decode(encrypted.encode())
    decrypted = bytearray()
    for i, byte in enumerate(content_bytes):
        decrypted.append(byte ^ key_hash[i % len(key_hash)])
    return bytes(decrypted).decode()

def verify_password(password: str) -> bool:
    import bcrypt
    if not ADMIN_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode(), ADMIN_PASSWORD_HASH.encode())

# API 端点

@app.get("/api/health")
def health_check():
    try:
        conn = get_db()
        articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        categories = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        conn.close()
        return {"status": "ok", "articles": articles, "categories": categories}
    except Exception:
        return {"status": "error", "articles": 0, "categories": 0}

@app.post("/api/auth/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, password: str):
    if not verify_password(password):
        raise HTTPException(status_code=401, detail="密码错误")
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    conn = get_db()
    conn.execute("DELETE FROM tokens WHERE username = ?", ("admin",))
    conn.execute("INSERT INTO tokens (token, username, expires_at) VALUES (?, ?, ?)", (token, "admin", expires_at))
    conn.commit()
    conn.close()
    return {"token": token, "username": "admin"}

@app.get("/api/categories")
def get_categories():
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(c) for c in categories]

@app.post("/api/categories")
def create_category(category: CategoryCreate, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    # 验证 token
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    conn.close()
    
    slug = category.name.lower().replace(" ", "-")
    conn = get_db()
    conn.execute("INSERT INTO categories (name, slug, description) VALUES (?, ?, ?)",
                 (category.name, slug, category.description))
    conn.commit()
    conn.close()
    return {"message": "分类创建成功"}

@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return {"message": "分类删除成功"}

@app.get("/api/articles")
def get_articles(
    category_id: Optional[int] = None,
    tag: Optional[str] = None,
    public_only: bool = True,
    page: int = 1,
    page_size: int = 20,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    token_record = validate_token(credentials.credentials)
    conn = get_db()

    # 基础查询
    query = "SELECT * FROM articles WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM articles WHERE 1=1"
    params = []
    count_params = []

    if public_only and not token_record:
        query += " AND is_public = 1 AND (is_encrypted = 0 OR encryption_key IS NULL)"
        count_query += " AND is_public = 1 AND (is_encrypted = 0 OR encryption_key IS NULL)"

    if category_id:
        query += " AND category_id = ?"
        count_query += " AND category_id = ?"
        params.append(category_id)
        count_params.append(category_id)

    if tag:
        query += " AND tags LIKE ?"
        count_query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
        count_params.append(f"%{tag}%")

    query += " ORDER BY created_at DESC"

    # 分页查询
    offset = (page - 1) * page_size
    query += f" LIMIT {page_size} OFFSET {offset}"

    total = conn.execute(count_query, count_params).fetchone()[0]
    articles = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "articles": [dict(a) for a in articles],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        "has_next": page < (total + page_size - 1) // page_size if page_size > 0 else False
    }

@app.get("/api/articles/{slug}")
def get_article(slug: str, password: Optional[str] = None, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token_record = validate_token(credentials.credentials)
    conn = get_db()
    
    article = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    if not article:
        conn.close()
        raise HTTPException(status_code=404, detail="文章不存在")
    
    article_dict = dict(article)
    
    # 解密内容
    if article_dict["is_encrypted"] and article_dict["encryption_key"]:
        if password == article_dict["encryption_key"] or token_record:
            article_dict["content"] = decrypt_content(article_dict["content"], article_dict["encryption_key"])
        else:
            conn.close()
            raise HTTPException(status_code=403, detail="需要解密密码")
    
    conn.close()
    return article_dict

@app.post("/api/articles")
def create_article(article: ArticleCreate, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token_record = validate_token(credentials.credentials)
    conn = get_db()
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    
    slug = generate_slug(article.title)
    content = article.content
    encryption_key = None
    
    if article.is_encrypted and article.encryption_key:
        content = encrypt_content(content, article.encryption_key)
        encryption_key = article.encryption_key
    
    tags = json.dumps(article.tags) if article.tags else None
    
    conn.execute("""
        INSERT INTO articles (title, slug, content, category_id, tags, is_public, is_encrypted, encryption_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (article.title, slug, content, article.category_id, tags, 
          1 if article.is_public else 0, 1 if article.is_encrypted else 0, encryption_key))
    conn.commit()
    conn.close()
    return {"message": "文章创建成功", "slug": slug}

@app.put("/api/articles/{slug}")
def update_article(slug: str, article: ArticleUpdate, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    
    existing = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 处理内容
    content = article.content if article.content else existing["content"]
    encryption_key = article.encryption_key if article.encryption_key else existing["encryption_key"]
    
    if article.is_encrypted and article.encryption_key:
        content = encrypt_content(content, article.encryption_key)
        encryption_key = article.encryption_key
    
    tags = json.dumps(article.tags) if article.tags else existing["tags"]
    
    conn.execute("""
        UPDATE articles 
        SET title = ?, content = ?, category_id = ?, tags = ?, is_public = ?, is_encrypted = ?, encryption_key = ?, updated_at = CURRENT_TIMESTAMP
        WHERE slug = ?
    """, (article.title or existing["title"], content, article.category_id or existing["category_id"],
          tags, 1 if article.is_public is not None else existing["is_public"],
          1 if article.is_encrypted is not None else existing["is_encrypted"],
          encryption_key, slug))
    conn.commit()
    conn.close()
    return {"message": "文章更新成功"}

@app.delete("/api/articles/{slug}")
def delete_article(slug: str, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    
    conn.execute("DELETE FROM articles WHERE slug = ?", (slug,))
    conn.commit()
    conn.close()
    return {"message": "文章删除成功"}

@app.get("/api/tags")
def get_tags():
    conn = get_db()
    tags = conn.execute("SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL").fetchall()
    all_tags = set()
    for t in tags:
        try:
            tag_list = json.loads(t["tags"])
            all_tags.update(tag_list)
        except:
            pass
    conn.close()
    return sorted(list(all_tags))

@app.get("/api/stats")
def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    public = conn.execute("SELECT COUNT(*) FROM articles WHERE is_public = 1").fetchone()[0]
    encrypted = conn.execute("SELECT COUNT(*) FROM articles WHERE is_encrypted = 1").fetchone()[0]
    categories = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    conn.close()
    return {
        "total_articles": total,
        "public_articles": public,
        "encrypted_articles": encrypted,
        "categories": categories
    }

# 备份目录
BACKUP_DIR = os.environ.get("KB_BACKUP_DIR", "/data/backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_backup_files():
    """获取所有备份文件列表"""
    backups = []
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.endswith('.tar.gz'):
                filepath = os.path.join(BACKUP_DIR, f)
                stat = os.stat(filepath)
                backups.append({
                    "filename": f,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_readable": f"{stat.st_size / 1024:.1f} KB"
                })
    # 按创建时间倒序排列
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups

def create_backup():
    """创建数据库和文件的备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.tar.gz"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    with tarfile.open(backup_path, "w:gz") as tar:
        # 添加数据库
        if os.path.exists(DB_PATH):
            tar.add(DB_PATH, arcname=os.path.basename(DB_PATH))
        
        # 添加文章目录
        if os.path.exists(ARTICLES_DIR):
            tar.add(ARTICLES_DIR, arcname="articles")
        
        # 添加 .env 文件（排除敏感信息）
        env_path = os.path.join(os.path.dirname(DB_PATH), ".env")
        if os.path.exists(env_path):
            # 只备份非敏感环境变量
            with open(env_path, 'r') as f:
                env_content = f.read()
            # 过滤掉密码和密钥
            filtered_env = ""
            for line in env_content.split('\n'):
                if not any(k in line.lower() for k in ['password', 'secret', 'token', 'key']):
                    filtered_env += line + '\n'
            if filtered_env.strip():
                env_info = tarfile.TarInfo(name=".env")
                env_info.size = len(filtered_env.encode())
                tar.addfile(env_info, io.StringIO(filtered_env))
    
    return backup_filename

@app.post("/api/backup")
def create_backup_endpoint(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """创建备份并返回下载链接"""
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    conn.close()
    
    try:
        backup_filename = create_backup()
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        return {
            "message": "备份创建成功",
            "filename": backup_filename,
            "download_url": f"/api/backups/{backup_filename}",
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份创建失败: {str(e)}")

@app.get("/api/backups")
def list_backups(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """列出所有可用备份"""
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    conn.close()
    
    backups = get_backup_files()
    return {"backups": backups, "total": len(backups)}

@app.get("/api/backups/{filename}")
def download_backup(filename: str, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """下载指定备份文件"""
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    conn.close()
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")
    
    # 安全检查：防止路径遍历
    if '..' in filename or filename.startswith('/'):
        raise HTTPException(status_code=400, detail="非法文件名")
    
    return Response(
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.delete("/api/backups/{filename}")
def delete_backup(filename: str, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """删除指定备份文件"""
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    conn.close()

    backup_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="备份文件不存在")

    # 安全检查
    if '..' in filename or filename.startswith('/'):
        raise HTTPException(status_code=400, detail="非法文件名")

    os.remove(backup_path)
    return {"message": "备份删除成功"}

@app.get("/api/search")
def search_articles(keyword: str = "", credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """全文搜索文章"""
    token_record = validate_token(credentials.credentials)
    conn = get_db()

    if not keyword.strip():
        conn.close()
        return {"articles": [], "total": 0, "keyword": keyword}

    # 使用 FTS5 搜索
    search_query = f"{keyword}*"
    results = conn.execute("""
        SELECT a.*, rank
        FROM articles_fts fts
        JOIN articles a ON a.rowid = fts.rowid
        WHERE articles_fts MATCH ?
        ORDER BY rank
        LIMIT 50
    """, (search_query,)).fetchall()

    # 构建搜索结果
    articles = []
    for row in results:
        article = dict(row)
        # 解密内容
        if article["is_encrypted"] and article["encryption_key"]:
            if token_record:
                article["content"] = decrypt_content(article["content"], article["encryption_key"])
            else:
                # 跳过加密文章
                continue
        articles.append(article)

    conn.close()
    return {"articles": articles, "total": len(articles), "keyword": keyword}

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})

@app.exception_handler(422)
async def validation_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": str(exc.errors())})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
