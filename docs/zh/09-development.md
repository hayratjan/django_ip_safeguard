# 开发指南

## 设置开发环境

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 或 MySQL（可选）
- Redis（可选）

### 1. 克隆仓库

```bash
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 以开发模式安装带所有依赖
pip install -e ".[dev,geoip2]"

# 安装前端依赖
cd django_ip_safeguard/contrib/admin_frontend
npm install
cd ../../..
```

### 4. 运行测试

```bash
# 运行所有测试
pytest

# 带覆盖率
pytest --cov=django_ip_safeguard --cov-report=html

# 运行特定测试
pytest tests/test_middleware.py -v
```

### 5. 运行开发服务器

```bash
# 从演示项目
cd demo_project
python manage.py runserver 8000
```

### 6. 用 demo2 验证 pip 打包安装（可选）

仓库根目录先打包 wheel：

```bash
python -m build   # 生成 dist/django_ip_safeguard-<版本>-py3-none-any.whl
```

使用示例工程 **demo2**（依赖仅从 wheel 拉取，模拟 PyPI 安装）：

```bash
cd demo2
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install ../dist/django_ip_safeguard-0.3.0-py3-none-any.whl
# 或 pip install -r requirements-from-dist.txt（需在文件中核对 wheel 版本路径）
python manage.py migrate
python manage.py check
python manage.py runserver 8000
```

`demo2/demo2/settings.py` 中 `LOCALE_PATHS` 已指向已安装包内的 `locale`，无需再写仓库源码相对路径。

## 项目结构

```
django_ip_safeguard/
├── __init__.py              # 包初始化，app 配置
├── admin.py                 # Django admin 注册
├── apps.py                  # 应用配置
├── celery.py                # Celery 配置
├── conf.py                  # 设置管理
├── exceptions.py            # 自定义异常
├── middleware.py            # IP Guard 中间件
├── models.py                # 数据库模型
├── signals.py               # Django 信号
├── urls.py                  # URL 路由
├── views.py                 # API 视图
├── types.py                 # 类型定义
├── services/                # 业务逻辑
│   ├── audit_service.py     # 审计日志
│   ├── ban_service.py       # IP 封禁
│   ├── cache.py             # 缓存
│   ├── jwt_service.py       # JWT 处理
│   ├── policy_service.py    # 策略管理
│   ├── risk_engine.py       # 风险评估
│   ├── provider_*.py        # 各种提供者
│   └── ...
├── migrations/              # 数据库迁移
├── management/              # 自定义命令
│   └── commands/
├── locale/                  # 翻译文件
│   ├── en/
│   └── zh_Hans/
└── contrib/
    └── admin_frontend/      # Vue.js 仪表盘
        ├── src/             # 前端源码
        ├── static/          # 构建的资源
        └── management/       # 构建命令
```

## 添加新功能

### 1. 添加新模型

```python
# models.py
class MyFeature(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

### 2. 注册到 Admin

```python
# admin.py
@admin.register(MyFeature)
class MyFeatureAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
```

### 3. 创建 API 视图

```python
# views.py
from django.http import JsonResponse
from django.views import View

class MyFeatureListView(View):
    def get(self, request):
        features = MyFeature.objects.filter(is_active=True)
        data = [{"id": f.id, "name": f.name} for f in features]
        return JsonResponse({"items": data})
```

### 4. 添加 URL 路由

```python
# urls.py
path("my-features/", MyFeatureListView.as_view(), name="my_feature_list"),
```

## 前端开发

### 设置

```bash
cd django_ip_safeguard/contrib/admin_frontend
npm install
```

### 开发模式

```bash
npm run dev
```

开发服务器在 5173 端口运行，代理到 Django 后端。

### 构建生产版本

```bash
npm run build
```

或使用 Django 管理命令：

```bash
python manage.py build_frontend
```

## 代码规范

### Python

- 遵循 PEP 8
- 尽可能使用类型提示
- 使用 `from django_ip_safeguard import ...` 导入

### JavaScript/Vue

- 使用 Vue 3 Composition API
- 使用 `<script setup>` 语法
- 遵循 ESLint 规则

## 测试

### 编写测试

```python
# tests/test_my_feature.py
import pytest
from django_ip_safeguard.models import MyFeature

@pytest.mark.django_db
def test_my_feature_creation():
    feature = MyFeature.objects.create(name="Test")
    assert feature.name == "Test"
    assert feature.is_active is True
```

### 运行测试

```bash
# 所有测试
pytest

# 带覆盖率
pytest --cov=django_ip_safeguard --cov-report=term-missing

# 特定文件
pytest tests/test_middleware.py -v

# 监视模式
ptw  # pytest-watch
```

## 国际化

### 添加翻译字符串

```python
# Python
from django.utils.translation import gettext_lazy as _

name = _("Feature Name")
```

```html
<!-- 模板 -->
<h1>{% trans "Welcome" %}</h1>
```

```javascript
// JavaScript
const message = t("welcome_message");
```

### 更新翻译文件

```bash
# 提取字符串
python manage.py makemessages -l zh_Hans

# 编译消息
python manage.py compilemessages
```

## 调试

### Django Debug Toolbar

安装并配置 django-debug-toolbar 用于本地开发。

### 日志

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### IPython 调试

```python
from IPython import embed; embed()
```

## 贡献

1. Fork 仓库
2. 创建功能分支
3. 进行更改
4. 编写测试
5. 提交 Pull Request

## 代码审查清单

- [ ] 代码遵循项目规范
- [ ] 已添加/更新测试
- [ ] 已更新文档
- [ ] 没有破坏性更改
- [ ] 所有测试通过
- [ ] 已添加类型提示（Python）
