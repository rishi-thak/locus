from app.services.ollama import OllamaService
import json

class ExtractorService:
    def init(self):
        self.ollama = OllamaService()
        self.systemPrompt="""
        You are a graph extraction assistant. Your goal is to extract nodes and edges from text.
        Return ONLY valid JSON. Do not include any preamble or conversational text.
        Few-shot examples:

        Text: Rishi is a student at cal poly, majoring in CS
        JSON:
        JSON: {
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
          "nodes": [
            {"id": "vectr", "label": "Project", "properties": {"name": "Vectr"}},
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
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Extract from this text: {text}"}
        ]
        response = self.ollama.chat(messages, model=os.getenv("EXTRACTOR_MODEL", "qwen2.5:7b"))
        try:
            return json.loads(response['content'])
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            return {"nodes": [], "edges": []}

    