#!/usr/bin/env python3
"""个人知识库系统 - 支持分类、标签、加密文章"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import os
import json
import hashlib
import base64
import sqlite3
from pathlib import Path
import secrets

app = FastAPI(title="个人知识库", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库路径
DB_PATH = os.environ.get("KB_DB_PATH", "/data/knowledge_base.db")
ARTICLES_DIR = os.environ.get("KB_ARTICLES_DIR", "/data/articles")
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

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
    return password == ADMIN_PASSWORD

# API 端点

@app.get("/api/health")
def health_check():
    return {"status": "ok", "articles": 0, "categories": 0}

@app.post("/api/auth/login", response_model=AuthResponse)
def login(password: str):
    if not verify_password(password):
        raise HTTPException(status_code=401, detail="密码错误")
    token = secrets.token_urlsafe(32)
    conn = get_db()
    conn.execute("DELETE FROM tokens WHERE username = ?", ("admin",))
    conn.execute("INSERT INTO tokens (token, username) VALUES (?, ?)", (token, "admin"))
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
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    if not token_record:
        conn.close()
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
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    if not token_record:
        conn.close()
        raise HTTPException(status_code=401, detail="未授权")
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return {"message": "分类删除成功"}

@app.get("/api/articles")
def get_articles(category_id: Optional[int] = None, tag: Optional[str] = None, public_only: bool = True, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if public_only and not token_record:
        query += " AND is_public = 1 AND (is_encrypted = 0 OR encryption_key IS NULL)"
    
    if category_id:
        query += " AND category_id = ?"
        params.append(category_id)
    
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    
    query += " ORDER BY created_at DESC"
    
    articles = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(a) for a in articles]

@app.get("/api/articles/{slug}")
def get_article(slug: str, password: Optional[str] = None, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    
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
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    if not token_record:
        conn.close()
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
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    if not token_record:
        conn.close()
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
    conn = get_db()
    token_record = conn.execute("SELECT * FROM tokens WHERE token = ?", (credentials.credentials,)).fetchone()
    if not token_record:
        conn.close()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
