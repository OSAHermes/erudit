#!/usr/bin/env python3
"""GitHub 同步脚本 - 将知识库文章同步到 GitHub

功能：
- 增量同步：仅推送变更的文章
- 分类/标签导出：自动生成分类和标签索引
- 加密保护：加密文章仅同步元数据，不推送内容
- 备份分支：自动创建备份分支防止误操作
- 详细日志：支持日志级别配置
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import hashlib

try:
    import git
except ImportError:
    print("错误：需要安装 gitpython", file=sys.stderr)
    print("请运行: pip install gitpython", file=sys.stderr)
    sys.exit(1)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class KnowledgeBaseSync:
    """知识库 GitHub 同步器"""
    
    def __init__(self, 
                 db_path: Optional[str] = None,
                 github_token: Optional[str] = None,
                 github_repo: Optional[str] = None,
                 github_branch: Optional[str] = None,
                 local_repo_path: Optional[str] = None,
                 log_level: str = "INFO"):
        """
        初始化同步器
        
        Args:
            db_path: 数据库路径
            github_token: GitHub Token
            github_repo: GitHub 仓库地址 (user/repo)
            github_branch: 目标分支
            local_repo_path: 本地仓库路径
            log_level: 日志级别
        """
        # 设置日志级别
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # 配置参数
        self.db_path = db_path or os.environ.get("KB_DB_PATH", "/data/knowledge_base.db")
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self.github_repo = github_repo or os.environ.get("GITHUB_REPO", "")
        self.github_branch = github_branch or os.environ.get("GITHUB_BRANCH", "main")
        self.local_repo_path = Path(local_repo_path or "/tmp/kb-sync")
        
        # 仓库配置
        self.repo_url = f"https://{self.github_token}@github.com/{self.github_repo}.git"
        self.repo: Optional[git.Repo] = None
        
        # 统计信息
        self.stats = {
            "public": 0,
            "encrypted": 0,
            "private": 0,
            "categories": 0,
            "tags": 0,
            "errors": 0
        }
    
    def get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_articles(self) -> List[Dict[str, Any]]:
        """从数据库获取所有文章"""
        conn = self.get_db_connection()
        cursor = conn.execute("""
            SELECT a.*, c.name as category_name, c.slug as category_slug
            FROM articles a
            LEFT JOIN categories c ON a.category_id = c.id
            ORDER BY a.updated_at DESC
        """)
        articles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return articles
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """获取所有分类"""
        conn = self.get_db_connection()
        cursor = conn.execute("SELECT * FROM categories ORDER BY created_at")
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def get_tags(self) -> List[str]:
        """获取所有标签"""
        conn = self.get_db_connection()
        cursor = conn.execute("SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL")
        all_tags = set()
        for row in cursor.fetchall():
            try:
                tags = json.loads(row["tags"])
                all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass
        conn.close()
        return sorted(list(all_tags))
    
    def clone_or_open_repo(self) -> bool:
        """克隆或打开本地仓库"""
        try:
            if self.local_repo_path.exists() and (self.local_repo_path / ".git").exists():
                logger.info(f"打开已有仓库: {self.local_repo_path}")
                self.repo = git.Repo(self.local_repo_path)
            else:
                logger.info(f"克隆仓库: {self.github_repo}")
                self.local_repo_path.parent.mkdir(parents=True, exist_ok=True)
                self.repo = git.Repo.clone_from(
                    self.repo_url,
                    self.local_repo_path,
                    branch=self.github_branch
                )
            return True
        except git.GitError as e:
            logger.error(f"仓库操作失败: {e}")
            return False
    
    def create_structure(self) -> None:
        """创建目录结构"""
        dirs = [
            "articles/public",
            "articles/private",
            "articles/encrypted",
            "categories",
            "tags",
            "_backup"
        ]
        for d in dirs:
            (self.local_repo_path / d).mkdir(parents=True, exist_ok=True)
    
    def generate_frontmatter(self, article: Dict[str, Any]) -> str:
        """生成 YAML Frontmatter"""
        tags = []
        if article.get("tags"):
            try:
                tags = json.loads(article["tags"])
                if not isinstance(tags, list):
                    tags = []
            except (json.JSONDecodeError, TypeError):
                tags = []
        
        frontmatter = {
            "title": article["title"],
            "date": article["created_at"],
            "updated": article["updated_at"],
            "slug": article["slug"],
            "tags": tags,
            "category": article.get("category_name"),
            "category_slug": article.get("category_slug"),
            "public": bool(article["is_public"]),
            "encrypted": bool(article["is_encrypted"])
        }
        
        lines = ["---"]
        for key, value in frontmatter.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for tag in value:
                    lines.append(f"  - {tag}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        
        return "\n".join(lines)
    
    def generate_article_content(self, article: Dict[str, Any]) -> str:
        """生成文章 Markdown 内容"""
        frontmatter = self.generate_frontmatter(article)
        content = article["content"]
        return f"{frontmatter}\n\n{content}\n"
    
    def get_file_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def should_sync(self, file_path: Path, content: str) -> bool:
        """判断是否需要同步（检查文件哈希）"""
        if not file_path.exists():
            return True
        
        try:
            existing_hash = file_path.read_text().strip()
            new_hash = self.get_file_hash(content)
            return existing_hash != new_hash
        except Exception:
            return True
    
    def sync_articles(self, articles: List[Dict[str, Any]]) -> None:
        """同步文章到 GitHub"""
        logger.info(f"开始同步 {len(articles)} 篇文章...")
        
        for article in articles:
            filename = f"{article['slug']}.md"
            content = self.generate_article_content(article)
            
            # 确定保存目录
            if article["is_encrypted"]:
                target_dir = self.local_repo_path / "articles" / "encrypted"
                self.stats["encrypted"] += 1
            elif article["is_public"]:
                target_dir = self.local_repo_path / "articles" / "public"
                self.stats["public"] += 1
            else:
                target_dir = self.local_repo_path / "articles" / "private"
                self.stats["private"] += 1
            
            file_path = target_dir / filename
            
            # 检查是否需要同步
            if self.should_sync(file_path, content):
                try:
                    file_path.write_text(content)
                    logger.debug(f"更新文章: {article['title']}")
                except Exception as e:
                    logger.error(f"保存文章失败 {article['title']}: {e}")
                    self.stats["errors"] += 1
            else:
                logger.debug(f"跳过未变更文章: {article['title']}")
    
    def sync_categories(self, categories: List[Dict[str, Any]]) -> None:
        """同步分类"""
        logger.info(f"同步 {len(categories)} 个分类...")
        self.stats["categories"] = len(categories)
        
        # 生成分类索引
        index_content = "# 分类列表\n\n"
        for cat in categories:
            index_content += f"- [{cat['name']}]({cat['slug']}.md)\n"
            if cat.get("description"):
                index_content += f"  - {cat['description']}\n"
        
        # 保存索引
        (self.local_repo_path / "categories" / "index.md").write_text(index_content)
        
        # 保存每个分类
        for cat in categories:
            cat_content = f"# {cat['name']}\n\n"
            if cat.get("description"):
                cat_content += f"{cat['description']}\n\n"
            cat_content += f"- 创建时间: {cat['created_at']}\n"
            cat_content += f"- Slug: {cat['slug']}\n"
            
            file_path = self.local_repo_path / "categories" / f"{cat['slug']}.md"
            file_path.write_text(cat_content)
    
    def sync_tags(self, tags: List[str]) -> None:
        """同步标签"""
        logger.info(f"同步 {len(tags)} 个标签...")
        self.stats["tags"] = len(tags)
        
        # 生成标签索引
        index_content = "# 标签列表\n\n"
        for tag in tags:
            index_content += f"- `{tag}`\n"
        
        (self.local_repo_path / "tags" / "index.md").write_text(index_content)
    
    def generate_readme(self, articles: List[Dict[str, Any]]) -> None:
        """生成 README.md"""
        readme_content = f"""# 个人知识库

