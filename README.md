# 2wikimultihop
# 2WikiMultihopQA 多跳问答可视化系统

基于 Neo4j 图数据库和 Flask 的多跳问答检索与可视化系统。支持问题关键词检索、按类型筛选、查看多跳推理路径、聚类统计。

## 功能

- 问题检索（关键词 + 类型过滤）
- 多跳推理路径展示
- 聚类统计（关系类型 / 问题类型分布饼图）
- 分页浏览

## 技术栈

- 后端：Flask, Neo4j Python Driver
- 数据库：Neo4j 3.5 / 4.x
- 可视化：ECharts

## 安装与运行

1. 克隆仓库  
   `git clone https://github.com/ethrase/2wikimultihop.git`

2. 创建虚拟环境并安装依赖  
   ```bash
   python -m venv venv
   source venv/bin/activate   
   pip install -r requirements.txt
