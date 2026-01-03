// --- 設定區 ---
const SCRIPT_PROP = PropertiesService.getScriptProperties();

// 1. 讀取 API Key
const API_KEY = SCRIPT_PROP.getProperty('GEMINI_API_KEY'); 

// 2. 讀取 Model ID (如果屬性沒設定，就預設使用 gemini-2.0-flash)
const MODEL_ID = SCRIPT_PROP.getProperty('GEMINI_MODEL_ID') || 'gemini-2.5-flash'; 

// 3. 讀取 Spreadsheet ID (完全依賴屬性設定)
const SPREADSHEET_ID = SCRIPT_PROP.getProperty('SPREADSHEET_ID'); 

// --- 輔助函式：取得試算表 ---
function getSheet() {
  let ss;
  try {
    // 優先嘗試使用屬性中的 ID 開啟
    if (SPREADSHEET_ID) {
      ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    } else {
      // 如果沒設定 ID，嘗試抓取當前綁定的試算表 (適用於容器綁定腳本)
      ss = SpreadsheetApp.getActiveSpreadsheet();
    }
  } catch (e) {
    // 捕捉錯誤並提供更清楚的指示
    throw new Error(`無法開啟試算表。請檢查：\n1. 是否已在「指令碼屬性」設定 SPREADSHEET_ID？\n2. ID 是否正確？\n錯誤訊息: ${e.message}`);
  }

  if (!ss) throw new Error("找不到試算表，請在「專案設定 -> 指令碼屬性」中新增 'SPREADSHEET_ID'。");
  
  let sheet = ss.getSheetByName("SavedProfessors");
  if (!sheet) {
    sheet = ss.insertSheet("SavedProfessors");
    sheet.appendRow(["ID", "Name", "University", "Department", "Tags", "Status", "Note", "Details"]); 
  }
  return sheet;
}

// --- API 核心 ---
function callGeminiAPI(payload) {
  if (!API_KEY) throw new Error("請設定 GEMINI_API_KEY");
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL_ID}:generateContent?key=${API_KEY}`;
  const options = {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };
  const response = UrlFetchApp.fetch(url, options);
  const json = JSON.parse(response.getContentText());
  if (json.error) throw new Error(json.error.message);
  return json;
}

// --- 功能 1: 搜尋教授 ---
function searchProfessors(query, excludeNamesJson) {
  const excludeNames = excludeNamesJson ? JSON.parse(excludeNamesJson) : [];
  let exclusionPrompt = "";
  if (excludeNames.length > 0) {
    exclusionPrompt = `IMPORTANT: Do not include: ${excludeNames.join(', ')}.`;
  }

  // Phase 1: Search
  const searchPrompt = `
    Using Google Search, find 10 prominent professors in Taiwan in field: "${query}".
    CRITICAL: FACT CHECK they are current faculty. RELEVANCE must be high.
    ${exclusionPrompt}
    List them (Name - University - Department).
  `;
  const searchPayload = {
    contents: [{ parts: [{ text: searchPrompt }] }],
    tools: [{ google_search: {} }]
  };
  const searchResult = callGeminiAPI(searchPayload);
  const rawText = searchResult.candidates[0].content.parts[0].text;

  // Phase 2: Extract JSON
  const extractPrompt = `
    Extract professor names, universities, departments from text.
    Calculate Relevance Score (0-100) for query: "${query}".
    Return JSON array ONLY: [{"name": "...", "university": "...", "department": "...", "relevanceScore": 85}]
    Text: ${rawText}
  `;
  const extractPayload = {
    contents: [{ parts: [{ text: extractPrompt }] }],
    generationConfig: { response_mime_type: "application/json" }
  };
  const extractResult = callGeminiAPI(extractPayload);
  return JSON.parse(extractResult.candidates[0].content.parts[0].text);
}

// --- 功能 2: 詳細調查 ---
function getProfessorDetails(profDataJson) {
  const prof = JSON.parse(profDataJson);
  const prompt = `
    Investigate Professor ${prof.name} (${prof.department}, ${prof.university}).
    Find "Combat Experience":
    1. Key Publications (Last 5 Years) with Citation Counts.
    2. Alumni Directions (Jobs).
    3. Industry Collaboration.
    Format in Markdown (Traditional Chinese).
  `;
  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    tools: [{ google_search: {} }]
  };
  const result = callGeminiAPI(payload);
  const text = result.candidates[0].content.parts[0].text;
  
  let sources = [];
  const grounding = result.candidates[0].groundingMetadata;
  if (grounding && grounding.groundingChunks) {
    sources = grounding.groundingChunks
      .filter(c => c.web?.uri && c.web?.title)
      .map(c => ({ title: c.web.title, uri: c.web.uri }));
    sources = sources.filter((v,i,a)=>a.findIndex(t=>(t.uri===v.uri))===i);
  }
  return { text: text, sources: sources };
}

// --- 功能 3: 聊天 ---
function chatWithAI(historyJson, newMessage, context) {
  const history = JSON.parse(historyJson);
  let contents = [{ role: "user", parts: [{ text: `Source of truth:\n${context}` }] }, { role: "model", parts: [{ text: "OK" }] }];
  history.forEach(h => contents.push({ role: h.role, parts: [{ text: h.content }] }));
  contents.push({ role: "user", parts: [{ text: newMessage }] });

  const payload = { contents: contents };
  const result = callGeminiAPI(payload);
  return result.candidates[0].content.parts[0].text;
}

// --- 功能 4: 資料庫讀取 ---
function getSavedProfessors() {
  const sheet = getSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) return [];
  
  const data = sheet.getRange(2, 1, lastRow - 1, 8).getValues();
  return data.map(row => ({
    id: row[0],
    name: row[1],
    university: row[2],
    department: row[3],
    tags: row[4] ? String(row[4]).split(",") : [],
    status: row[5],
    note: row[6],
    details: row[7] || "" 
  })).reverse();
}

// --- 功能 5: 資料庫寫入 ---
function saveOrUpdateProfessor(profJson) {
  const prof = JSON.parse(profJson);
  const sheet = getSheet();
  const lastRow = sheet.getLastRow();
  const id = `${prof.name}-${prof.university}`;
  
  let rowIndex = -1;
  if (lastRow > 1) {
    const ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues().flat();
    rowIndex = ids.indexOf(id);
  }

  const rowData = [
    id, prof.name, prof.university, prof.department,
    (prof.tags || []).join(","),
    prof.status || "pending",
    prof.note || "",
    prof.details || "" 
  ];

  if (rowIndex > -1) {
    sheet.getRange(rowIndex + 2, 1, 1, 8).setValues([rowData]);
  } else {
    sheet.appendRow(rowData);
  }
  return getSavedProfessors();
}

// --- 功能 6: 刪除教授 (新增) ---
function deleteProfessor(profJson) {
  const prof = JSON.parse(profJson);
  const sheet = getSheet();
  const lastRow = sheet.getLastRow();
  const id = `${prof.name}-${prof.university}`;
  
  if (lastRow > 1) {
    const ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues().flat();
    const rowIndex = ids.indexOf(id);
    
    if (rowIndex > -1) {
      sheet.deleteRow(rowIndex + 2); // 刪除該行
    }
  }
  return getSavedProfessors();
}

// --- Web App 入口 ---
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
      .evaluate()
      .setTitle('Prof.404，開箱教授去哪兒？')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}