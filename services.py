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
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("警告：找不到 GEMINI_API_KEY")
        
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_id = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")

    def _check_client(self):
        if not self.client:
            raise ValueError("API Key 未設定，請檢查 .env 或 Hugging Face Secrets")

    # ==========================
    # 🎓 教授搜尋相關功能
    # ==========================
    def search_professors(self, query: str, exclude_names: List[str] = []) -> List[Dict]:
        self._check_client()
        exclusion_prompt = ""
        if exclude_names:
            exclusion_prompt = f"IMPORTANT: Do not include: {', '.join(exclude_names)}."

        # Phase 1: Search
        search_prompt = f"""
        Using Google Search, find 10 prominent professors in universities across Taiwan who are experts in the field of "{query}".
        CRITICAL: FACT CHECK they are current faculty. RELEVANCE must be high.
        {exclusion_prompt}
        List them (Name - University - Department) in Traditional Chinese.
        """
        search_response = self.client.models.generate_content(
            model=self.model_id, contents=search_prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        
        # Phase 2: Extract JSON
        extract_prompt = f"""
        From the text below, extract professor names, universities, and departments.
        Calculate a Relevance Score (0-100) based on query: "{query}".
        Return ONLY a JSON array: [{{"name": "...", "university": "...", "department": "...", "relevanceScore": 85}}]
        Text: --- {search_response.text} ---
        """
        extract_response = self.client.models.generate_content(
            model=self.model_id, contents=extract_prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        try: return json.loads(extract_response.text)
        except: return []

    def get_professor_details(self, professor: Dict) -> Dict:
        self._check_client()
        name, uni, dept = professor.get('name'), professor.get('university'), professor.get('department')
        prompt = f"""
        Act as an academic consultant. Investigate Professor {name} from {dept} at {uni}.
        Find "Combat Experience":
        1. **Key Publications (Last 5 Years)**: Find 2-3 top papers with Citation Counts.
        2. **Alumni Directions**: Where do their graduates work?
        3. **Industry Collaboration**: Any industry projects?
        Format output in Markdown (Traditional Chinese).
        """
        response = self.client.models.generate_content(
            model=self.model_id, contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        return self._format_response_with_sources(response)

    # ==========================
    # 🏢 公司搜尋相關功能
    # ==========================
    def search_companies(self, query: str, exclude_names: List[str] = []) -> List[Dict]:
        self._check_client()
        exclusion_prompt = ""
        if exclude_names:
            exclusion_prompt = f"IMPORTANT: Do not include: {', '.join(exclude_names)}."

        # Phase 1: Search
        search_prompt = f"""
        Using Google Search, find 5 to 10 prominent companies in Taiwan related to: "{query}".
        Instructions:
        1. If "{query}" is an industry (e.g. AI), list representative Taiwanese companies.
        2. If "{query}" is a name, list the company and competitors.
        {exclusion_prompt}
        List them (Full Name - Industry/Main Product) in Traditional Chinese.
        """
        search_response = self.client.models.generate_content(
            model=self.model_id, contents=search_prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )

        # Phase 2: Extract JSON
        extract_prompt = f"""
        From text, extract company names and industry.
        Calculate Relevance Score (0-100) for query: "{query}".
        Return ONLY JSON array: [{{"name": "...", "industry": "...", "relevanceScore": 85}}]
        Text: --- {search_response.text} ---
        """
        extract_response = self.client.models.generate_content(
            model=self.model_id, contents=extract_prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json')
        )
        try: return json.loads(extract_response.text)
        except: return []

    def get_company_details(self, company: Dict) -> Dict:
        self._check_client()
        name = company.get('name')
        prompt = f"""
        Act as a "Business Analyst". Investigate Taiwanese company: "{name}".
        Targets:
        1. **Overview**: Tax ID (統編), Capital (資本額), Representative.
        2. **Workforce & Culture**: Employee count, Reviews from PTT(Tech_Job)/Dcard/Qollie (Pros & Cons).
        3. **Legal & Risks**: Search for "{name} 勞資糾紛", "{name} 判決", "{name} 違反勞基法".
        Format in Markdown (Traditional Chinese). Be objective.
        """
        response = self.client.models.generate_content(
            model=self.model_id, contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        return self._format_response_with_sources(response)

    # ==========================
    # 共用功能
    # ==========================
    def _format_response_with_sources(self, response):
        sources = []
        if response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.grounding_chunks:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web and chunk.web.uri and chunk.web.title:
                    sources.append({"title": chunk.web.title, "uri": chunk.web.uri})
        unique_sources = {v['uri']: v for v in sources}.values()
        return {"text": response.text, "sources": list(unique_sources)}

    def chat_with_ai(self, history: List[Dict], new_message: str, context: str, role_instruction: str = "Source of truth") -> str:
        self._check_client()
        system_instruction = f"{role_instruction}:\n{context}"
        
        chat_history = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            chat_history.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))

        chat = self.client.chats.create(
            model=self.model_id, history=chat_history,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        response = chat.send_message(new_message)
        return response.text