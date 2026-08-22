# Erudit 常见问题与修复

## 问题 1: 登录按钮点击无反应

### 现象
点击登录按钮后页面无反应，无法登录。

### 原因
前端使用 GET 请求发送密码，但后端只接受 POST 请求（或反之）。

### 解决方案
修改 `/api/auth/login` 端点，同时支持 GET 和 POST：

```python
@app.post("/api/auth/login")
@app.get("/api/auth/login")
def login(request: Request, password: str = Form(default=None)):
    if password is None:
        password = request.query_params.get("password")
    # ...
```

前端使用 POST：
```javascript
const resp = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `password=${encodeURIComponent(password)}`
});
```

---

## 问题 2: 统计数字显示 0

### 现象
Web UI 中文章数和分类数显示为 0，即使有数据。

### 原因
前端没有调用 API 获取统计数据，或没有更新 DOM。

### 解决方案
在 `loadArticles()` 中添加统计更新：

```javascript
async function loadArticles() {
    const resp = await fetch('/api/articles', { headers: { 'Authorization': 'Bearer ' + token } });
    const data = await resp.json();
    articles = data.articles || [];
    document.getElementById('statArticles').textContent = data.total || articles.length;
    renderList();
    loadCategories();  // 新增
}

async function loadCategories() {
    const resp = await fetch('/api/categories', { headers: { 'Authorization': 'Bearer ' + token } });
    const data = await resp.json();
    document.getElementById('statCategories').textContent = data.length || 0;
}
```

---

## 问题 3: 创建分类报错 UnboundLocalError

### 现象
```
UnboundLocalError: cannot access local variable 'conn' where it is not associated with a value
```

### 原因
`conn.close()` 在 `conn = get_db()` 之前调用。

### 解决方案
```python
@app.post("/api/categories")
def create_category(category: CategoryCreate, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token_record = validate_token(credentials.credentials)
    if not token_record:
        raise HTTPException(status_code=401, detail="未授权")
    
    conn = get_db()  # 先获取连接
    slug = category.name.lower().replace(" ", "-")
    conn.execute("INSERT INTO categories ...", ...)
    conn.commit()
    conn.close()  # 后关闭
```

---

## 问题 4: 密码修改后重启失效

### 现象
通过 API 修改密码后，重启容器密码恢复默认。

### 原因
密码修改只在内存中生效，没有持久化到环境变量。

### 解决方案
在 `.env` 文件中设置 `ADMIN_PASSWORD_HASH`：

```bash
# 生成 bcrypt 哈希
python3 -c "import bcrypt; print(bcrypt.hashpw('your_password'.encode(), bcrypt.gensalt()).decode())"

# 添加到 .env
ADMIN_PASSWORD_HASH=$2b$12$...
```

---

## 问题 5: 宿主机无法访问服务

### 现象
容器内可以访问 API，但宿主机返回 404 或连接拒绝。

### 原因
Docker 网络隔离导致端口映射失效。

### 解决方案
使用 host 网络模式：

```yaml
services:
  erudit:
    network_mode: host
    # 不使用 ports 映射
```

---

## API 速查表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | GET/POST | 登录获取 Token |
| `/api/auth/change-password` | POST | 修改密码 |
| `/api/articles` | GET | 文章列表 |
| `/api/articles` | POST | 创建文章 |
| `/api/articles/{slug}` | GET | 获取文章 |
| `/api/articles/{slug}` | PUT | 更新文章 |
| `/api/articles/{slug}` | DELETE | 删除文章 |
| `/api/categories` | GET | 分类列表 |
| `/api/categories` | POST | 创建分类 |
| `/api/backup` | POST | 创建备份 |
| `/api/backup/cleanup` | POST | 清理旧备份 |
| `/api/rss` | GET | RSS 订阅 |
| `/api/metrics` | GET | 系统指标 |
| `/api/health` | GET | 健康检查 |
| `/` | GET | Web UI |