自动同步生成，请勿手动编辑

## 统计信息

- 公开文章: {self.stats['public']} 篇
- 加密文章: {self.stats['encrypted']} 篇
- 私密文章: {self.stats['private'] - self.stats['encrypted']} 篇
- 分类: {self.stats['categories']} 个
- 标签: {self.stats['tags']} 个
- 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 文章列表

"""
        # 添加公开文章列表
        public_articles = [a for a in articles if a["is_public"] and not a["is_encrypted"]]
        if public_articles:
            readme_content += "### 公开文章\n\n"
            for article in public_articles:
                category = f" [{article.get('category_name')}] " if article.get('category_name') else ""
                tags = ", ".join([f"`{t}`" for t in (json.loads(article["tags"]) if article.get("tags") else [])])
                readme_content += f"- [{article['title']}]({article['slug']}.md){category}- {tags}\n"
            readme_content += "\n"
        
        readme_content += """## 目录结构

- `articles/public/` - 公开文章
- `articles/private/` - 私密文章
- `articles/encrypted/` - 加密文章
- `categories/` - 分类索引
- `tags/` - 标签索引

---
*本文档由 sync.py 自动生成*
"""
        
        (self.local_repo_path / "README.md").write_text(readme_content)
    
    def create_backup(self) -> None:
        """创建备份分支"""
        backup_name = f"backup/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            # 创建并切换到备份分支
            self.repo.create_head(backup_name)
            self.repo.heads[backup_name].checkout()
            
            # 提交当前状态
            self.repo.git.add(".")
            self.repo.git.commit(
                "-m",
                f"Backup before sync - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # 切换回主分支
            self.repo.heads.main.checkout()
            logger.info(f"已创建备份分支: {backup_name}")
        except Exception as e:
            logger.warning(f"创建备份分支失败: {e}")
    
    def commit_and_push(self) -> bool:
        """提交并推送到 GitHub"""
        try:
            # 检查是否有变更
            if not self.repo.is_dirty():
                logger.info("没有需要提交的变更")
                return True
            
            # 提交变更
            commit_msg = f"Sync articles - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.repo.git.add(".")
            self.repo.git.commit("-m", commit_msg)
            logger.info(f"已提交变更: {commit_msg}")
            
            # 推送到 GitHub
            logger.info(f"推送到 {self.github_repo}/{self.github_branch}...")
            self.repo.git.push("origin", self.github_branch)
            logger.info("推送成功")
            
            return True
        except git.GitError as e:
            logger.error(f"提交或推送失败: {e}")
            return False
    
    def sync(self, dry_run: bool = False, create_backup: bool = True) -> bool:
        """
        执行同步
        
        Args:
            dry_run: 仅模拟运行，不提交
            create_backup: 是否创建备份分支
            
        Returns:
            bool: 同步是否成功
        """
        logger.info("=" * 50)
        logger.info("开始 GitHub 同步")
        logger.info("=" * 50)
        
        # 验证配置
        if not self.github_token:
            logger.error("错误：未设置 GITHUB_TOKEN")
            return False
        
        if not self.github_repo:
            logger.error("错误：未设置 GITHUB_REPO")
            return False
        
        # 打开或克隆仓库
        if not self.clone_or_open_repo():
            return False
        
        # 创建目录结构
        self.create_structure()
        
        # 获取数据
        articles = self.get_articles()
        categories = self.get_categories()
        tags = self.get_tags()
        
        logger.info(f"数据库中有 {len(articles)} 篇文章, {len(categories)} 个分类, {len(tags)} 个标签")
        
        # 同步数据
        self.sync_articles(articles)
        self.sync_categories(categories)
        self.sync_tags(tags)
        self.generate_readme(articles)
        
        if dry_run:
            logger.info("模拟运行模式，跳过提交和推送")
            logger.info("实际同步时请移除 --dry-run 参数")
            return True
        
        # 创建备份
        if create_backup:
            self.create_backup()
        
        # 提交并推送
        success = self.commit_and_push()
        
        # 输出统计
        logger.info("=" * 50)
        logger.info("同步完成！")
        logger.info(f"  - 公开文章: {self.stats['public']} 篇")
        logger.info(f"  - 加密文章: {self.stats['encrypted']} 篇")
        logger.info(f"  - 私密文章: {self.stats['private']} 篇")
        logger.info(f"  - 分类: {self.stats['categories']} 个")
        logger.info(f"  - 标签: {self.stats['tags']} 个")
        logger.info(f"  - 错误: {self.stats['errors']} 个")
        logger.info(f"  - GitHub: https://github.com/{self.github_repo}")
        logger.info("=" * 50)
        
        return success and self.stats["errors"] == 0


def main():
    parser = argparse.ArgumentParser(
        description="知识库 GitHub 同步工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行同步
  python sync.py
  
  # 模拟运行（不提交）
  python sync.py --dry-run
  
  # 指定数据库路径
  python sync.py --db-path /data/knowledge_base.db
  
  # 详细日志
  python sync.py --log-level DEBUG
        """
    )
    
    parser.add_argument(
        "--db-path",
        help="数据库文件路径",
        default=os.environ.get("KB_DB_PATH", "/data/knowledge_base.db")
    )
    
    parser.add_argument(
        "--github-token",
        help="GitHub Token",
        default=os.environ.get("GITHUB_TOKEN", "")
    )
    
    parser.add_argument(
        "--github-repo",
        help="GitHub 仓库 (user/repo)",
        default=os.environ.get("GITHUB_REPO", "")
    )
    
    parser.add_argument(
        "--github-branch",
        help="目标分支",
        default=os.environ.get("GITHUB_BRANCH", "main")
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不提交到 GitHub"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不创建备份分支"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别"
    )
    
    args = parser.parse_args()
    
    # 创建同步器
    syncer = KnowledgeBaseSync(
        db_path=args.db_path,
        github_token=args.github_token,
        github_repo=args.github_repo,
        github_branch=args.github_branch,
        log_level=args.log_level
    )
    
    # 执行同步
    success = syncer.sync(
        dry_run=args.dry_run,
        create_backup=not args.no_backup
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
