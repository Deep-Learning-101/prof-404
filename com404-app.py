import gradio as gr
import json
import os
import pandas as pd
from dotenv import load_dotenv
from services import GeminiService
from huggingface_hub import HfApi, hf_hub_download

# Load Env
load_dotenv()
SAVE_FILE = os.getenv("SAVE_FILE_NAME", "saved_companies.json")
HF_TOKEN = os.getenv("HF_TOKEN")
DATASET_REPO_ID = os.getenv("DATASET_REPO_ID")

# Init Service
try:
    gemini_service = GeminiService()
except Exception as e:
    print(f"Service Error: {e}")
    gemini_service = None

# --- Helper Functions ---

def get_key(c):
    return f"{c['name']}"

def load_data():
    data = []
    # 1. 嘗試從雲端下載
    if HF_TOKEN and DATASET_REPO_ID:
        try:
            print(f"正在同步雲端資料: {DATASET_REPO_ID}...")
            hf_hub_download(
                repo_id=DATASET_REPO_ID,
                filename=SAVE_FILE,
                repo_type="dataset",
                token=HF_TOKEN,
                local_dir="." # 覆蓋本地檔案
            )
            print("雲端同步完成。")
        except Exception as e:
            print(f"雲端同步略過 (初次啟動或無權限): {e}")

    # 2. 讀取檔案
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = []
    return data

def save_data(data):
    # 1. 存本地
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save Error: {e}")
        return

    # 2. 上傳雲端
    if HF_TOKEN and DATASET_REPO_ID:
        try:
            api = HfApi(token=HF_TOKEN)
            api.upload_file(
                path_or_fileobj=SAVE_FILE,
                path_in_repo=SAVE_FILE,
                repo_id=DATASET_REPO_ID,
                repo_type="dataset",
                commit_message="Sync company data"
            )
        except Exception as e:
            print(f"Upload Error: {e}")

def format_df(source_list, saved_list):
    if not source_list:
        return pd.DataFrame(columns=["狀態", "公司名稱", "產業類別", "標籤"])
    
    if saved_list is None:
        saved_list = []
    
    saved_map = {get_key(c): c for c in saved_list}
    
    data = []
    for c in source_list:
        display_c = saved_map.get(get_key(c), c)
        
        status_map = {'good': '✅ 優質', 'risk': '⚠️ 風險', 'pending': '❓ 未定'}
        status_icon = status_map.get(display_c.get('status'), '')
        has_detail = "📄" if display_c.get('details') else ""
        
        tags = ", ".join(display_c.get('tags', []))
        
        data.append([
            f"{status_icon} {has_detail}",
            display_c['name'],
            display_c.get('industry', '未知'),
            tags
        ])
    return pd.DataFrame(data, columns=["狀態", "公司名稱", "產業類別", "標籤"])

def get_tags_text(comp):
    if not comp or not comp.get('tags'):
        return "目前標籤: (無)"
    return "🏷️ " + ", ".join([f"`{t}`" for t in comp['tags']])

def get_tags_choices(comp):
    if not comp: return []
    return comp.get('tags', [])

# --- Event Handlers ---

def search_companies(query, current_saved):
    if not query: return gr.update(), current_saved, gr.update()
    
    try:
        results = gemini_service.search_companies(query)
        return format_df(results, current_saved), results, gr.update(visible=True)
    except Exception as e:
        raise gr.Error(f"搜尋失敗: {e}")

def load_more(query, current_results, current_saved):
    if not query: return gr.update(), current_results
    
    current_names = [c['name'] for c in current_results]
    try:
        new_results = gemini_service.search_companies(query, exclude_names=current_names)
        
        existing_keys = set(get_key(c) for c in current_results)
        for c in new_results:
            if get_key(c) not in existing_keys:
                current_results.append(c)
                
        return format_df(current_results, current_saved), current_results
    except Exception as e:
        raise gr.Error(f"載入失敗: {e}")

