---
license: mit
title: Prof.404.Com 產學導航系統
sdk: gradio
emoji: 👀
colorFrom: purple
colorTo: pink
pinned: true
short_description: 'Status code 404: 🎓 Prof.404 - 教授去哪兒？ + 🏢 Com.404 - 公司去那兒？'
sdk_version: 6.2.0
---

# Prof.404.Com 產學導航系統
_🎓 Prof.404 - 教授去哪兒？ + 🏢 Com.404 - 公司去那兒？_

<div align="center">

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/DeepLearning101/Prof.404.Com)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-black)](https://github.com/Deep-Learning-101/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by](https://img.shields.io/badge/Powered%20by-Gemini%202.0%20Flash-4285F4?logo=google)](https://deepmind.google/technologies/gemini/)

👉 歡迎 Star [GitHub](https://github.com/Deep-Learning-101/) ⭐ 覺得不錯 👈

**🚀 Prof.404.Com 產學導航系統 (🎓 Prof.404 - 教授去哪兒？ + 🏢 Com.404 - 公司去那兒？)**  
**學術研究啟程、產業導航、公司徵信、AI 諮詢的導航系統，拒絕當科研路/求職與合作上的無頭蒼蠅**  
**API Rate limits 是 RPD 20，建議自行 Fork使用** | **產學雙棲、研究導航、商業徵信，你的全方位 AI 顧問**  
**(支援雲端同步！Space 重啟資料不遺失 🔄)**  

<h3>🧠 補腦專區：<a href="https://deep-learning-101.github.io/" target="_blank">Deep Learning 101</a></h3>

| 🔥 技術傳送門 (Tech Stack) | 📚 必讀心法 (Must Read) |
| :--- | :--- |
| 🤖 [**大語言模型 (LLM)**](https://deep-learning-101.github.io/Large-Language-Model) | 🏹 [**策略篇：企業入門策略**](https://deep-learning-101.github.io/Blog/AIBeginner) |
| 📝 [**自然語言處理 (NLP)**](https://deep-learning-101.github.io/Natural-Language-Processing) | 📊 [**評測篇：臺灣 LLM 分析**](https://deep-learning-101.github.io/Blog/TW-LLM-Benchmark) |
| 👁️ [**電腦視覺 (CV)**](https://deep-learning-101.github.io//Computer-Vision) | 🛠️ [**實戰篇：打造高精準 RAG**](https://deep-learning-101.github.io/RAG) |
| 🎤 [**語音處理 (Speech)**](https://deep-learning-101.github.io/Speech-Processing) | 🕳️ [**避坑篇：AI Agent 開發陷阱**](https://deep-learning-101.github.io/agent) |

</div>

---

## 🤔 為什麼你需要這個？

在這個 AI 論文比薩滿還要多的時代 ...  
想做研究、找產學合作，還是單純想知道台灣誰在搞最新的算法，你是否常覺得自己像隻無頭蒼蠅，撞得一頭血卻找不到方向？  
傳統求職網只能搜公司名，卻不能告訴你「這個領域誰是老大」；傳統論壇只能爬文，卻不能幫你「總結 100 篇抱怨文的重點」。  
要在茫茫學海中找到「對的人」談何容易？「想做 AI 但不知道台灣有哪些公司？」、「想去這家公司但怕是家族企業？」  

**Prof.404.Com** 是一個基於 Google Gemini 模型的 **學術/產業雷達與徵信 Agent**。它能幫你：  

* 🌐 **產業探索**：輸入「量子計算」或「綠能」，直接列出台灣相關領域的代表公司。  
* 🕵️‍♂️ **深度調查**：自動搜尋統編、資本額、PTT/Dcard 評價、掃描勞資糾紛與判決書。  
* 💬 **AI 顧問**：看完報告還有疑問？直接問：「這間公司適合新鮮人嗎？」、「薪資結構如何？」。  
* 🚀 **科研人員/開發者**：想知道台灣誰在做最新的「後量子密碼」或「具身智能」？別再一篇篇翻系所網頁了，AI 直接幫你盤點戰力。  
* 🤝 **產業界/企業主**：想找教授做產學合作、技術顧問？這裡能幫你分析教授的實戰經驗與過往產學績效。  
* 🎓 **準研究生**：選指導教授就像選對象，適不適合很重要。這裡提供客觀的研究方向與畢業生出路分析，作為你的選組參考。  

---

## 🚀 快速佈署 (Hugging Face Space)

我們提供兩種方案，不管你是 Google Sheet 的信徒，還是 Python 的狂熱者，都能輕鬆上手。

### 方案 A：Google Apps Script (GAS) 版
**特色：免費、免伺服器、結合 Google Sheet 自動存檔（最簡單！）**

1.  建立一個新的 [Google Apps Script](https://script.google.com/) 專案。
2.  **複製程式碼**：
    * `Code.gs`: 複製本 Repo 中 `prof-404/code.gs` 的內容。
    * `Index.html`: 建立一個 HTML 檔案並複製 `prof-404/Index.html` 的內容。
3.  **設定環境變數** (專案設定 -> 指令碼屬性)：
    * `GEMINI_API_KEY`: 你的 Google Gemini API Key。
    * `SPREADSHEET_ID`: 建立一個 Google Sheet，把網址 `d/` 後面的 ID 貼過來（AI 幫你搜集的資料會自動存進去！）。
    * `GEMINI_MODEL_ID`: (選填) 例如 `gemini-2.0-flash`。
4.  **執行權限驗證**：在編輯器手動執行一次 `getSheet` 函式，同意權限。
5.  **發布**：點擊「部署」->「新增部署」->「網頁應用程式」->「建立新版本」-> 完成！

### 方案 B：Hugging Face Space (Python/Gradio) 版
**特色：介面美觀、一鍵 Fork、支援雲端同步 (資料不遺失)**

1.  **準備雲端資料庫** (若不需雲端存檔可跳過)：
    * 到 HF 建立一個新的 **Dataset** (建議設為 Private)，記下 ID (如 `YourName/prof-data`)。
2.  **Fork 專案**：直接到我們的 Space 點擊右上角的 **Duplicate this Space**。
    * 👉 [DeepLearning101/Prof.404](https://huggingface.co/spaces/DeepLearning101/Prof.404.Com)
3.  **設定 Secret** (Settings -> Variables and secrets -> Secrets)：
    * `GEMINI_API_KEY`: **(必填)** Gemini API 金鑰。
    * `HF_TOKEN`: **(選填)** 你的 HF Access Token (需有 Write 權限)，用於同步資料。
    * `DATASET_REPO_ID`: **(選填)** 步驟 1 建立的 Dataset ID (例如 `DeepLearning101/prof-data`)。
    * `GEMINI_MODEL_ID`: (選填) 預設 `gemini-2.0-flash`。
4.  **搞定**：Space 會自動 Build。設定好 `HF_TOKEN` 後，**即使 Space 重啟，你的追蹤清單也會自動從 Dataset 還原！**

---

## 🛠️ 本地開發

```bash
# 1. Clone 專案
git clone [https://github.com/Deep-Learning-101/prof-404.git](https://github.com/Deep-Learning-101/prof-404.git)
cd prof-404

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定 .env
# GEMINI_API_KEY=你的Key
# SAVE_FILE_NAME=saved_companies.json
# HF_TOKEN=... (選填)
# DATASET_REPO_ID=... (選填)

# 4. 啟動
python app.py