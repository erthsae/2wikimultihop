import pandas as pd
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4j123"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def update_question_fields(tx, q_id, q_type, context, supporting_facts):
    # 将 context 和 supporting_facts 转换为 JSON 字符串以便存储
    import json
    context_str = json.dumps(context) if context else None
    supporting_facts_str = json.dumps(supporting_facts) if supporting_facts else None
    
    tx.run("""
        MATCH (q:Question {id: $id})
        SET q.type = $type,
            q.context = $context,
            q.supporting_facts = $supporting_facts
    """, id=q_id, type=q_type, context=context_str, supporting_facts=supporting_facts_str)

def main():
    df = pd.read_parquet('/home/developer/dev.parquet')
    print(f"Total rows: {len(df)}")
    with driver.session() as session:
        for idx, row in df.iterrows():
            q_id = row['_id']
            q_type = row.get('type')
            context = row.get('context')
            supporting_facts = row.get('supporting_facts')
            session.execute_write(update_question_fields, q_id, q_type, context, supporting_facts)
            if idx % 1000 == 0:
                print(f"Processed {idx} rows")
    driver.close()
    print("Done")

if __name__ == "__main__":
    main()
