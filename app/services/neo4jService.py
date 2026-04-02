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

            for node_id in data.get('deletions', {}).get('nodes', []):
                session.run("MATCH (n {id: $id}) DETACH DELETE n", id=node_id)
            for edge in data.get('deletions', {}).get('edges', []):
                session.run(
                    "MATCH (a {id: $source})-[r]->(b {id: $target}) DELETE r",
                    source=edge['source'], target=edge['target']
                )

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
    
    def getGraph(self):
        with self.driver.session(database=self.database) as session:
            query = "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m"
            result = session.run(query)

            nodes = {}
            links = []

            for record in result:
                nodeN = record['n']
                nID= nodeN['id']
                if nID not in nodes:
                    nodes[nID]= {"id": nID, "label": nodeN['label'], "properties": dict(nodeN)}

                if record['r']:
                    nodeM = record['m']
                    mID = nodeM['id']
                    if mID not in nodes:
                        nodes[mID] = {"id": mID, "label": nodeM['label'], "properties": dict(nodeM)}

                    links.append({
                        "source": nID,
                        "target": mID,
                        "type": record['r'].get('type', 'RELATED_TO')
                    })
            
            return {"nodes": list(nodes.values()), "links": links}

    #keyword extraction, graphrag in a way
    def getContext(self, queryText):
        keywords = [word.lower().strip('?.!,') for word in queryText.split() if len(word) > 3]
        if not keywords:
            return ""
        cypher = """
            MATCH (n)
            WHERE any(prop IN keys(n) WHERE toLower(toString(n[prop])) CONTAINS $k)
            OPTIONAL MATCH (n)-[r]-(neighbor)
            RETURN n.id as node, r.type as rel, neighbor.id as target
            LIMIT 15
        """

        facts = []
        with self.driver.session(database=self.database) as session:
            for kw in keywords:
                result = session.run(cypher, k=kw)
                for record in result:
                    if record["rel"]:
                        facts.append(f"{record['node']} {record['rel']} {record['target']}")
                    else:
                        facts.append(f"found entity: {record['node']}")

        return "\n".join(list(set(facts)))
                    
                
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