# 中文 Quick Start

这份文档只讲当前已经可用、可验证、可直接运行的纯 CLI 工作流。

## 适用场景

如果你希望用命令行完成下面这套流程：

- 初始化一份本地可写数据库
- 查询问题与评论
- 汇总某一道题的最新进展
- 跑一次增量更新
- 看当天有哪些变化
- 跟踪某个特定问题的记录
- 搜索和查看相关讨论

那就照这份文档直接跑。

## 1. 安装 Python 包

进入仓库目录：

```bash
cd /home/zhihong/Playground/core/erdospy
```

用可编辑模式安装：

```bash
pip install -e .
```

安装完成后，命令行里会有 `erdospy` 命令。

## 2. 初始化本地工作库

执行：

```bash
erdospy build
```

默认会在当前目录生成：

```bash
~/.erdospy/erdos_problems.db
~/.erdospy/history.jsonl
~/.erdospy/snapshot.json
```

这三个文件的作用分别是：

- `erdos_problems.db`：本地可写 SQLite 数据库
- `history.jsonl`：CLI 运行历史和兼容事件流
- `snapshot.json`：本地快照索引

如果你想强制重新初始化：

```bash
erdospy build --force
```

## 3. 查询当前本地数据

先看总体状态：

```bash
erdospy stats --db ~/.erdospy/erdos_problems.db
```

看某一道题：

```bash
erdospy get 42 --db ~/.erdospy/erdos_problems.db
```

连评论一起看：

```bash
erdospy get 42 --db ~/.erdospy/erdos_problems.db --comments
```

输出 JSON：

```bash
erdospy get 42 --db ~/.erdospy/erdos_problems.db --json
```

全文搜索：

```bash
erdospy search "Sidon set" --db ~/.erdospy/erdos_problems.db --limit 5
```

结构化筛选：

```bash
erdospy list --db ~/.erdospy/erdos_problems.db --status open --tag primes --limit 10
```

看某一道题的综合进展：

```bash
erdospy progress 12 --db ~/.erdospy/erdos_problems.db
```

看一份简洁 digest：

```bash
erdospy digest --db ~/.erdospy/erdos_problems.db --limit 10
```

## 4. 跑一次增量更新

执行：

```bash
erdospy update --db ~/.erdospy/erdos_problems.db
```

当前版本这一步已经是原生 CLI 更新链路，不再只是借上游脚本做包装。

现在它会做的事情是：

- 抓取 `erdosproblems.com/forum/`
- 解析 forum thread 活跃信息
- 写入本地 SQLite 跟踪表
- 生成本地 changelog
- 让 `daily` 和 `record` 命令可以直接读取这些变化

更新完成后，CLI 会输出一张 `Update Summary` 表，以及变化摘要。

## 5. 查看每日进度

看最近一天的记录：

```bash
erdospy daily --db ~/.erdospy/erdos_problems.db
```

看指定日期：

```bash
erdospy daily --db ~/.erdospy/erdos_problems.db --date 2026-04-07
```

当前 `daily` 会展示：

- 当天运行次数
- 变化总数
- 涉及的问题数
- 纯文本 change summary
- rich 表格形式的 change log

## 6. 查看论坛讨论与相关进展

先做一版 forum 全量抓取：

```bash
erdospy forum sync --db ~/.erdospy/erdos_problems.db --limit 20 --show-top 5
```

看最新讨论：

```bash
erdospy forum latest --db ~/.erdospy/erdos_problems.db --limit 10
```

看某题相关讨论：

```bash
erdospy forum related 12 --db ~/.erdospy/erdos_problems.db
```

搜索讨论内容：

```bash
erdospy forum search "formalised" --db ~/.erdospy/erdos_problems.db --limit 10
```

## 7. 查看单个问题的记录

例如查看 `749`：

```bash
erdospy record 749 --db ~/.erdospy/erdos_problems.db
```

例如查看 `42`：

```bash
erdospy record 42 --db ~/.erdospy/erdos_problems.db
```

当前 `record` 会展示该问题在本地变更日志里的记录。

## 8. 一套最短日常流程

每天如果只想快速刷新和查看变化，直接跑：

```bash
cd /home/zhihong/Playground/core/erdospy

erdospy update --db ~/.erdospy/erdos_problems.db
erdospy daily --db ~/.erdospy/erdos_problems.db
erdospy progress 12 --db ~/.erdospy/erdos_problems.db
erdospy record 749 --db ~/.erdospy/erdos_problems.db
```

## 9. 从零完整跑一遍

如果你要从头开始完整演示一次：

```bash
cd /home/zhihong/Playground/core/erdospy
pip install -e .

erdospy build --force
erdospy stats --db ~/.erdospy/erdos_problems.db
erdospy get 42 --db ~/.erdospy/erdos_problems.db --comments
erdospy forum sync --db ~/.erdospy/erdos_problems.db --limit 20 --show-top 5
erdospy update --db ~/.erdospy/erdos_problems.db
erdospy progress 12 --db ~/.erdospy/erdos_problems.db
erdospy digest --db ~/.erdospy/erdos_problems.db --limit 10
erdospy daily --db ~/.erdospy/erdos_problems.db
erdospy record 749 --db ~/.erdospy/erdos_problems.db
```

## 10. 当前实现边界

当前已经完成：

- Python 包安装
- CLI 查询能力
- 问题级 progress 汇总
- digest 摘要
- 本地工作库初始化
- forum 原生增量更新
- forum 全量抓取
- 讨论搜索与相关讨论查看
- daily 进度查看
- 单题 record 查看

当前还没完成：

- `erdospy changelog` 独立命令
- 对 problem page 本身的更深层增量抓取
- status / comments / reactions 的完整原生 diff

所以现在最适合把它当作：

- 一个本地 CLI 工作台
- 一个 Erdős problems 分析工具
- 一个 forum activity tracker
- 一个日常更新和单题追踪工具
- 一个命令行讨论检索与问题进展查看工具

而不是最终完整版本。
