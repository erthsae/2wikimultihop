from flask import Flask, render_template_string, request
from neo4j import GraphDatabase
import math

app = Flask(__name__)

# Neo4j 连接配置
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4j123"
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# ------------------ 辅助函数 ------------------
def run_query(query, params=None):
    with driver.session() as session:
        result = session.run(query, parameters=params)
        return [record.data() for record in result]

# ------------------ 路由 ------------------
@app.route('/')
def index():
    # 获取所有问题类型用于下拉框
    types = run_query("MATCH (q:Question) RETURN DISTINCT q.type AS type ORDER BY type")
    return render_template_string(HTML_TEMPLATE, results=None, search_results=None, clusters=None,
                                  page=1, total_pages=1, keyword='', type_filter='', types=types)

@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword', '').strip()
    type_filter = request.args.get('type_filter', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if not keyword:
        # 获取类型列表以便重新渲染页面
        types = run_query("MATCH (q:Question) RETURN DISTINCT q.type AS type ORDER BY type")
        return render_template_string(HTML_TEMPLATE, results=None, search_results=None, clusters=None,
                                      page=1, total_pages=1, keyword='', type_filter='', types=types, error="请输入关键词")

    # 构建过滤条件
    type_condition = ""
    if type_filter:
        type_condition = "AND q.type = $type_filter"

    # 查询总数
    count_query = f"""
        MATCH (q:Question)
        WHERE q.text CONTAINS $keyword {type_condition}
        RETURN count(q) AS total
    """
    params = {"keyword": keyword}
    if type_filter:
        params["type_filter"] = type_filter
    total_records = run_query(count_query, params)[0]['total']
    total_pages = math.ceil(total_records / per_page) if total_records > 0 else 1
    offset = (page - 1) * per_page

    # 分页查询
    data_query = f"""
        MATCH (q:Question)
        WHERE q.text CONTAINS $keyword {type_condition}
        RETURN q.id AS id, q.text AS question, q.answer AS answer, q.type AS type
        ORDER BY q.id
        SKIP $skip LIMIT $limit
    """
    params.update({"skip": offset, "limit": per_page})
    results = run_query(data_query, params)

    # 获取所有可用的问题类型，用于下拉框
    types = run_query("MATCH (q:Question) RETURN DISTINCT q.type AS type ORDER BY type")

    return render_template_string(HTML_TEMPLATE,
                                  search_results=results,
                                  keyword=keyword,
                                  type_filter=type_filter,
                                  page=page,
                                  total_pages=total_pages,
                                  types=types,
                                  results=None,
                                  clusters=None,
                                  total_records=total_records)

@app.route('/question/<qid>')
def question_detail(qid):
    # 查询问题基本信息
    q_res = run_query("MATCH (q:Question {id: $id}) RETURN q", {"id": qid})
    if not q_res:
        return "问题不存在", 404
    q_node = q_res[0]['q']

    # 查询第一条完整路径（到答案）
    path_query = """
        MATCH (q:Question {id: $id})
        MATCH path = (q)-[:FIRST_ENTITY]->(start:Entity)-[:RELATION*1..5]->(end:Entity)
        WHERE end.name = q.answer
        RETURN [node in nodes(path) | node.name] AS node_names,
               [rel in relationships(path) | {
                   from: startNode(rel).name,
                   to: endNode(rel).name,
                   type: type(rel)
               }] AS rels
        LIMIT 1
    """
    path_data = run_query(path_query, {"id": qid})

    path_steps = []
    if path_data:
        record = path_data[0]
        rels = record.get('rels', [])
        for rel in rels:
            path_steps.append({
                'from': rel['from'],
                'to': rel['to'],
                'type': rel['type']
            })

    return render_template_string(HTML_TEMPLATE,
                                  question=q_node,
                                  path_steps=path_steps,
                                  search_results=None,
                                  results=None,
                                  clusters=None)

@app.route('/cluster')
def cluster():
    # 关系类型统计
    rel_stats = run_query("MATCH ()-[r:RELATION]->() RETURN r.type AS type, COUNT(*) AS count ORDER BY count DESC LIMIT 10")
    # 问题类型统计
    type_stats = run_query("MATCH (q:Question) RETURN q.type AS type, COUNT(*) AS count ORDER BY count DESC")
    # 实体总数
    entity_count = run_query("MATCH (e:Entity) RETURN COUNT(e) AS count")[0]['count']
    # 问题总数
    question_count = run_query("MATCH (q:Question) RETURN COUNT(q) AS count")[0]['count']

    # 准备 ECharts 数据
    rel_categories = [r['type'] for r in rel_stats]
    rel_counts = [r['count'] for r in rel_stats]
    type_categories = [t['type'] for t in type_stats]
    type_counts = [t['count'] for t in type_stats]

    return render_template_string(HTML_TEMPLATE,
                                  clusters={
                                      'relation_types': rel_stats,
                                      'question_types': type_stats,
                                      'entity_count': entity_count,
                                      'question_count': question_count,
                                      'rel_categories': rel_categories,
                                      'rel_counts': rel_counts,
                                      'type_categories': type_categories,
                                      'type_counts': type_counts
                                  },
                                  search_results=None, results=None)

# ------------------ 模板 ------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>2WikiMultihopQA 多跳查询系统</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 15px; text-decoration: none; color: #2196F3; }
        .search-box { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .path-step { background: #f9f9f9; margin: 10px 0; padding: 10px; border-left: 4px solid #4CAF50; }
        .pagination { margin: 20px 0; }
        .pagination a { margin: 0 5px; padding: 5px 10px; border: 1px solid #ddd; text-decoration: none; }
        .pagination .active { background: #4CAF50; color: white; }
        .error { color: red; }
        .filter { margin: 10px 0; }
        .stats-container { display: flex; flex-wrap: wrap; justify-content: space-between; }
        .stats-table { width: 45%; }
        .stats-chart { width: 50%; height: 400px; }
        hr { margin: 20px 0; }
        .no-results { background: #fff3cd; border: 1px solid #ffeeba; padding: 15px; border-radius: 5px; color: #856404; margin: 20px 0; }
    </style>
    <!-- ECharts CDN -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
</head>
<body>
    <h1>2WikiMultihopQA 多跳查询系统</h1>
    <div class="nav">
        <a href="/">首页</a>
        <a href="/cluster">聚类统计</a>
    </div>
    <div class="search-box">
        <form action="/search" method="get">
            <input type="text" name="keyword" placeholder="输入问题关键词" size="50" value="{{ keyword or '' }}">
            <select name="type_filter">
                <option value="">所有类型</option>
                {% for t in types %}
                <option value="{{ t.type }}" {% if type_filter == t.type %}selected{% endif %}>{{ t.type }}</option>
                {% endfor %}
            </select>
            <button type="submit">检索问题</button>
        </form>
    </div>
    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}

    {# 搜索结果区域 #}
    {% if search_results is not none %}
        {% if search_results %}
            <h2>检索结果 (关键词: {{ keyword }}{% if type_filter %}，类型: {{ type_filter }}{% endif %})</h2>
            <p>共 {{ total_records }} 条结果</p>
            <table>
                <tr><th>问题ID</th><th>问题内容</th><th>答案</th><th>类型</th><th>操作</th></tr>
                {% for r in search_results %}
                <tr>
                    <td>{{ r.id[:8] }}...</td>
                    <td>{{ r.question[:100] }}...</td>
                    <td>{{ r.answer }}</td>
                    <td>{{ r.type }}</td>
                    <td><a href="/question/{{ r.id }}">查看多跳路径</a></td>
                </tr>
                {% endfor %}
            </table>
            <div class="pagination">
                {% if page > 1 %}<a href="?keyword={{ keyword }}&type_filter={{ type_filter }}&page={{ page-1 }}">上一页</a>{% endif %}
                {% for p in range(1, total_pages+1) %}
                    {% if p == page %}<span class="active">{{ p }}</span>{% else %}<a href="?keyword={{ keyword }}&type_filter={{ type_filter }}&page={{ p }}">{{ p }}</a>{% endif %}
                {% endfor %}
                {% if page < total_pages %}<a href="?keyword={{ keyword }}&type_filter={{ type_filter }}&page={{ page+1 }}">下一页</a>{% endif %}
            </div>
        {% else %}
            <div class="no-results">
                <strong>未找到匹配的问题</strong>，共 {{ total_records }} 条结果。
            </div>
        {% endif %}
    {% endif %}

    {% if question %}
        <h2>问题详情</h2>
        <p><strong>ID:</strong> {{ question.id }}</p>
        <p><strong>问题:</strong> {{ question.text }}</p>
        <p><strong>答案:</strong> {{ question.answer }}</p>
        <p><strong>类型:</strong> {{ question.type }}</p>
        <h3>推理路径（多跳过程）</h3>
        {% if path_steps %}
            {% for step in path_steps %}
                <div class="path-step">
                    {{ step.from }} → {{ step.to }}  (关系: <strong>{{ step.type }}</strong>)
                </div>
            {% endfor %}
            <div style="margin-top: 15px; padding: 8px; background: #e8f5e9; border-radius: 8px;">
                <strong>最终答案:</strong> {{ question.answer }}
            </div>
        {% else %}
            <p>未找到完整的推理路径。</p>
        {% endif %}
    {% endif %}

    {% if clusters %}
        <h2>聚类统计</h2>
        <div class="stats-container">
            <div class="stats-table">
                <h3>关系类型 (predicate) 分布 (前10)</h3>
                <table>
                    <tr><th>关系类型 (predicate)</th><th>出现次数</th></tr>
                    {% for r in clusters.relation_types %}
                    <tr><td>{{ r.type }}</td><td>{{ r.count }}</td></tr>
                    {% endfor %}
                </table>
            </div>
            <div class="stats-chart">
                <div id="rel-chart" style="height: 400px;"></div>
            </div>
        </div>
        <hr>
        <div class="stats-container">
            <div class="stats-table">
                <h3>问题类型 (type) 分布</h3>
                <table>
                    <tr><th>问题类型 (type)</th><th>数量</th></tr>
                    {% for t in clusters.question_types %}
                    <tr><td>{{ t.type }}</td><td>{{ t.count }}</td></tr>
                    {% endfor %}
                </table>
            </div>
            <div class="stats-chart">
                <div id="type-chart" style="height: 400px;"></div>
            </div>
        </div>
        <p>实体节点总数: {{ clusters.entity_count }} | 问题节点总数: {{ clusters.question_count }}</p>
        <script>
            var relChart = echarts.init(document.getElementById('rel-chart'));
            relChart.setOption({
                tooltip: { trigger: 'item' },
                legend: { top: '5%', left: 'center' },
                series: [{
                    name: '关系类型 (predicate)', type: 'pie', radius: ['40%', '70%'],
                    data: [
                        {% for i in range(clusters.rel_categories|length) %}
                        { name: "{{ clusters.rel_categories[i] }}", value: {{ clusters.rel_counts[i] }} }{% if not loop.last %},{% endif %}
                        {% endfor %}
                    ]
                }]
            });
            var typeChart = echarts.init(document.getElementById('type-chart'));
            typeChart.setOption({
                tooltip: { trigger: 'item' },
                legend: { top: '5%', left: 'center' },
                series: [{
                    name: '问题类型 (type)', type: 'pie', radius: ['40%', '70%'],
                    data: [
                        {% for i in range(clusters.type_categories|length) %}
                        { name: "{{ clusters.type_categories[i] }}", value: {{ clusters.type_counts[i] }} }{% if not loop.last %},{% endif %}
                        {% endfor %}
                    ]
                }]
            });
        </script>
    {% endif %}
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007, debug=True)
