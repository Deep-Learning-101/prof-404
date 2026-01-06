import gradio as gr
import json
import os
import pandas as pd
from dotenv import load_dotenv
from services import GeminiService
from huggingface_hub import HfApi, hf_hub_download

# Load Env
load_dotenv()
PROF_SAVE_FILE = "saved_professors.json"
COMP_SAVE_FILE = "saved_companies.json"
HF_TOKEN = os.getenv("HF_TOKEN")
DATASET_REPO_ID = os.getenv("DATASET_REPO_ID")

# Init Service
try:
    gemini_service = GeminiService()
except Exception as e:
    print(f"Service Error: {e}")
    gemini_service = None

# --- Shared Helper Functions ---

def load_data(filename):
    data = []
    if HF_TOKEN and DATASET_REPO_ID:
        try:
            hf_hub_download(repo_id=DATASET_REPO_ID, filename=filename, repo_type="dataset", token=HF_TOKEN, local_dir=".")
        except: pass
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f: data = json.load(f)
        except: data = []
    return data

def save_data(data, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except: return
    if HF_TOKEN and DATASET_REPO_ID:
        try:
            api = HfApi(token=HF_TOKEN)
            api.upload_file(path_or_fileobj=filename, path_in_repo=filename, repo_id=DATASET_REPO_ID, repo_type="dataset", commit_message=f"Sync {filename}")
        except: pass

def get_tags_text(item):
    if not item or not item.get('tags'): return "目前標籤: (無)"
    return "🏷️ " + ", ".join([f"`{t}`" for t in item['tags']])

def get_tags_choices(item):
    return item.get('tags', []) if item else []

# --- 🎓 Professor Logic ---

def prof_get_key(p): return f"{p['name']}-{p['university']}"

def prof_format_df(source_list, saved_list):
    if not source_list: return pd.DataFrame(columns=["狀態", "姓名", "大學", "系所", "標籤"])
    if saved_list is None: saved_list = []
    saved_map = {prof_get_key(p): p for p in saved_list}
    data = []
    for p in source_list:
        dp = saved_map.get(prof_get_key(p), p)
        icon = {'match':'✅','mismatch':'❌','pending':'❓'}.get(dp.get('status'), '')
        detail = "📄" if dp.get('details') else ""
        data.append([f"{icon} {detail}", dp['name'], dp['university'], dp['department'], ", ".join(dp.get('tags', []))])
    return pd.DataFrame(data, columns=["狀態", "姓名", "大學", "系所", "標籤"])

def prof_search(query, current_saved):
    if not query: return gr.update(), current_saved, gr.update()
    try:
        res = gemini_service.search_professors(query)
        return prof_format_df(res, current_saved), res, gr.update(visible=True)
    except Exception as e: raise gr.Error(f"搜尋失敗: {e}")

def prof_load_more(query, cur_res, cur_saved):
    if not query: return gr.update(), cur_res
    try:
        new_res = gemini_service.search_professors(query, exclude_names=[p['name'] for p in cur_res])
        exist_keys = set(prof_get_key(p) for p in cur_res)
        for p in new_res:
            if prof_get_key(p) not in exist_keys: cur_res.append(p)
        return prof_format_df(cur_res, cur_saved), cur_res
    except Exception as e: raise gr.Error(f"載入失敗: {e}")

def prof_select(evt: gr.SelectData, search_res, saved_data, view_mode):
    if not evt: return [gr.update()]*8
    idx = evt.index[0]
    target = saved_data if view_mode == "追蹤清單" else search_res
    if not target or idx >= len(target): return [gr.update()]*8
    
    p = target[idx]
    key = prof_get_key(p)
    saved_p = next((x for x in saved_data if prof_get_key(x) == key), None)
    curr = saved_p if saved_p else p
    
    md = ""
    if curr.get('details') and len(curr.get('details')) > 10:
        md = curr['details']
        if not saved_p: saved_data.insert(0, curr); save_data(saved_data, PROF_SAVE_FILE)
    else:
        gr.Info(f"正在調查 {curr['name']}...")
        try:
            res = gemini_service.get_professor_details(curr)
            curr['details'] = res['text']; curr['sources'] = res['sources']
            md = res['text']
            if saved_p: saved_p.update(curr)
            else: saved_data.insert(0, curr)
            save_data(saved_data, PROF_SAVE_FILE)
        except Exception as e: raise gr.Error(f"調查失敗: {e}")
    
    if curr.get('sources'): md += "\n\n### 📚 參考來源\n" + "\n".join([f"- [{s['title']}]({s['uri']})" for s in curr['sources']])
    return gr.update(visible=True), md, [], curr, saved_data, get_tags_text(curr), gr.update(choices=get_tags_choices(curr), value=None), gr.update(visible=True)

def prof_chat(hist, msg, curr):
    if not curr: return hist, ""
    try:
        reply = gemini_service.chat_with_ai(
            [{"role":"user","content":h[0]} for h in hist if h[0]] + ([{"role":"model","content":h[1]} for h in hist if h[1]]),
            msg, curr.get('details', ''), "你是學術顧問，請根據這份教授資料回答"
        )
        hist.append((msg, reply))
    except Exception as e: hist.append((msg, f"Error: {e}"))
    return hist, ""

def prof_add_tag(tag, curr, saved, mode, res):
    if not curr or not tag: return gr.update(), gr.update(), gr.update(), saved, gr.update()
    if 'tags' not in curr: curr['tags'] = []
    if tag not in curr['tags']:
        curr['tags'].append(tag)
        key = prof_get_key(curr)
        found = False
        for i, p in enumerate(saved):
            if prof_get_key(p) == key: saved[i] = curr; found=True; break
        if not found: saved.insert(0, curr)
        save_data(saved, PROF_SAVE_FILE)
    return gr.update(value=""), get_tags_text(curr), gr.update(choices=curr['tags']), saved, prof_format_df(saved if mode=="追蹤清單" else res, saved)

def prof_remove_tag(tag, curr, saved, mode, res):
    if not curr or not tag: return gr.update(), gr.update(), saved, gr.update()
    if 'tags' in curr and tag in curr['tags']:
        curr['tags'].remove(tag)
        key = prof_get_key(curr)
        for i, p in enumerate(saved):
            if prof_get_key(p) == key: saved[i] = curr; break
        save_data(saved, PROF_SAVE_FILE)
    return get_tags_text(curr), gr.update(choices=curr['tags'], value=None), saved, prof_format_df(saved if mode=="追蹤清單" else res, saved)

def prof_update_status(stat, curr, saved, mode, res):
    if not curr: return gr.update(), saved
    curr['status'] = stat if curr.get('status') != stat else None
    key = prof_get_key(curr)
    for i, p in enumerate(saved):
        if prof_get_key(p) == key: saved[i] = curr; break
    save_data(saved, PROF_SAVE_FILE)
    return prof_format_df(saved if mode=="追蹤清單" else res, saved), saved

def prof_remove(curr, saved, mode, res):
    if not curr: return gr.update(), gr.update(value=None), saved, gr.update(visible=False)
    key = prof_get_key(curr)
    new_saved = [p for p in saved if prof_get_key(p) != key]
    save_data(new_saved, PROF_SAVE_FILE)
    return gr.Info("已移除"), prof_format_df(new_saved if mode=="追蹤清單" else res, new_saved), new_saved, gr.update(visible=False)

def prof_toggle(mode, res, saved):
    return prof_format_df(res if mode=="搜尋結果" else saved, saved), gr.update(visible=mode=="搜尋結果")

# --- 🏢 Company Logic ---

def comp_get_key(c): return f"{c['name']}"

def comp_format_df(source_list, saved_list):
    if not source_list: return pd.DataFrame(columns=["狀態", "公司名稱", "產業類別", "標籤"])
    if saved_list is None: saved_list = []
    saved_map = {comp_get_key(c): c for c in saved_list}
    data = []
    for c in source_list:
        dc = saved_map.get(comp_get_key(c), c)
        icon = {'good':'✅','risk':'⚠️','pending':'❓'}.get(dc.get('status'), '')
        detail = "📄" if dc.get('details') else ""
        data.append([f"{icon} {detail}", dc['name'], dc.get('industry','未知'), ", ".join(dc.get('tags', []))])
    return pd.DataFrame(data, columns=["狀態", "公司名稱", "產業類別", "標籤"])

def comp_search(query, current_saved):
    if not query: return gr.update(), current_saved, gr.update()
    try:
        res = gemini_service.search_companies(query)
        return comp_format_df(res, current_saved), res, gr.update(visible=True)
    except Exception as e: raise gr.Error(f"搜尋失敗: {e}")

def comp_load_more(query, cur_res, cur_saved):
    if not query: return gr.update(), cur_res
    try:
        new_res = gemini_service.search_companies(query, exclude_names=[c['name'] for c in cur_res])
        exist_keys = set(comp_get_key(c) for c in cur_res)
        for c in new_res:
            if comp_get_key(c) not in exist_keys: cur_res.append(c)
        return comp_format_df(cur_res, cur_saved), cur_res
    except Exception as e: raise gr.Error(f"載入失敗: {e}")

def comp_select(evt: gr.SelectData, search_res, saved_data, view_mode):
    if not evt: return [gr.update()]*8
    idx = evt.index[0]
    target = saved_data if view_mode == "追蹤清單" else search_res
    if not target or idx >= len(target): return [gr.update()]*8
    
    c = target[idx]
    key = comp_get_key(c)
    saved_c = next((x for x in saved_data if comp_get_key(x) == key), None)
    curr = saved_c if saved_c else c
    
    md = ""
    if curr.get('details') and len(curr.get('details')) > 10:
        md = curr['details']
        if not saved_c: saved_data.insert(0, curr); save_data(saved_data, COMP_SAVE_FILE)
    else:
        gr.Info(f"正在調查 {curr['name']}...")
        try:
            res = gemini_service.get_company_details(curr)
            curr['details'] = res['text']; curr['sources'] = res['sources']
            md = res['text']
            if saved_c: saved_c.update(curr)
            else: saved_data.insert(0, curr)
            save_data(saved_data, COMP_SAVE_FILE)
        except Exception as e: raise gr.Error(f"調查失敗: {e}")
    
    if curr.get('sources'): md += "\n\n### 📚 資料來源\n" + "\n".join([f"- [{s['title']}]({s['uri']})" for s in curr['sources']])
    return gr.update(visible=True), md, [], curr, saved_data, get_tags_text(curr), gr.update(choices=get_tags_choices(curr), value=None), gr.update(visible=True)

def comp_chat(hist, msg, curr):
    if not curr: return hist, ""
    try:
        reply = gemini_service.chat_with_ai(
            [{"role":"user","content":h[0]} for h in hist if h[0]] + ([{"role":"model","content":h[1]} for h in hist if h[1]]),
            msg, curr.get('details', ''), "你是商業顧問，請根據這份公司調查報告回答"
        )
        hist.append((msg, reply))
    except Exception as e: hist.append((msg, f"Error: {e}"))
    return hist, ""

def comp_add_tag(tag, curr, saved, mode, res):
    if not curr or not tag: return gr.update(), gr.update(), gr.update(), saved, gr.update()
    if 'tags' not in curr: curr['tags'] = []
    if tag not in curr['tags']:
        curr['tags'].append(tag)
        key = comp_get_key(curr)
        found = False
        for i, c in enumerate(saved):
            if comp_get_key(c) == key: saved[i] = curr; found=True; break
        if not found: saved.insert(0, curr)
        save_data(saved, COMP_SAVE_FILE)
    return gr.update(value=""), get_tags_text(curr), gr.update(choices=curr['tags']), saved, comp_format_df(saved if mode=="追蹤清單" else res, saved)

def comp_remove_tag(tag, curr, saved, mode, res):
    if not curr or not tag: return gr.update(), gr.update(), saved, gr.update()
    if 'tags' in curr and tag in curr['tags']:
        curr['tags'].remove(tag)
        key = comp_get_key(curr)
        for i, c in enumerate(saved):
            if comp_get_key(c) == key: saved[i] = curr; break
        save_data(saved, COMP_SAVE_FILE)
    return get_tags_text(curr), gr.update(choices=curr['tags'], value=None), saved, comp_format_df(saved if mode=="追蹤清單" else res, saved)

def comp_update_status(stat, curr, saved, mode, res):
    if not curr: return gr.update(), saved
    curr['status'] = stat if curr.get('status') != stat else None
    key = comp_get_key(curr)
    for i, c in enumerate(saved):
        if comp_get_key(c) == key: saved[i] = curr; break
    save_data(saved, COMP_SAVE_FILE)
    return comp_format_df(saved if mode=="追蹤清單" else res, saved), saved

def comp_remove(curr, saved, mode, res):
    if not curr: return gr.update(), gr.update(value=None), saved, gr.update(visible=False)
    key = comp_get_key(curr)
    new_saved = [c for c in saved if comp_get_key(c) != key]
    save_data(new_saved, COMP_SAVE_FILE)
    return gr.Info("已移除"), comp_format_df(new_saved if mode=="追蹤清單" else res, new_saved), new_saved, gr.update(visible=False)

def comp_toggle(mode, res, saved):
    return comp_format_df(res if mode=="搜尋結果" else saved, saved), gr.update(visible=mode=="搜尋結果")

# --- Initialize ---
def prof_init(): d = load_data(PROF_SAVE_FILE); return d, prof_format_df(d, d)
def comp_init(): d = load_data(COMP_SAVE_FILE); return d, comp_format_df(d, d)

# --- UI Layout ---

with gr.Blocks(title="Prof.404.Com 產學導航系統", theme=gr.themes.Soft()) as demo:
    
    gr.Markdown("""
    <div align="center">
    
    # 🚀 Prof.404.Com 產學導航系統 (🎓 Prof.404 - 教授去哪兒？ + 🏢 Com.404 - 公司去那兒？)   
    **學術研究啟程的導航系統，拒絕當科研路上的無頭蒼蠅** | **產業導航、公司徵信、AI 諮詢，拒絕當求職與合作的無頭蒼蠅 🪰**
    **API Rate limits 是 RPD 20，故建議自行 Fork使用** | **產學雙棲、研究導航、商業徵信，你的全方位 AI 顧問**
    
    👉 歡迎 Star [GitHub](https://github.com/Deep-Learning-101/) ⭐ 覺得不錯 👈
    <h3>🧠 補腦專區：<a href="https://deep-learning-101.github.io/" target="_blank">Deep Learning 101</a></h3>
    
    | 🔥 技術傳送門 (Tech Stack) | 📚 必讀心法 (Must Read) |
    | :--- | :--- |
    | 🤖 [**大語言模型 (LLM)**](https://deep-learning-101.github.io/Large-Language-Model) | 🏹 [**策略篇：企業入門策略**](https://deep-learning-101.github.io/Blog/AIBeginner) |
    | 📝 [**自然語言處理 (NLP)**](https://deep-learning-101.github.io/Natural-Language-Processing) | 📊 [**評測篇：臺灣 LLM 分析**](https://deep-learning-101.github.io/Blog/TW-LLM-Benchmark) |
    | 👁️ [**電腦視覺 (CV)**](https://deep-learning-101.github.io//Computer-Vision) | 🛠️ [**實戰篇：打造高精準 RAG**](https://deep-learning-101.github.io/RAG) |
    | 🎤 [**語音處理 (Speech)**](https://deep-learning-101.github.io/Speech-Processing) | 🕳️ [**避坑篇：AI Agent 開發陷阱**](https://deep-learning-101.github.io/agent) |
    </div>
    """)
    

    with gr.Tabs():
        
        # ==========================
        # Tab 1: 🎓 教授去哪兒？
        # ==========================
        with gr.Tab("🎓 找教授 (Prof.404)"):
            prof_saved = gr.State([])
            prof_res = gr.State([])
            prof_sel = gr.State(None)
            
            with gr.Row():
                p_in = gr.Textbox(label="搜尋教授", placeholder="輸入研究領域 (如: LLM)...", scale=4)
                p_btn = gr.Button("🔍 搜尋", variant="primary", scale=1)
            
            p_view = gr.Radio(["搜尋結果", "追蹤清單"], label="顯示模式", value="追蹤清單")
            
            with gr.Row():
                with gr.Column(scale=1):
                    p_df = gr.Dataframe(headers=["狀態","姓名","大學","系所","標籤"], datatype=["str","str","str","str","str"], interactive=False)
                    p_load = gr.Button("載入更多", visible=False)
                
                with gr.Column(scale=2, visible=False) as p_col:
                    p_md = gr.Markdown("...")
                    with gr.Column():
                        gr.Markdown("### 🤖 學術顧問")
                        p_chat = gr.Chatbot(height=250)
                        with gr.Row():
                            p_msg = gr.Textbox(label="提問", scale=4)
                            p_send = gr.Button("送出", scale=1)
                    gr.Markdown("---")
                    with gr.Column(visible=False) as p_tag_row:
                        p_tag_disp = gr.Markdown("標籤: (無)")
                        with gr.Row():
                            p_tag_in = gr.Textbox(label="新增標籤", scale=3)
                            p_tag_add = gr.Button("➕", scale=1)
                        with gr.Accordion("刪除標籤", open=False):
                            with gr.Row():
                                p_tag_drop = gr.Dropdown(label="選擇標籤", choices=[], scale=3)
                                p_tag_del = gr.Button("🗑️", scale=1, variant="secondary")
                    with gr.Row():
                        p_good = gr.Button("✅ 符合")
                        p_bad = gr.Button("❌ 不符")
                        p_pend = gr.Button("❓ 待觀察")
                        p_rem = gr.Button("🗑️ 移除", variant="stop")

            # Wiring Prof
            demo.load(prof_init, None, [prof_saved, p_df])
            p_btn.click(prof_search, [p_in, prof_saved], [p_df, prof_res, p_load]).then(lambda: gr.update(value="搜尋結果"), outputs=[p_view])
            p_load.click(prof_load_more, [p_in, prof_res, prof_saved], [p_df, prof_res])
            p_view.change(prof_toggle, [p_view, prof_res, prof_saved], [p_df, p_load])
            p_df.select(prof_select, [prof_res, prof_saved, p_view], [p_col, p_md, p_chat, prof_sel, prof_saved, p_tag_disp, p_tag_drop, p_tag_row])
            p_send.click(prof_chat, [p_chat, p_msg, prof_sel], [p_chat, p_msg]); p_msg.submit(prof_chat, [p_chat, p_msg, prof_sel], [p_chat, p_msg])
            p_tag_add.click(prof_add_tag, [p_tag_in, prof_sel, prof_saved, p_view, prof_res], [p_tag_in, p_tag_disp, p_tag_drop, prof_saved, p_df])
            p_tag_del.click(prof_remove_tag, [p_tag_drop, prof_sel, prof_saved, p_view, prof_res], [p_tag_disp, p_tag_drop, prof_saved, p_df])
            for btn, s in [(p_good,'match'),(p_bad,'mismatch'),(p_pend,'pending')]: btn.click(prof_update_status, [gr.State(s), prof_sel, prof_saved, p_view, prof_res], [p_df, prof_saved])
            p_rem.click(prof_remove, [prof_sel, prof_saved, p_view, prof_res], [gr.State(None), p_df, prof_saved, p_col])

        # ==========================
        # Tab 2: 🏢 公司去那兒？
        # ==========================
        with gr.Tab("🏢 找公司 (Com.404)"):
            comp_saved = gr.State([])
            comp_res = gr.State([])
            comp_sel = gr.State(None)
            
            with gr.Row():
                c_in = gr.Textbox(label="搜尋公司/領域", placeholder="輸入產業 (如: 量子計算) 或公司名稱...", scale=4)
                c_btn = gr.Button("🔍 搜尋", variant="primary", scale=1)
            
            c_view = gr.Radio(["搜尋結果", "追蹤清單"], label="顯示模式", value="追蹤清單")
            
            with gr.Row():
                with gr.Column(scale=1):
                    c_df = gr.Dataframe(headers=["狀態","公司名稱","產業類別","標籤"], datatype=["str","str","str","str"], interactive=False)
                    c_load = gr.Button("載入更多", visible=False)
                
                with gr.Column(scale=2, visible=False) as c_col:
                    c_md = gr.Markdown("...")
                    with gr.Column():
                        gr.Markdown("### 🤖 商業顧問")
                        c_chat = gr.Chatbot(height=250)
                        with gr.Row():
                            c_msg = gr.Textbox(label="提問", scale=4)
                            c_send = gr.Button("送出", scale=1)
                    gr.Markdown("---")
                    with gr.Column(visible=False) as c_tag_row:
                        c_tag_disp = gr.Markdown("標籤: (無)")
                        with gr.Row():
                            c_tag_in = gr.Textbox(label="新增標籤", scale=3)
                            c_tag_add = gr.Button("➕", scale=1)
                        with gr.Accordion("刪除標籤", open=False):
                            with gr.Row():
                                c_tag_drop = gr.Dropdown(label="選擇標籤", choices=[], scale=3)
                                c_tag_del = gr.Button("🗑️", scale=1, variant="secondary")
                    with gr.Row():
                        c_good = gr.Button("✅ 優質")
                        c_risk = gr.Button("⚠️ 風險")
                        c_pend = gr.Button("❓ 未定")
                        c_rem = gr.Button("🗑️ 移除", variant="stop")

            # Wiring Comp
            demo.load(comp_init, None, [comp_saved, c_df])
            c_btn.click(comp_search, [c_in, comp_saved], [c_df, comp_res, c_load]).then(lambda: gr.update(value="搜尋結果"), outputs=[c_view])
            c_load.click(comp_load_more, [c_in, comp_res, comp_saved], [c_df, comp_res])
            c_view.change(comp_toggle, [c_view, comp_res, comp_saved], [c_df, c_load])
            c_df.select(comp_select, [comp_res, comp_saved, c_view], [c_col, c_md, c_chat, comp_sel, comp_saved, c_tag_disp, c_tag_drop, c_tag_row])
            c_send.click(comp_chat, [c_chat, c_msg, comp_sel], [c_chat, c_msg]); c_msg.submit(comp_chat, [c_chat, c_msg, comp_sel], [c_chat, c_msg])
            c_tag_add.click(comp_add_tag, [c_tag_in, comp_sel, comp_saved, c_view, comp_res], [c_tag_in, c_tag_disp, c_tag_drop, comp_saved, c_df])
            c_tag_del.click(comp_remove_tag, [c_tag_drop, comp_sel, comp_saved, c_view, comp_res], [c_tag_disp, c_tag_drop, comp_saved, c_df])
            for btn, s in [(c_good,'good'),(c_risk,'risk'),(c_pend,'pending')]: btn.click(comp_update_status, [gr.State(s), comp_sel, comp_saved, c_view, comp_res], [c_df, comp_saved])
            c_rem.click(comp_remove, [comp_sel, comp_saved, c_view, comp_res], [gr.State(None), c_df, comp_saved, c_col])

if __name__ == "__main__":
    demo.launch()