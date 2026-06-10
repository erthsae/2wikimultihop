import pandas as pd
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4j123"   

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def clear_db(tx):
    """清空数据库"""
    tx.run("MATCH (n) DETACH DELETE n")

def create_evidence_path(tx, q_id, question, evidence_path, answer):
    if not evidence_path:
        return
    # 创建问题节点
    tx.run("""
        MERGE (q:Question {id: $id})
        SET q.text = $question, q.answer = $answer
    """, id=q_id, question=question, answer=answer)
    
    for i, triple in enumerate(evidence_path):
        if len(triple) < 3:
            continue
        subj, rel, obj = triple
        # 实体节点
        tx.run("MERGE (e:Entity {name: $name})", name=subj)
        tx.run("MERGE (e:Entity {name: $name})", name=obj)
        # 关系
        tx.run("""
            MATCH (s:Entity {name: $subj})
            MATCH (o:Entity {name: $obj})
            MERGE (s)-[r:RELATION {type: $rel, hop: $hop}]->(o)
            SET r.question_id = $q_id
        """, subj=subj, rel=rel, obj=obj, hop=i+1, q_id=q_id)
        # 第一跳实体与问题关联
        if i == 0:
            tx.run("""
                MATCH (q:Question {id: $q_id})
                MATCH (e:Entity {name: $subj})
                MERGE (q)-[:FIRST_ENTITY]->(e)
            """, q_id=q_id)
    # 答案实体关联
    tx.run("""
        MATCH (q:Question {id: $q_id})
        MATCH (a:Entity {name: $answer})
        MERGE (q)-[:ANSWER_ENTITY]->(a)
    """, q_id=q_id, answer=answer)

def main():
    df = pd.read_parquet('/home/developer/dev.parquet')
    print(f"总数据条数: {len(df)}")
    
    with driver.session() as session:
        for idx, row in df.iterrows():
            q_id = row['_id']
            question = row['question']
            answer = row['answer']
            evidences = row.get('evidences')
            if evidences and isinstance(evidences, list):
                session.execute_write(create_evidence_path, q_id, question, evidences, answer)
            if (idx+1) % 100 == 0:
                print(f"已处理 {idx+1} 条")
        print("导入完成")
    driver.close()

if __name__ == "__main__":
    main()
