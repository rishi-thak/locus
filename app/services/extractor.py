from app.services.ollama import OllamaService
import json
import os
import re

class ExtractorService:
    def __init__(self):
        self.ollama = OllamaService()
        self.systemPrompt="""
        You are a graph extraction assistant. 
        - Your goal is to extract nodes and edges ONLY from the provided text.
        - Do not include any preamble or conversational text. 
        - DO NOT use any external knowledge about people or companies.
        - If a sentence mentions two things, there MUST be an edge between them.

        FOR EVERY EXTRACTION, YOU MUST:
        - REASON: think step-by-step about which entities are mentioned and how they relate.
        - RESOLVE: follow the entity resolution rules strictly.
        - MAP: create a JSON object with 'reasoning', 'nodes', and 'edges'.

        ENTITY RESOLUTION RULES:
        - ALWAYS use 'rishi' as the id for 'rishi thakkar' or 'rishi'
        - ALWAYS use 'vectr' as the id for 'vectr' or 'vectr ai'
        - ALWAYS use 'cal_poly' as the id for 'cal poly' or 'cal poly slo'
        - use lowercase_snake_case for all other ids

        EXTRACTION RULES:
        - EVERY entity mentioned in an edge MUST have a corresponding entry in the nodes array.
        - DO NOT create nodes for numbers, quantities, or abstract concepts (e.g., '50_developers').
        - Use properties to store extra details like names or counts.

        Return ONLY valid JSON. 

        Few-shot examples:

        Text: Rishi is a student at cal poly, majoring in CS
        JSON: {
          "reasoning": "user mentioned 'Rishi', applying rule: id is 'rishi'. 'cal poly' maps to 'cal_poly'.",
          "nodes": [
            {"id": "rishi", "label": "Person", "properties": {"name": "Rishi"}},
            {"id": "cal_poly", "label": "University", "properties": {"name": "Cal Poly"}},
            {"id": "cs", "label": "Major", "properties": {"name": "Computer Science"}}
          ],
          "edges": [
            {"source": "rishi", "target": "cal_poly", "type": "STUDENT_AT"},
            {"source": "rishi", "target": "cs", "type": "MAJORS_IN"}
          ]
        }

        Text: vectr is an intelligence-native workspace built by rishi and scott
        JSON: {
          "reasoning": "user mentioned 'vectr ai', applying rule: id is 'vectr'. 'rishi' and 'scott' map to 'vectr'.",
          "nodes": [
            {"id": "vectr", "label": "Project", "properties": {"name": "Vectr"}},
            {"id": "rishi", "label": "Person", "properties": {"name": "Rishi"}},
            {"id": "scott", "label": "Person", "properties": {"name": "Scott"}}
          ],
          "edges": [
            {"source": "rishi", "target": "vectr", "type": "CONTRIBUTOR_TO"},
            {"source": "scott", "target": "vectr", "type": "CONTRIBUTOR_TO"}
          ]
        }
        """

    def extract(self, text):
        messages=[
            {"role": "system", "content": self.systemPrompt},
            {"role": "user", "content": f"Extract from this text: {text}"}
        ]
        response = self.ollama.chat(messages, model=os.getenv("EXTRACTOR_MODEL", "qwen2.5:7b"))
        content = response['content']
        print(f"DEBUG: raw extractor output: {content}")
        try:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            json_str = match.group() if match else content
            return json.loads(json_str)
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            return {"nodes": [], "edges": []}

    