def select_company(evt: gr.SelectData, search_results, saved_data, view_mode):
    if not evt: return [gr.update()] * 8
    index = evt.index[0]
    
    target_list = saved_data if view_mode == "追蹤清單" else search_results
    if not target_list or index >= len(target_list): 
        return gr.update(), gr.update(), gr.update(), None, None, gr.update(), gr.update(), gr.update()
    
    comp = target_list[index]
    
    key = get_key(comp)
    saved_comp = next((c for c in saved_data if get_key(c) == key), None)
    current_comp = saved_comp if saved_comp else comp
    
    details_md = ""
    
    # Check Cache
    if current_comp.get('details') and len(current_comp.get('details')) > 10:
        details_md = current_comp['details']
        if not saved_comp: 
            saved_data.insert(0, current_comp)
            save_data(saved_data)
    else:
        # Call API
        gr.Info(f"正在調查 {current_comp['name']} (查詢統編、PTT評價)...")
        try:
            res = gemini_service.get_company_details(current_comp)
            current_comp['details'] = res['text']
            current_comp['sources'] = res['sources']
            details_md = res['text']
            
            if saved_comp:
                saved_comp.update(current_comp)
            else:
                saved_data.insert(0, current_comp)
            save_data(saved_data)
        except Exception as e:
            raise gr.Error(f"調查失敗: {e}")

    if current_comp.get('sources'):
        details_md += "\n\n### 📚 資料來源\n"
        for s in current_comp['sources']:
            details_md += f"- [{s['title']}]({s['uri']})\n"

    return (
        gr.update(visible=True),    
        details_md,                 
        [],                         
        current_comp,               
        saved_data,                 
        get_tags_text(current_comp),           
        gr.update(choices=get_tags_choices(current_comp), value=None), 
        gr.update(visible=True)     
    )

def add_tag(new_tag, selected_comp, saved_data, view_mode, search_results):
    if not selected_comp or not new_tag: 
        return gr.update(), gr.update(), gr.update(), saved_data, gr.update()

    if 'tags' not in selected_comp: selected_comp['tags'] = []
    
    if new_tag not in selected_comp['tags']:
        selected_comp['tags'].append(new_tag)
        
        key = get_key(selected_comp)
        found = False
        for i, c in enumerate(saved_data):
            if get_key(c) == key:
                saved_data[i] = selected_comp
                found = True
                break
        if not found:
            saved_data.insert(0, selected_comp)
        
        save_data(saved_data)
        gr.Info(f"已新增標籤: {new_tag}")
    
    target_list = saved_data if view_mode == "追蹤清單" else search_results
    new_df = format_df(target_list, saved_data)

    return (
        gr.update(value=""), 
        get_tags_text(selected_comp),
        gr.update(choices=selected_comp['tags']),
        saved_data,
        new_df
    )

def remove_tag(tag_to_remove, selected_comp, saved_data, view_mode, search_results):
    if not selected_comp or not tag_to_remove: 
        return gr.update(), gr.update(), saved_data, gr.update()
    
    if 'tags' in selected_comp and tag_to_remove in selected_comp['tags']:
        selected_comp['tags'].remove(tag_to_remove)
        
        key = get_key(selected_comp)
        for i, c in enumerate(saved_data):
            if get_key(c) == key:
                saved_data[i] = selected_comp
                break
        save_data(saved_data)
        gr.Info(f"已移除標籤: {tag_to_remove}")

    target_list = saved_data if view_mode == "追蹤清單" else search_results
    new_df = format_df(target_list, saved_data)
    
    return (
        get_tags_text(selected_comp),
        gr.update(choices=selected_comp['tags'], value=None),
        saved_data,
        new_df
    )

def chat_response(history, message, selected_comp):
    if not selected_comp: return history, ""
    context = selected_comp.get('details', '')
    if not context: return history, ""
    
    service_history = []
    for h in history:
        service_history.append({"role": "user", "content": h[0]})
        if h[1]: service_history.append({"role": "model", "content": h[1]})
            
    try:
        reply = gemini_service.chat_with_ai(service_history, message, context)
        history.append((message, reply))
    except Exception as e:
        history.append((message, f"Error: {e}"))
    return history, ""

