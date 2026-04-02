import ollama
import os
from dotenv import load_dotenv

load_dotenv()

class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.chat_model = os.getenv("CHAT_MODEL", "qwen2.5-coder:14b")
        self.extractor_model = os.getenv("EXTRACTOR_MODEL", "qwen2.5:7b")
        self.embed_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    def chat(self, messages, model=None, options=None):
        target_model = model or self.chat_model
        response = ollama.chat(
            model=target_model,
            messages=messages,
            options=options
            )
        return response['message']

    # def extractEntities(self,text):
    #     # PROMPTING HERE -> we want the extractor model to pull very specific entities/ relationships
    #     # we can use multi-shot prompting to get the model to pull the right things
    #     #TODO - implement multi-shot prompting
    #     prompt= f"Extract entities and relationships from this text as JSON: {text}"
    #     response = ollama.generate(model=self.extractor_model, prompt=prompt, format='json')
    #     return response['response']

    #ABOVE IMPLEMENTED IN EXTRACTOR.PY

    def embed(self,text):
        response= ollama.embeddings(model=self.embed_model, prompt=text)
        return response['embedding']
