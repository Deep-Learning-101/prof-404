# 🎓 Prof.404 - 開箱教授去哪兒？ (Professor Insight Scout)

<div align="center">

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/DeepLearning101/Prof.404)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-black)](https://github.com/Deep-Learning-101/prof-404)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by](https://img.shields.io/badge/Powered%20by-Gemini%20Pro-4285F4?logo=google)](https://deepmind.google/technologies/gemini/)

👉 歡迎 Star ⭐ GitHub 👆 👆 HuggingFace  ⭐ 覺得不錯 👈

**學術研究啟程的導航系統，拒絕當科研路上的無頭蒼蠅 🪰**

[立即體驗 (Hugging Face)](https://huggingface.co/spaces/DeepLearning101/Prof.404) | [Deep Learning 101](https://deep-learning-101.github.io/)

</div>

---

## 🤔 為什麼你需要這個酷東西？

在這個 AI 論文比薩滿還要多的時代，要在茫茫學海中找到「對的人」談何容易？
不管你是想做研究、找產學合作，還是單純想知道台灣誰在搞最新的算法，你是否常覺得自己像隻無頭蒼蠅，撞得一頭血卻找不到方向？

**Prof.404** 是一個基於 Google Gemini 模型的 **學術雷達**。它不只是搜人，更是你的科研情報官：

* 🚀 **科研人員/開發者**：想知道台灣誰在做最新的「後量子密碼」或「具身智能」或「擴散模型」？別再一篇篇翻系所網頁了，AI 直接幫你盤點戰力。
* 🤝 **產業界/企業主**：想找教授做產學合作、技術顧問？這裡能幫你分析教授的實戰經驗與過往產學績效。
* 🎓 **準研究生**：選指導教授就像選對象，適不適合很重要。這裡提供客觀的研究方向與畢業生出路分析，作為你的選組參考。

---

## 🧠 補腦專區：Deep Learning 101

在使用工具飛向宇宙之前，先把裝備穿好。這裡有我們整理的最新乾貨滿滿 AI 技術地圖與實戰心法：

### 🔥 技術傳送門 (Tech Stack)
* 🤖 **大語言模型 (LLM)**: [拆解 LLM 的黑盒子](https://deep-learning-101.github.io/Large-Language-Model)
* 📝 **自然語言處理 (NLP)**: [讓機器聽懂人話](https://deep-learning-101.github.io/Natural-Language-Processing)
* 👁️ **電腦視覺 (CV)**: [像素眼中的世界](https://deep-learning-101.github.io//Computer-Vision)
* 🎤 **語音處理 (Speech)**: [聲音的 AI 魔法](https://deep-learning-101.github.io/Speech-Processing)

### 📚 必讀心法 (Must Read)
* **策略篇** 👉 [AI 新賽局：企業的入門策略指南](https://deep-learning-101.github.io/Blog/AIBeginner)
* **評測篇** 👉 [臺灣 LLM 性能評測與在地化分析](https://deep-learning-101.github.io/Blog/TW-LLM-Benchmark)
* **實戰篇** 👉 [從零到一：打造高精準度 RAG 系統](https://deep-learning-101.github.io/RAG)
* **避坑篇** 👉 [避開 AI Agent 開發陷阱與解決方案](https://deep-learning-101.github.io/agent)

---

## 🚀 快速佈署：只需 3 分鐘，打造你的專屬雷達

我們提供兩種方案，不管你是 Google Sheet 的信徒，還是 Python 的狂熱者，都能輕鬆上手。

### 方案 A：Google Apps Script (GAS) 版
**特色：免費、免伺服器、結合 Google Sheet 自動存檔（超方便！）**

1.  建立一個新的 [Google Apps Script](https://script.google.com/) 專案。
2.  **複製程式碼**：
    * `Code.gs`: 複製本 Repo 中 `prof-404/code.gs` 的內容。
    * `Index.html`: 建立一個 HTML 檔案並複製 `prof-404/Index.html` 的內容。
3.  **設定環境變數** (專案設定 -> 指令碼屬性)：
    * `GEMINI_API_KEY`: 你的 Google Gemini API Key。
    * `SPREADSHEET_ID`: 建立一個 Google Sheet，把網址 `d/` 後面的 ID 貼過來（AI 幫你搜集的資料會自動存進去！）。
    * `GEMINI_MODEL_ID`: (選填) 例如 `gemini-2.5-flash`。
4.  **執行權限驗證**：在編輯器手動執行一次 `getSheet` 函式，同意權限。
5.  **發布**：點擊「部署」->「新增部署」->「網頁應用程式」->「建立新版本」-> 完成！

### 方案 B：Hugging Face Space (Python/Gradio) 版
**特色：介面美觀、一鍵 Fork、支援 Python 生態**

1.  **Fork 專案**：直接到我們的 Space 點擊右上角的 **Duplicate this Space**。
    * 👉 [DeepLearning101/Prof.404](https://huggingface.co/spaces/DeepLearning101/Prof.404)
2.  **設定 Secret**：
    * 進入 Space 的 `Settings` -> `Variables and secrets` -> `Secrets`。
    * 新增 `GEMINI_API_KEY`: 必填：Gemini API 金鑰。
    * 新增 `GEMINI_MODEL_ID`: 選填：模型版本 (改這裡就不需要改程式碼)。
    * 新增 `SAVE_FILE_NAME`: 選填：存檔檔名 (如果你想連這個都設定的話)。

3.  **搞定**：Space 會自動 Build，幾分鐘後就能用了！

*(小提醒：HF Space 免費版重啟後資料會重置，若要永久存檔建議使用 GAS 版或自行串接資料庫)*

---

## 🛠️ 本地開發 (Local Development)

如果你想在自己電腦上魔改這個專案：

```bash
# 1. Clone 專案
git clone https://github.com/Deep-Learning-101/prof-404.git
cd prof-404

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定 .env
# 建立 .env 檔案並填入：
# 必填：Gemini API 金鑰
# GEMINI_API_KEY=你的_AIza_開頭的金鑰
# 選填：模型版本 (改這裡就不需要改程式碼)
# GEMINI_MODEL_ID=gemini-2.5-flash
# 選填：存檔檔名 (如果你想連這個都設定的話)
# SAVE_FILE_NAME=saved_professors.json

# 4. 啟動 Gradio
python app.py