def update_status(status, selected_comp, saved_data, view_mode, search_results):
    if not selected_comp: return gr.update(), saved_data
    
    selected_comp['status'] = status if selected_comp.get('status') != status else None
    
    key = get_key(selected_comp)
    for i, c in enumerate(saved_data):
        if get_key(c) == key:
            saved_data[i] = selected_comp
            break
    save_data(saved_data)
    
    target_list = saved_data if view_mode == "追蹤清單" else search_results
    return format_df(target_list, saved_data), saved_data

def remove_comp(selected_comp, saved_data, view_mode, search_results):
    if not selected_comp: return gr.update(), gr.update(value=None), saved_data, gr.update(visible=False)
    
    key = get_key(selected_comp)
    new_saved = [c for c in saved_data if get_key(c) != key]
    save_data(new_saved)
    
    target_list = new_saved if view_mode == "追蹤清單" else search_results
    
    return (
        gr.Info("已移除"), 
        format_df(target_list, new_saved),
        new_saved, 
        gr.update(visible=False)
    )

def toggle_view(mode, search_res, saved_data):
    if mode == "搜尋結果":
        return format_df(search_res, saved_data), gr.update(visible=True)
    else:
        return format_df(saved_data, saved_data), gr.update(visible=False)

def init_on_load():
    data = load_data()
    return data, format_df(data, data)

# --- UI Layout ---

