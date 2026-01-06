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
            raise ValueError("API Key 未設定")

    def search_companies(self, query: str, exclude_names: List[str] = []) -> List[Dict]:
        """
        Step 1: 領域探索 -> 公司列表
        """
        self._check_client()
        exclusion_prompt = ""
        if exclude_names:
            exclusion_prompt = f"IMPORTANT: Do not include: {', '.join(exclude_names)}."

        # Phase 1: Google Search (廣泛探索)
        # 這裡的 Prompt 強調：如果使用者輸入的是「領域(如: AI)」，請列出該領域的台灣代表性公司。
        search_prompt = f"""
        Using Google Search, find 5 to 10 prominent companies in Taiwan related to the query: "{query}".
        
        **Instructions:**
        1. **Domain Search:** If "{query}" is an industry or technology (e.g., "AI", "Green Energy"), list the top representative Taiwanese companies in this field.
        2. **Company Search:** If "{query}" is a specific name, list that company and its direct competitors.
        3. **Target:** Focus on Taiwanese companies (or global companies with major R&D in Taiwan).
        {exclusion_prompt}
        
        List them (Full Name - Industry/Main Product) in Traditional Chinese.
        """

        search_response = self.client.models.generate_content(
            model=self.model_id,
            contents=search_prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        raw_text = search_response.text

        # Phase 2: Extract JSON (結構化)
        extract_prompt = f"""
        From the text below, extract company names and their industry/main product.
        Calculate a Relevance Score (0-100) based on query: "{query}".
        
        Return ONLY a JSON array: [{{"name": "...", "industry": "...", "relevanceScore": 85}}]
        
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

    def get_company_details(self, company: Dict) -> Dict:
        """
        Step 2: 進行商業徵信調查 (Deep Dive)
        """
        self._check_client()
        name = company.get('name')
        
        prompt = f"""
        Act as a professional "Business Analyst & Investigator". 
        Conduct a comprehensive investigation on the Taiwanese company: "{name}".

        **Investigation Targets:**

        1.  **Overview (基本盤)**:
            - **Tax ID (統編)** & **Capital (資本額)**. (Try to find specific numbers)
            - **Representative (代表人)**.
            - **Core Business**: What specific problem do they solve? What is their "Ace" product?

        2.  **Workforce & Culture (內部情報)**:
            - **Employee Count**.
            - **Reviews/Gossip**: Search **PTT (Tech_Job, Soft_Job)**, **Dcard**, **Qollie**.
            - Summarize the *REAL* work vibe (e.g., "Good for juniors but low ceiling", "Free snacks but forced overtime").

        3.  **Legal & Risks (排雷專區)**:
            - Search: "{name} 勞資糾紛", "{name} 違反勞基法", "{name} 判決", "{name} 罰款".
            - List any red flags found in government records or news.

        **Format**:
        - Use Markdown.
        - Language: Traditional Chinese (繁體中文).
        - Be objective but don't sugarcoat potential risks.
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
        
        unique_sources = {v['uri']: v for v in sources}.values()

        return {
            "text": response.text,
            "sources": list(unique_sources)
        }

    def chat_with_ai(self, history: List[Dict], new_message: str, context: str) -> str:
        self._check_client()
        system_instruction = f"You are an expert Business Consultant. Answer based on this company report:\n{context}"
        
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