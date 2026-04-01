from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jService:
    def __init__(self):
        url=os.getenv("NEO4J_URL")
        user=os.getenv("NEO4J_USER")
        password=os.getenv("NEO4J_PASSWORD")
        self.driver=GraphDatabase.driver(url,auth=(user,password))
        self.database=os.getenv("NEO4J_DATABASE", "neo4j")

    def close(self):
        self.driver.close()

    def upsertGraph(self,data):
        with self.driver.session(database=self.database) as session:
            #merging nodes
            for node in data.get('nodes', []):
                session.run("MERGE (n:Entity {id: $id}) SET n.label = $label, n += $properties",
                    id=node['id'],
                    label=node['label'],
                    properties=node.get('properties', {})
                )
            #matching nodes and merging edges
            for edge in data.get('edges', []):
                session.run("""
                    MATCH (a:Entity {id: $source})
                    MATCH (b:Entity {id: $target})
                    MERGE (a)-[r:RELATED_TO {type: $type}]->(b)
                    """,
                    source=edge['source'], 
                    target=edge['target'], 
                    type=edge['type'])
                
if __name__ == "__main__":
    service = Neo4jService()
    test_data = {
        "nodes": [
            {"id": "rishi", "label": "Person", "properties": {"name": "Rishi"}},
            {"id": "cal_poly", "label": "University", "properties": {"name": "Cal Poly"}}
        ],
        "edges": [
            {"source": "rishi", "target": "cal_poly", "type": "STUDENT_AT"}
        ]
    }
    try:
        service.upsertGraph(test_data)
        print("graph updated successfully")
    except Exception as e:
        print(f"error: {e}")
    finally:
        service.close()