with gr.Blocks(title="Com.404 公司去那兒？", theme=gr.themes.Soft()) as demo:
    
    saved_state = gr.State([])
    search_res_state = gr.State([])
    selected_comp_state = gr.State(None)

    gr.Markdown("""
    <div align="center">
    
    # 🏢 Com.404 - 公司去那兒？
    
    [![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/DeepLearning101/Com.404)
    [![GitHub](https://img.shields.io/badge/GitHub-Repo-black)](https://github.com/Deep-Learning-101/prof-404) 
    [![Powered by](https://img.shields.io/badge/Powered%20by-Gemini%202.0%20Flash-4285F4?logo=google)](https://deepmind.google/technologies/gemini/)
    
    **產業導航、公司徵信、AI 諮詢，拒絕當求職與合作的無頭蒼蠅 🪰**
    <span style="font-size: 0.9em; color: gray;">(支援雲端同步！Space 重啟資料不遺失 🔄 | API KEY RPD，建議自行 Fork)</span>
    
    👉 歡迎 Star [GitHub](https://github.com/Deep-Learning-101/prof-404) ⭐ 覺得不錯 👈
    <h3>🧠 補腦專區：<a href="https://deep-learning-101.github.io/" target="_blank">Deep Learning 101</a></h3>
    
    | 🔥 技術傳送門 (Tech Stack) | 📚 必讀心法 (Must Read) |
    | :--- | :--- |
    | 🤖 [**大語言模型 (LLM)**](https://deep-learning-101.github.io/Large-Language-Model) | 🏹 [**策略篇：企業入門策略**](https://deep-learning-101.github.io/Blog/AIBeginner) |
    | 📝 [**自然語言處理 (NLP)**](https://deep-learning-101.github.io/Natural-Language-Processing) | 📊 [**評測篇：臺灣 LLM 分析**](https://deep-learning-101.github.io/Blog/TW-LLM-Benchmark) |
    | 👁️ [**電腦視覺 (CV)**](https://deep-learning-101.github.io//Computer-Vision) | 🛠️ [**實戰篇：打造高精準 RAG**](https://deep-learning-101.github.io/RAG) |
    | 🎤 [**語音處理 (Speech)**](https://deep-learning-101.github.io/Speech-Processing) | 🕳️ [**避坑篇：AI Agent 開發陷阱**](https://deep-learning-101.github.io/agent) |
    </div>
    """)
    
    with gr.Row():
        search_input = gr.Textbox(label="探索領域或公司", placeholder="輸入產業領域 (如: 量子計算)、技術關鍵字或公司名稱...", scale=4)
        search_btn = gr.Button("🔍 搜尋", variant="primary", scale=1)
    
    with gr.Row():
        view_radio = gr.Radio(["搜尋結果", "追蹤清單"], label="顯示模式", value="追蹤清單")
    
    with gr.Row():
        # Left: List
        with gr.Column(scale=1):
            comp_df = gr.Dataframe(
                headers=["狀態", "公司名稱", "產業類別", "標籤"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="公司列表 (點擊查看詳情)"
            )
            load_more_btn = gr.Button("載入更多", visible=False)
        
        # Right: Details
        with gr.Column(scale=2, visible=False) as details_col:
            detail_md = gr.Markdown("詳細資料...")
            
            # Chat Section
            with gr.Column(elem_classes="chat-section"):
                gr.Markdown("### 🤖 商業顧問 (已閱讀下方報告)")
                # 這裡 Chatbot 使用預設設定 (相容 Tuple 格式)
                chatbot = gr.Chatbot(height=250)
                with gr.Row():
                    msg = gr.Textbox(label="提問", placeholder="例如：這間公司適合新鮮人嗎？有勞資糾紛嗎？", scale=4)
                    send_btn = gr.Button("送出", scale=1)

            gr.Markdown("---")

            # Tags & Status
            with gr.Column(visible=False) as tags_row:
                tags_display = gr.Markdown("目前標籤: (無)")
                with gr.Row():
                    tag_input = gr.Textbox(label="新增標籤", placeholder="例如: 薪水高, 加班多...", scale=3)
                    tag_add_btn = gr.Button("➕ 新增", scale=1)
                with gr.Accordion("刪除標籤", open=False):
                    with gr.Row():
                        tag_dropdown = gr.Dropdown(label="選擇標籤", choices=[], scale=3)
                        tag_del_btn = gr.Button("🗑️ 刪除", scale=1, variant="secondary")
            
            with gr.Row():
                btn_good = gr.Button("✅ 優質")
                btn_risk = gr.Button("⚠️ 風險")
                btn_pending = gr.Button("❓ 未定")
                btn_remove = gr.Button("🗑️ 移除", variant="stop")

    # --- Wiring ---
    
    demo.load(init_on_load, inputs=None, outputs=[saved_state, comp_df])

    # 🌟 這裡修正了：search_companies
    search_btn.click(
        search_companies, 
        inputs=[search_input, saved_state], 
        outputs=[comp_df, search_res_state, load_more_btn]
    ).then(
        lambda: gr.update(value="搜尋結果"), outputs=[view_radio]
    )
    
    load_more_btn.click(
        load_more, 
        inputs=[search_input, search_res_state, saved_state], 
        outputs=[comp_df, search_res_state]
    )
    
    view_radio.change(
        toggle_view, 
        inputs=[view_radio, search_res_state, saved_state], 
        outputs=[comp_df, load_more_btn]
    )
    
    # 🌟 這裡修正了：select_company
    comp_df.select(
        select_company, 
        inputs=[search_res_state, saved_state, view_radio], 
        outputs=[
            details_col, detail_md, chatbot, selected_comp_state, saved_state, 
            tags_display, tag_dropdown, tags_row
        ]
    )
    
    send_btn.click(chat_response, inputs=[chatbot, msg, selected_comp_state], outputs=[chatbot, msg])
    msg.submit(chat_response, inputs=[chatbot, msg, selected_comp_state], outputs=[chatbot, msg])
    
    tag_add_btn.click(
        add_tag, 
        inputs=[tag_input, selected_comp_state, saved_state, view_radio, search_res_state], 
        outputs=[tag_input, tags_display, tag_dropdown, saved_state, comp_df]
    )
    tag_del_btn.click(
        remove_tag, 
        inputs=[tag_dropdown, selected_comp_state, saved_state, view_radio, search_res_state], 
        outputs=[tags_display, tag_dropdown, saved_state, comp_df]
    )
    
    for btn, status in [(btn_good, 'good'), (btn_risk, 'risk'), (btn_pending, 'pending')]:
        btn.click(
            update_status, 
            inputs=[gr.State(status), selected_comp_state, saved_state, view_radio, search_res_state], 
            outputs=[comp_df, saved_state]
        )
    
    # 🌟 這裡修正了：remove_comp
    btn_remove.click(
        remove_comp, 
        inputs=[selected_comp_state, saved_state, view_radio, search_res_state], 
        outputs=[gr.State(None), comp_df, saved_state, details_col]
    )

if __name__ == "__main__":
    demo.launch()