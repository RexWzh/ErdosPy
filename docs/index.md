# erdospy

`erdospy` 是一个面向 Erdős 问题数据的 Python 包和命令行工具。

当前版本已经支持：

- 本地可写 SQLite 工作库初始化
- CLI 查询问题、搜索问题、筛选问题
- 原生 forum 增量更新
- 查看每日进度摘要
- 查看单个问题的本地变更记录
- `skills` 风格的任务化入口
- 简单 dashboard 页面与本地 `serve` 命令

如果你想直接开始用，先看 `中文 Quick Start`。

## 新入口

常用任务现在可以通过 `skills` 和 `serve` 入口访问：

```bash
erdospy skills refresh --db ~/.erdospy/erdos_problems.db
erdospy skills investigate 12 --db ~/.erdospy/erdos_problems.db
erdospy serve dashboard --db ~/.erdospy/erdos_problems.db --port 8000
```

GitHub Pages 发布时也会自动生成一个静态 dashboard 页面：`site/dashboard/index.html`。
