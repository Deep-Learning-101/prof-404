import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional

# 載入環境變數
load_dotenv()

class GeminiService:
    def __init__(self):
        # 從環境變數讀取 Key，兼容本地 .env 與 Hugging Face Secrets
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # 為了避免佈署時報錯，這裡僅印出警告，讓 UI 層處理
            print("警告：找不到 GEMINI_API_KEY")
        
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_id = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")

    def _check_client(self):
        if not self.client:
            raise ValueError("API Key 未設定，請檢查 .env 或 Hugging Face Secrets")

    def search_professors(self, query: str, exclude_names: List[str] = []) -> List[Dict]:
        self._check_client()
        exclusion_prompt = ""
        if exclude_names:
            exclusion_prompt = f"IMPORTANT: Do not include: {', '.join(exclude_names)}."

        # Phase 1: Search (Pure Text)
        search_prompt = f"""
        Using Google Search, find 10 prominent professors in universities across Taiwan who are experts in the field of "{query}".
        
        CRITICAL:
        1. FACT CHECK: Verify they are currently faculty.
        2. RELEVANCE: Their PRIMARY research focus must be "{query}".
        {exclusion_prompt}
        
        List them (Name - University - Department) in Traditional Chinese.
        """

        search_response = self.client.models.generate_content(
            model=self.model_id,
            contents=search_prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        raw_text = search_response.text

        # Phase 2: Extract JSON
        extract_prompt = f"""
        From the text below, extract professor names, universities, and departments.
        Calculate a Relevance Score (0-100) based on query: "{query}".
        
        Return ONLY a JSON array: [{{"name": "...", "university": "...", "department": "...", "relevanceScore": 85}}]
        
        Text:
        ---
        {raw_text}
        ---
        """

        extract_response = self.client.models.generate_content(
            model=self.model_id,
            contents=extract_prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )

        try:
            return json.loads(extract_response.text)
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            return []

    def get_professor_details(self, professor: Dict) -> Dict:
        self._check_client()
        name = professor.get('name')
        uni = professor.get('university')
        dept = professor.get('department')

        prompt = f"""
        Act as an academic consultant. Investigate Professor {name} from {dept} at {uni}.
        
        Find their "Combat Experience" (實戰經驗). Search for:
        1. **Recent Key Publications (Last 5 Years)**: Find 2-3 top papers. **MUST try to find Citation Counts**.
        2. **Alumni Directions**: Where do their graduates work? (e.g., TSMC, Google).
        3. **Industry Collaboration**: Any industry projects?

        Format output in Markdown (Traditional Chinese).
        """

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        # Extract Sources
        sources = []
        if response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web and chunk.web.uri and chunk.web.title:
                    sources.append({"title": chunk.web.title, "uri": chunk.web.uri})
        
        # Deduplicate
        unique_sources = {v['uri']: v for v in sources}.values()

        return {
            "text": response.text,
            "sources": list(unique_sources)
        }

    def chat_with_ai(self, history: List[Dict], new_message: str, context: str) -> str:
        self._check_client()
        system_instruction = f"Source of truth:\n{context}"
        
        chat_history = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            chat_history.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))

        chat = self.client.chats.create(
            model=self.model_id,
            history=chat_history,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        
        response = chat.send_message(new_message)
        return response.text