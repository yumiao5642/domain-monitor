/home/cloud-user/domain_monitor/
├── core/
│   ├── migrations/
│   │   └── (Django 自动生成的迁移文件，用于数据库表结构变更)
│   ├── static/
│   │   └── css/
│   │       └── domain_monitor_custom.css  # 自定义 CSS 样式文件，包含页面样式和自适应布局
│   ├── templates/
│   │   ├── base.html                     # 基础模板，包含页面通用布局（如导航栏、侧边栏）
│   │   ├── dashboard.html                # 仪表板页面模板，显示统计信息
│   │   ├── domain_form.html              # 添加/编辑域名页面模板，包含表单和动态逻辑
│   │   ├── domain_list.html              # 域名管理页面模板，显示域名列表和操作按钮
│   │   ├── login.html                    # 登录页面模板
│   │   └── alert_config.html             # 告警配置页面模板
│   ├── __init__.py                       # Python 包初始化文件
│   ├── admin.py                          # Django 管理后台配置文件
│   ├── apps.py                           # 应用配置文件
│   ├── models.py                         # 数据库模型文件，定义 User、Domain 等表结构
│   ├── tests.py                          # 测试文件（可能为空）
│   ├── urls.py                           # 应用级 URL 路由配置文件
│   ├── utils.py                          # 工具函数文件，包含 get_domain_stats 和 format_interval
│   └── views.py                          # 视图函数文件，处理页面逻辑和请求
├── domain_monitor/
│   ├── __init__.py                       # 项目包初始化文件
│   ├── asgi.py                           # ASGI 配置文件，用于异步部署
│   ├── settings.py                       # 项目配置文件，包含数据库、静态文件等设置
│   ├── urls.py                           # 项目级 URL 路由配置文件
│   └── wsgi.py                           # WSGI 配置文件，用于同步部署
├── manage.py                             # Django 管理脚本，用于运行服务器、迁移数据库等
├── staticfiles/                          # 收集的静态文件目录（由 collectstatic 生成）
└── venv/                                 # Python 虚拟环境目录，包含 Python 3.9.21 环境
