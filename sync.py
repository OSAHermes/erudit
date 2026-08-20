#!/usr/bin/env python3
"""GitHub 同步脚本 - 将知识库文章同步到 GitHub"""

import os
import sys
import json
import sqlite3
import git
from datetime import datetime
from pathlib import Path

class KnowledgeBaseSync:
    def __init__(self):
        self.db_path = os.environ.get("KB_DB_PATH", "/data/knowledge_base.db")
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.github_repo = os.environ.get("GITHUB_REPO", "")
        self.github_branch = os.environ.get("GITHUB_BRANCH", "main")
        self.articles_dir = Path("/data/articles")
        self.articles_dir.mkdir(parents=True, exist_ok=True)
    
    def get_articles(self):
        """从数据库获取所有文章"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM articles ORDER BY updated_at DESC")
        articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return articles
    
    def sync_to_github(self):
        """同步文章到 GitHub"""
        if not self.github_token or not self.github_repo:
            print("错误：请设置 GITHUB_TOKEN 和 GITHUB_REPO 环境变量")
            return False
        
        print(f"正在同步到 {self.github_repo}...")
        
        # 克隆仓库
        repo_url = f"https://{self.github_token}@github.com/{self.github_repo}.git"
        local_repo = Path("/tmp/kb-sync")
        
        if local_repo.exists():
            import shutil
            shutil.rmtree(local_repo)
        
        try:
            repo = git.Repo.clone_from(repo_url, local_repo)
        except git.GitError as e:
            print(f"克隆仓库失败：{e}")
            return False
        
        # 导出文章
        articles = self.get_articles()
        
        # 创建目录结构
        (local_repo / "articles" / "public").mkdir(parents=True, exist_ok=True)
        (local_repo / "articles" / "private").mkdir(parents=True, exist_ok=True)
        (local_repo / "articles" / "encrypted").mkdir(parents=True, exist_ok=True)
        (local_repo / "categories").mkdir(parents=True, exist_ok=True)
        (local_repo / "tags").mkdir(parents=True, exist_ok=True)
        
        # 保存公开文章
        public_count = 0
        encrypted_count = 0
        private_count = 0
        
        for article in articles:
            # 清理标题作为文件名
            filename = article["slug"] + ".md"
            content = article["content"]
            
            # 添加 Frontmatter
            frontmatter = {
                "title": article["title"],
                "date": article["created_at"],
                "updated": article["updated_at"],
                "slug": article["slug"],
                "tags": json.loads(article["tags"]) if article["tags"] else [],
                "category": None
            }
            
            if article["category_id"]:
                # 获取分类名
                cat_conn = sqlite3.connect(self.db_path)
                cat = cat_conn.execute("SELECT name FROM categories WHERE id = ?", (article["category_id"],)).fetchone()
                if cat:
                    frontmatter["category"] = cat["name"]
                cat_conn.close()
            
            # 生成 Markdown
            md_content = f"---\n"
            for key, value in frontmatter.items():
                if isinstance(value, list):
                    md_content += f"{key}:\n"
                    for tag in value:
                        md_content += f"  - {tag}\n"
                else:
                    md_content += f"{key}: {value}\n"
            md_content += f"---\n\n"
            md_content += content + "\n"
            
            # 根据访问权限保存到不同目录
            if article["is_encrypted"]:
                (local_repo / "articles" / "encrypted" / filename).write_text(md_content)
                encrypted_count += 1
            elif article["is_public"]:
                (local_repo / "articles" / "public" / filename).write_text(md_content)
                public_count += 1
            else:
                (local_repo / "articles" / "private" / filename).write_text(md_content)
                private_count += 1
        
        # 创建汇总文件
        index_content = f"# 个人知识库\n\n"
        index_content += f"- 公开文章：{public_count} 篇\n"
        index_content += f"- 加密文章：{encrypted_count} 篇\n"
        index_content += f"- 私密文章：{private_count} 篇\n"
        index_content += f"- 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        index_content += "## 目录\n\n"
        
        for article in articles[:20]:  # 只显示前20篇
            index_content += f"- [{article['title']}]({article['slug']}.md)\n"
        
        (local_repo / "README.md").write_text(index_content)
        
        # 提交并推送
        repo.git.add(".")
        repo.git.commit("-m", f"同步文章 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        repo.git.push("origin", self.github_branch)
        
        print(f"同步完成！")
        print(f"  - 公开文章：{public_count} 篇")
        print(f"  - 加密文章：{encrypted_count} 篇")
        print(f"  - 私密文章：{private_count} 篇")
        print(f"  - GitHub: https://github.com/{self.github_repo}")
        
        return True

if __name__ == "__main__":
    sync = KnowledgeBaseSync()
    success = sync.sync_to_github()
    sys.exit(0 if success else 1)
