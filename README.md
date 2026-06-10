# 2WikiMultihopQA

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
   `cd 2wikimultihop`

2. 创建虚拟环境并安装依赖  
   `python -m venv venv`  
   `source venv/bin/activate`  
   `pip install -r requirements.txt`

3. 修改 `web.py` 中的 Neo4j 连接配置

4. 确保 Neo4j 服务已启动，且数据已导入
   sudo systemctl start neo4j

5. 运行应用  
   `python web.py`

6. 访问 `http://localhost:5007`


