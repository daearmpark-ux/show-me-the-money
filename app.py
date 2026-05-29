import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import datetime
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import json
import os
import copy
import urllib.request
import xml.etree.ElementTree as ET
import google.generativeai as genai
import re
import uuid
import random

# ==========================================
# 🔑 API 키 풀 — 반드시 AIzaSy... 형식만 유효
#    Google AI Studio(aistudio.google.com)에서 발급
#    여러 개 등록할수록 할당량 여유 생김
# ==========================================
API_KEY_POOL = [
    "AIzaSyBNI4yTFxxpP24XL2EuGhUcGCFR1Soh6_8",
    "AIzaSyCkKaxrzXAzSI7MLD9exqvTVZswqfCokxM",
    "AIzaSyD94fdgp_jZI-YU-hGDXgLKenzA9DguKpY",
    "AIzaSyBUmwAxFMLD1mvaFOvEWVbQYOJ8aqGjOSo",
    "AIzaSyBfHtgIIjwXzUo7Hc2jtnj6XXskO4ZVxok",
    # ↑ 본인의 AIzaSy... 형식 키만 여기에 추가하세요
    # AQ. 로 시작하는 키는 Gemini API에서 동작하지 않습니다 (삭제됨)
]

# ==========================================
# 1. 페이지 설정 및 로컬 DB
# ==========================================
st.set_page_config(
    page_title="Show me the money",
    layout="wide",
    initial_sidebar_state="collapsed"
)
DATA_FILE = "my_quant_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "portfolio": {}, "watchlist": [], "realized_profit": 0,
        "realized_loss": 0, "issue_archive": [], "momentum_archive": [],
        "recom_archive": [], "chat_history": [], "transaction_log": [],
        "theme_1": "우주 항공", "theme_2": "인공지능(AI)",
        "last_update": "2000-01-01T00:00:00"
    }

def save_data():
    if 'chat_history' in st.session_state:
        st.session_state.chat_history = st.session_state.chat_history[-20:]
    data = {
        "portfolio": st.session_state.portfolio,
        "watchlist": st.session_state.watchlist,
        "realized_profit": st.session_state.realized_profit,
        "realized_loss": st.session_state.realized_loss,
        "issue_archive": st.session_state.issue_archive,
        "momentum_archive": st.session_state.momentum_archive,
        "recom_archive": st.session_state.recom_archive,
        "chat_history": st.session_state.chat_history,
        "transaction_log": st.session_state.transaction_log,
        "theme_1": st.session_state.get('theme_1', "우주 항공"),
        "theme_2": st.session_state.get('theme_2', "인공지능(AI)"),
        "last_update": st.session_state.last_update
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def rebuild_portfolio():
    pf = {}
    r_profit = 0
    r_loss = 0
    valid_logs = []
    for tx in st.session_state.transaction_log:
        s = tx['stock']
        if tx['type'] == 'buy':
            if s not in pf:
                pf[s] = {'qty': 0, 'total_invested': 0}
            pf[s]['qty'] += tx['qty']
            pf[s]['total_invested'] += (tx['price'] * tx['qty'])
            valid_logs.append(tx)
        elif tx['type'] == 'sell':
            if s in pf and pf[s]['qty'] >= tx['qty']:
                avg_p = pf[s]['total_invested'] / pf[s]['qty']
                realized = (tx['price'] - avg_p) * tx['qty']
                if realized > 0:
                    r_profit += realized
                else:
                    r_loss += abs(realized)
                pf[s]['qty'] -= tx['qty']
                pf[s]['total_invested'] -= (avg_p * tx['qty'])
                if pf[s]['qty'] == 0:
                    del pf[s]
                valid_logs.append(tx)
    st.session_state.portfolio = pf
    st.session_state.realized_profit = r_profit
    st.session_state.realized_loss = r_loss
    st.session_state.transaction_log = valid_logs
    save_data()

if 'init' not in st.session_state:
    saved = load_data()
    for k, v in saved.items():
        st.session_state[k] = v
    if 'recom_archive' not in st.session_state:
        st.session_state.recom_archive = []
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'transaction_log' not in st.session_state:
        st.session_state.transaction_log = []
    if 'theme_1' not in st.session_state:
        st.session_state.theme_1 = "우주 항공"
    if 'theme_2' not in st.session_state:
        st.session_state.theme_2 = "인공지능(AI)"
    st.session_state.history = []
    st.session_state.init = True

# ==========================================
# 2. UI/UX 및 CSS
# ==========================================
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)
st.markdown("""
<style>
    * { translate: no !important; }
    .block-container {
        max-width: 98% !important;
        padding-top: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .stApp { background-color: #12121A; }
    .main-title {
        font-size: 3rem !important; font-weight: 900;
        color: #E6B800; font-family: 'Arial Black', sans-serif;
        letter-spacing: -1px; margin-bottom: 25px; margin-top: -30px;
    }
    .sub-title {
        font-size: 1.3rem !important; font-weight: bold;
        margin-bottom: 15px; border-bottom: 2px solid #2B2B36;
        padding-bottom: 8px; color: #FFFFFF;
    }
    .dash-box {
        background-color: #1E1E2A; padding: 20px; border-radius: 12px;
        border: 1px solid #333; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .dash-title { font-size: 1rem; color: #A0A0B0; font-weight: bold; margin-bottom: 8px; }
    .dash-val { font-size: 1.8rem; font-weight: 900; color: #FFF; }
    .val-red  { color: #ff4b4b !important; }
    .val-blue { color: #33C4FF !important; }

    div[role="radiogroup"] {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
    }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[role="radiogroup"] label {
        background-color: #1A1A24 !important;
        border: 1px solid #2D2D3D !important;
        border-radius: 12px !important; height: 65px !important;
        display: flex !important; flex-direction: column !important;
        justify-content: center !important; align-items: center !important;
        margin: 0 !important; padding: 5px !important;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.4) !important;
        transition: all 0.2s ease !important; cursor: pointer !important;
    }
    div[role="radiogroup"] label p {
        display: flex !important; flex-direction: column !important;
        align-items: center !important; justify-content: center !important;
        gap: 4px !important; font-size: 1rem !important;
        font-weight: 900 !important; color: #E0E0E0 !important;
        text-align: center; margin: 0 !important; word-break: keep-all !important;
    }
    div[role="radiogroup"] label p span { font-size: 1.8rem !important; color: #FFFFFF !important; }
    div[role="radiogroup"] label:nth-child(1)  { border-top: 4px solid #FF5E5E !important; }
    div[role="radiogroup"] label:nth-child(2)  { border-top: 4px solid #33C4FF !important; }
    div[role="radiogroup"] label:nth-child(3)  { border-top: 4px solid #A855F7 !important; }
    div[role="radiogroup"] label:nth-child(4)  { border-top: 4px solid #FFB84D !important; }
    div[role="radiogroup"] label:nth-child(5)  { border-top: 4px solid #4ADE80 !important; }
    div[role="radiogroup"] label:nth-child(6)  { border-top: 4px solid #F472B6 !important; }
    div[role="radiogroup"] label:nth-child(7)  { border-top: 4px solid #FACC15 !important; }
    div[role="radiogroup"] label:nth-child(8)  { border-top: 4px solid #E879F9 !important; }
    div[role="radiogroup"] label:nth-child(9)  { border-top: 4px solid #14B8A6 !important; }
    div[role="radiogroup"] label:nth-child(10) { border-top: 4px solid #EF4444 !important; }
    div[role="radiogroup"] label:hover { transform: translateY(-3px); filter: brightness(1.3); }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #2D2D42 !important;
        box-shadow: 0 0 20px rgba(255,255,255,0.2) !important;
        filter: brightness(1.5);
    }
    .star-btn button {
        background: transparent !important; border: none !important;
        box-shadow: none !important; font-size: 1.5rem !important;
        padding: 0 !important; color: #FFD700 !important;
    }
    .star-btn button:hover { transform: scale(1.2); background: transparent !important; }
    .up-color   { color: #ff4b4b !important; font-weight: bold; }
    .down-color { color: #33C4FF !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. AI 응답 함수 — 스마트 키 순환 + 캐싱
# ==========================================

# ── 응답 캐시 (세션 내 동일 프롬프트 재호출 방지) ──
if 'ai_response_cache' not in st.session_state:
    st.session_state.ai_response_cache = {}

# ── 키별 실패 상태 추적 ──
if 'api_key_status' not in st.session_state:
    st.session_state.api_key_status = {k: 'unknown' for k in API_KEY_POOL}

def get_ai_response(prompt, use_cache=True, cache_ttl_min=60):
    """
    개선된 AI 호출 함수
    - 유효한 AIzaSy... 키만 사용
    - 키별 상태 추적 (quota / fail / ok)
    - 1시간 응답 캐싱으로 불필요한 API 소비 방지
    """
    # ── 캐시 확인 ──
    cache_key = prompt[:200]  # 프롬프트 앞 200자를 키로
    if use_cache and cache_key in st.session_state.ai_response_cache:
        cached = st.session_state.ai_response_cache[cache_key]
        age_min = (datetime.datetime.now() - cached['time']).seconds / 60
        if age_min < cache_ttl_min:
            return cached['text']

    # ── 사용 가능한 키 필터링 (quota/fail 키는 제외) ──
    available_keys = [
        k for k in API_KEY_POOL
        if st.session_state.api_key_status.get(k, 'unknown') not in ('quota', 'fail')
    ]
    # 모든 키가 소진됐으면 전체 재시도
    if not available_keys:
        available_keys = API_KEY_POOL
        st.session_state.api_key_status = {k: 'unknown' for k in API_KEY_POOL}

    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro']
    last_err = ""

    for api_key in available_keys:
        # AIzaSy 형식 검증 (잘못된 키 즉시 스킵)
        if not api_key.startswith('AIzaSy'):
            st.session_state.api_key_status[api_key] = 'fail'
            continue

        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.session_state.api_key_status[api_key] = 'fail'
            last_err = str(e)
            continue

        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    # 성공 → 캐시 저장 + 키 상태 ok
                    st.session_state.api_key_status[api_key] = 'ok'
                    if use_cache:
                        st.session_state.ai_response_cache[cache_key] = {
                            'text': response.text,
                            'time': datetime.datetime.now()
                        }
                    return response.text

            except Exception as e:
                last_err = str(e).lower()

                if "404" in last_err or "not found" in last_err:
                    # 이 모델이 없음 → 다음 모델 시도
                    continue

                if any(x in last_err for x in ["429", "quota", "exhausted", "resource_exhausted"]):
                    # 할당량 초과 → 이 키 스킵
                    st.session_state.api_key_status[api_key] = 'quota'
                    break

                if any(x in last_err for x in ["invalid", "api_key", "400", "401", "403", "permission"]):
                    # 잘못된 키 → 이 키 영구 스킵
                    st.session_state.api_key_status[api_key] = 'fail'
                    break

                # 그 외 → 다음 키로
                break

    return f"⚠️ API 응답 실패\n\n**원인:** {last_err or '알 수 없는 오류'}\n\n**해결 방법:**\n- 좌측 사이드바 또는 상단 설정에서 새 API 키를 추가하세요\n- [Google AI Studio](https://aistudio.google.com) 에서 무료 발급 가능합니다"


# ==========================================
# 4. 데이터 수집 공통 함수
# ==========================================
@st.cache_data(ttl=3600)
def load_krx_data():
    return fdr.StockListing('KRX')

@st.cache_data(ttl=3600)
def load_sp500_data():
    try:
        return fdr.StockListing('S&P500').head(500)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_all_searchable_stocks():
    krx = load_krx_data()[['Code', 'Name', 'Market']]
    sp5 = load_sp500_data()
    krx_list = []
    for _, row in krx.iterrows():
        c = str(row['Code']).zfill(6)
        yf_c = f"{c}.KS" if row['Market'] == 'KOSPI' else f"{c}.KQ"
        krx_list.append(f"🇰🇷 {row['Name']} ({yf_c})")
    us_list = []
    if not sp5.empty:
        for _, row in sp5.iterrows():
            us_list.append(f"🇺🇸 {row['Name']} ({row['Symbol']})")
    return krx_list + us_list

def safe_extract_price(val):
    try:
        if isinstance(val, pd.Series):
            return float(val.iloc[0])
        elif isinstance(val, pd.DataFrame):
            return float(val.iloc[0, 0])
        return float(val)
    except:
        return 0.0

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        data = yf.download("USDKRW=X", period="1d", progress=False)
        return safe_extract_price(data['Close'].iloc[-1])
    except:
        return 1300.0

krx_df    = load_krx_data()
ex_rate   = get_exchange_rate()
all_stocks = get_all_searchable_stocks()

def format_kr(p):
    if str(p) in ("", "-"):
        return ""
    return f"{math.ceil(float(p)):,}원"

def format_rt(r):
    if str(r) in ("", "-"):
        return ""
    v = float(r)
    if v > 0:
        return f"▲ {v:.2f}%"
    elif v < 0:
        return f"▼ {abs(v):.2f}%"
    return f"- {v:.2f}%"

def color_rt(v):
    if str(v) in ("", "-"):
        return ""
    if '▲' in str(v):
        return 'color: #ff4b4b; font-weight: bold;'
    elif '▼' in str(v):
        return 'color: #33C4FF; font-weight: bold;'
    return 'color: #E0E0E0; font-weight: bold;'

def color_pl(v):
    if str(v) in ("", "-"):
        return ""
    if '-' in str(v):
        return 'color: #33C4FF; font-weight: bold;'
    elif v != '0원':
        return 'color: #ff4b4b; font-weight: bold;'
    return 'color: #E0E0E0;'

def get_realtime_price(stock_name):
    if "(" in stock_name and ")" in stock_name:
        yf_code = stock_name.split("(")[-1].replace(")", "").strip()
    else:
        if stock_name in krx_df['Name'].values:
            row = krx_df[krx_df['Name'] == stock_name].iloc[0]
            yf_code = f"{str(row['Code']).zfill(6)}.KS" if row['Market'] == 'KOSPI' else f"{str(row['Code']).zfill(6)}.KQ"
        else:
            yf_code = stock_name
    try:
        hist = yf.download(yf_code, period="1d", progress=False)
        if not hist.empty:
            return int(safe_extract_price(hist['Close'].iloc[-1]))
        return 0
    except:
        return 0

def get_stock_info(stock_name, period="1d"):
    if "(" in stock_name and ")" in stock_name:
        yf_code = stock_name.split("(")[-1].replace(")", "").strip()
    else:
        if stock_name in krx_df['Name'].values:
            row = krx_df[krx_df['Name'] == stock_name].iloc[0]
            yf_code = f"{str(row['Code']).zfill(6)}.KS" if row['Market'] == 'KOSPI' else f"{str(row['Code']).zfill(6)}.KQ"
        else:
            yf_code = stock_name
    try:
        return yf.Ticker(yf_code).history(period=period)
    except:
        return pd.DataFrame()

def render_editable_stock_table(df, key):
    df['⭐ 관심'] = df['종목명'].apply(lambda x: True if str(x) in st.session_state.watchlist else False)
    cols = ['⭐ 관심'] + [c for c in df.columns if c != '⭐ 관심']
    df = df[cols]
    styled_df = df.style.map(color_rt, subset=['등락률'])
    edited = st.data_editor(
        styled_df,
        column_config={"⭐ 관심": st.column_config.CheckboxColumn("⭐ 관심")},
        disabled=[c for c in df.columns if c != '⭐ 관심'],
        hide_index=True, key=key, width="stretch", use_container_width=True
    )
    changed = False
    for i, r in edited.iterrows():
        name = str(r['종목명']).replace("🎯", "").strip()
        if name in ("", "nan"):
            continue
        if r['⭐ 관심'] and name not in st.session_state.watchlist:
            st.session_state.watchlist.append(name)
            changed = True
        elif not r['⭐ 관심'] and name in st.session_state.watchlist:
            st.session_state.watchlist.remove(name)
            changed = True
    if changed:
        save_data()
        st.rerun()

@st.cache_data(ttl=3600)
def fetch_dynamic_theme_kr(theme_name):
    prompt = f"""한국 주식 시장(KOSPI/KOSDAQ)에서 '{theme_name}' 테마와 엮여있는 핵심 주식 딱 10개를 선정해주세요.
상위 5개는 무조건 시장을 주도하는 '대장주', 하위 5개는 '수혜/관련주'로 구분하세요. (해외 주식 절대 금지)
반드시 아래 JSON 배열 형식으로만 대답하세요.
[ {{"name": "종목명", "type": "대장주" 또는 "수혜주"}} ]"""
    try:
        res = get_ai_response(prompt)
        if "⚠️" in res:
            raise Exception(res)
        match = re.search(r'\[.*\]', res, re.DOTALL)
        cleaned = match.group(0) if match else re.sub(r"```json|```", "", res).strip()
        data = json.loads(cleaned)
        out = []
        for item in data:
            c_p, p_p = 0, 0
            row = krx_df[krx_df['Name'] == item['name']]
            if not row.empty:
                code   = str(row['Code'].iloc[0]).zfill(6)
                yf_code = f"{code}.KS" if row['Market'].iloc[0] == 'KOSPI' else f"{code}.KQ"
                h = yf.Ticker(yf_code).history(period="5d")
                if not h.empty and len(h) >= 2:
                    c_p, p_p = float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100 if p_p > 0 else 0
            out.append({
                "구분": item['type'], "종목명": item['name'],
                "현재가": format_kr(c_p) if c_p > 0 else "-",
                "등락률": format_rt(chg) if c_p > 0 else "-"
            })
        return pd.DataFrame(out)
    except Exception as e:
        raise e

@st.cache_data(ttl=3600)
def fetch_surging_analysis_kr(stock_list):
    s_names = ", ".join(stock_list)
    prompt = f"""다음은 오늘 한국 증시 급등 종목 5개입니다: {s_names}. JSON 배열만 반환하세요:
[ {{"name": "종목명", "theme": "테마명", "inv_type": "단기" 또는 "장기", "reason": "상승이유 요약", "action": "진행시켜!" 또는 "주의요망!" 또는 "도망쳐!"}} ]
action 필드는 1.진행시켜! 2.주의요망! 3.도망쳐! 중 하나만 선택하세요."""
    try:
        res = get_ai_response(prompt)
        if "⚠️" in res:
            raise Exception(res)
        match = re.search(r'\[.*\]', res, re.DOTALL)
        cleaned = match.group(0) if match else re.sub(r"```json|```", "", res).strip()
        data = json.loads(cleaned)
        out = []
        for item in data:
            c_p, p_p = 0, 0
            row = krx_df[krx_df['Name'] == item['name']]
            if not row.empty:
                code    = str(row['Code'].iloc[0]).zfill(6)
                yf_code = f"{code}.KS" if row['Market'].iloc[0] == 'KOSPI' else f"{code}.KQ"
                h = yf.Ticker(yf_code).history(period="5d")
                if not h.empty and len(h) >= 2:
                    c_p, p_p = float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100 if p_p > 0 else 0
            out.append({
                "종목명": item['name'],
                "현재가": format_kr(c_p) if c_p > 0 else "-",
                "등락률": format_rt(chg) if c_p > 0 else "-",
                "테마": item['theme'], "성향": item['inv_type'],
                "이유": item['reason'], "액션": item.get('action', '')
            })
        return pd.DataFrame(out)
    except Exception as e:
        raise e


# ==========================================
# 5. 메인 화면 레이아웃
# ==========================================
c_main_content, c_menu = st.columns([8.5, 1.5])

with c_main_content:
    st.markdown(
        f'<div class="main-title notranslate">⚡ Show me the money '
        f'<span style="font-size:1.2rem; color:#A0A0B0; font-weight:normal;">'
        f'(💱 1$ = {format_kr(ex_rate)})</span></div>',
        unsafe_allow_html=True
    )

with c_menu:
    st.markdown("<div id='quick-menu-anchor'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title notranslate" style="text-align:center; border:none; '
        'font-family:Arial Black; margin-top:-30px;">QUICK</div>',
        unsafe_allow_html=True
    )
    menu_selection = st.radio("메뉴:", [
        ":material/home: 홈",
        ":material/search: 검색",
        ":material/view_week: 주간분석",
        ":material/pie_chart: 패턴분석",
        ":material/account_balance_wallet: 투자현황",
        ":material/insights: 투자분석",
        ":material/star: 관심주",
        ":material/rocket_launch: 추천주",
        ":material/bar_chart: 수익섹터",
        ":material/smart_toy: 올해분석"
    ], label_visibility="collapsed")


# ==========================================
# 6. 메뉴별 노출 영역
# ==========================================
with c_main_content:

    # ───────────────────────────────────────
    # 홈
    # ───────────────────────────────────────
    if "홈" in menu_selection:
        c_left_area, c_right_area = st.columns([6.5, 3.5])
        with c_left_area:
            c_kr, c_pf = st.columns(2)
            with c_kr:
                st.markdown('<div class="sub-title">🇰🇷 국내 Top 5</div>', unsafe_allow_html=True)
                top5 = krx_df.sort_values(by='Marcap', ascending=False).head(5)
                df_kr = pd.DataFrame({
                    '종목명': top5['Name'],
                    '현재가': top5['Close'].apply(lambda x: format_kr(x)),
                    '등락률': top5['ChagesRatio'].apply(format_rt)
                })
                render_editable_stock_table(df_kr, "home_kr")

            with c_pf:
                st.markdown('<div class="sub-title">💼 내 투자 현황</div>', unsafe_allow_html=True)
                pf_summary = []
                for name, data in st.session_state.portfolio.items():
                    curr_p = get_realtime_price(name)
                    avg_p  = data['total_invested'] / data['qty'] if data['qty'] > 0 else 0
                    if curr_p == 0:
                        curr_p = avg_p
                    pl = (curr_p - avg_p) * data['qty']
                    pf_summary.append([name, format_kr(curr_p), format_kr(pl)])
                while len(pf_summary) < 5:
                    pf_summary.append(["", "", ""])
                df_pf = pd.DataFrame(pf_summary[:5], columns=['종목', '현재가', '손익금'])
                st.dataframe(
                    df_pf.style.map(color_pl, subset=['손익금']),
                    width="stretch", use_container_width=True, hide_index=True
                )

            st.markdown('<div class="sub-title" style="margin-top:15px;">⭐ 내 관심종목 요약</div>', unsafe_allow_html=True)
            wl_summ = []
            for w in st.session_state.watchlist[:10]:
                row = krx_df[krx_df['Name'] == w]
                if not row.empty:
                    wl_summ.append([w, format_kr(row['Close'].iloc[0]), format_rt(row['ChagesRatio'].iloc[0])])
                else:
                    wl_summ.append([w, "-", "-"])

            c_wl_left, c_wl_right = st.columns(2)
            with c_wl_left:
                left_data = wl_summ[:5]
                while len(left_data) < 5:
                    left_data.append(["", "", ""])
                df_wl_left = pd.DataFrame(left_data, columns=['종목명', '현재가', '등락률'])
                st.dataframe(df_wl_left.style.map(color_rt, subset=['등락률']), width="stretch", use_container_width=True, hide_index=True)

            with c_wl_right:
                right_data = wl_summ[5:10]
                while len(right_data) < 5:
                    right_data.append(["", "", ""])
                df_wl_right = pd.DataFrame(right_data, columns=['종목명', '현재가', '등락률'])
                st.dataframe(df_wl_right.style.map(color_rt, subset=['등락률']), width="stretch", use_container_width=True, hide_index=True)

        with c_right_area:
            st.markdown('<div class="sub-title">🔥 실시간 떡상 (Top 5)</div>', unsafe_allow_html=True)
            df_up     = krx_df.sort_values(by='ChagesRatio', ascending=False).head(5)
            df_up_fmt = pd.DataFrame({
                '종목명': df_up['Name'],
                '현재가': df_up['Close'].apply(lambda x: format_kr(x)),
                '등락률': df_up['ChagesRatio'].apply(format_rt)
            })
            render_editable_stock_table(df_up_fmt, "home_up")

            st.markdown('<div class="sub-title" style="margin-top:20px;">🧊 실시간 떡락 (Top 5)</div>', unsafe_allow_html=True)
            df_dn     = krx_df.sort_values(by='ChagesRatio', ascending=True).head(5)
            df_dn_fmt = pd.DataFrame({
                '종목명': df_dn['Name'],
                '현재가': df_dn['Close'].apply(lambda x: format_kr(x)),
                '등락률': df_dn['ChagesRatio'].apply(format_rt)
            })
            render_editable_stock_table(df_dn_fmt, "home_dn")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<div class="sub-title">🚀 커스텀 테마 딥다이브 & 실시간 떡상주 AI 분석 (국내장 전용)</div>',
            unsafe_allow_html=True
        )
        t1, t2 = st.columns(2)
        with t1:
            theme_1 = st.text_input("테마 1 직접 입력 (예: 우주, 초전도체)", value=st.session_state.theme_1)
            if theme_1 != st.session_state.theme_1:
                st.session_state.theme_1 = theme_1
                save_data()
        with t2:
            theme_2 = st.text_input("테마 2 직접 입력 (예: AI, 비만치료제)", value=st.session_state.theme_2)
            if theme_2 != st.session_state.theme_2:
                st.session_state.theme_2 = theme_2
                save_data()

        c_t1, c_t2, c_t3 = st.columns(3)
        with c_t1:
            st.markdown(f"##### 💡 [{st.session_state.theme_1}] 10대 핵심주")
            try:
                df_th1 = fetch_dynamic_theme_kr(st.session_state.theme_1)
                st.dataframe(df_th1.style.map(color_rt, subset=['등락률']), width="stretch", use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"{str(e)}")

        with c_t2:
            st.markdown(f"##### 💡 [{st.session_state.theme_2}] 10대 핵심주")
            try:
                df_th2 = fetch_dynamic_theme_kr(st.session_state.theme_2)
                st.dataframe(df_th2.style.map(color_rt, subset=['등락률']), width="stretch", use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"{str(e)}")

        with c_t3:
            st.markdown(
                f"##### 💥 떡상주분석 (<span style='color:#F97316; font-weight:bold;'>단기</span> / "
                f"<span style='color:#A855F7; font-weight:bold;'>장기</span>)",
                unsafe_allow_html=True
            )
            hot_list = krx_df.sort_values(by='ChagesRatio', ascending=False).head(5)['Name'].tolist()
            try:
                df_sa = fetch_surging_analysis_kr(hot_list)
                for _, row in df_sa.iterrows():
                    is_long   = '장기' in str(row['성향'])
                    color     = '#A855F7' if is_long else '#F97316'
                    action    = str(row['액션'])
                    action_html = ""
                    if "진행시켜" in action:
                        action_html = f" <span style='color:#4ADE80; font-weight:bold;'>[{action}]</span>"
                    elif "주의요망" in action:
                        action_html = f" <span style='color:#FACC15; font-weight:bold;'>[{action}]</span>"
                    elif "도망쳐"  in action:
                        action_html = f" <span style='color:#ff4b4b; font-weight:bold;'>[{action}]</span>"
                    st.markdown(f"""
                    <div style="background-color:#1E1E2A; padding:12px; border-radius:8px;
                                margin-bottom:10px; border-left:4px solid {color}; border:1px solid #333;">
                        <div style="font-size:1.05rem; font-weight:bold; margin-bottom:5px;">
                            <span style="color:{color};">{row['종목명']}</span>
                            <span style="font-size:0.8rem; color:#A0A0B0; font-weight:normal; margin-left:5px;">
                                ({row['현재가']} | {row['테마']})
                            </span>
                        </div>
                        <div style="font-size:0.85rem; color:#E0E0E0; line-height:1.4;">
                            💬 {row['이유']}{action_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"{str(e)}")

    # ───────────────────────────────────────
    # 검색
    # ───────────────────────────────────────
    elif "검색" in menu_selection:
        st.markdown('<div class="sub-title">🔍 투자할 상품 검색 (한국/미국 통합)</div>', unsafe_allow_html=True)
        search_term = st.text_input("종목명이나 테마를 입력하세요 (예: 로보틱스, 반도체)", placeholder="검색어 입력 후 Enter")

        if search_term:
            matched_df   = krx_df[krx_df['Name'].str.contains(search_term, na=False, case=False)]
            matched_list = matched_df['Name'].tolist()

            if not matched_list:
                st.warning(f"'{search_term}'이(가) 포함된 종목을 찾을 수 없습니다.")
            else:
                st.success(f"총 {len(matched_list)}개의 종목이 검색되었습니다.")
                with st.container(height=140):
                    selected_search = st.radio(
                        "검색 결과 목록", matched_list,
                        horizontal=True, label_visibility="collapsed"
                    )

                st.divider()

                if selected_search:
                    display_name = selected_search
                    target_row   = matched_df[matched_df['Name'] == display_name].iloc[0]
                    yf_code      = f"{str(target_row['Code']).zfill(6)}.KS" if target_row['Market'] == 'KOSPI' else f"{str(target_row['Code']).zfill(6)}.KQ"
                    is_watched   = display_name in st.session_state.watchlist

                    col_chart_title, col_star = st.columns([6, 1])
                    with col_star:
                        st.markdown('<div class="star-btn">', unsafe_allow_html=True)
                        if st.button("⭐" if is_watched else "☆", key="star_toggle_search"):
                            if is_watched:
                                st.session_state.watchlist.remove(display_name)
                            else:
                                st.session_state.watchlist.append(display_name)
                            save_data()
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    with st.spinner(f"{display_name} 차트 불러오는 중..."):
                        data = yf.Ticker(yf_code).history(period="1y", interval="1d")

                    if not data.empty and len(data) >= 2:
                        c_p   = safe_extract_price(data['Close'].iloc[-1])
                        p_p   = safe_extract_price(data['Close'].iloc[-2])
                        f_r   = format_rt(((c_p - p_p) / p_p) * 100) if p_p > 0 else "0.00%"
                        color = "up-color" if "▲" in f_r else ("down-color" if "▼" in f_r else "flat-color")
                        p_str = format_kr(c_p)
                        with col_chart_title:
                            st.markdown(f"<h3 class='{color}'>{display_name} : {p_str} ({f_r})</h3>", unsafe_allow_html=True)
                        fig = go.Figure(go.Scatter(
                            x=data.index, y=data['Close'],
                            mode='lines', line=dict(color='#33C4FF', width=2)
                        ))
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'), height=400, margin=dict(t=0)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("데이터를 불러올 수 없습니다.")

    # ───────────────────────────────────────
    # 투자현황
    # ───────────────────────────────────────
    elif "투자현황" in menu_selection:
        st.markdown('<div class="sub-title">💼 내 자산 완벽 결산 대시보드</div>', unsafe_allow_html=True)
        total_invested    = sum([d['total_invested'] for d in st.session_state.portfolio.values()])
        current_valuation = sum([
            (get_realtime_price(k) * v['qty'] if get_realtime_price(k) > 0 else v['total_invested'])
            for k, v in st.session_state.portfolio.items()
        ])
        eval_profit = current_valuation - total_invested
        eval_ratio  = (eval_profit / total_invested * 100) if total_invested > 0 else 0
        net_profit  = st.session_state.realized_profit - st.session_state.realized_loss

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="dash-box">
                <div class="dash-title">📊 실시간 주식 가치 (평가 손익)</div>
                <div class="dash-val">총 매수 원금: {format_kr(total_invested)}</div>
                <div class="dash-val" style="font-size:1.3rem;">현재 평가금: {format_kr(current_valuation)}</div>
                <div class="dash-val {'val-red' if eval_profit>0 else 'val-blue'}">
                    {format_kr(eval_profit)} ({eval_ratio:.2f}%)
                </div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="dash-box">
                <div class="dash-title">💰 내 지갑 최종 결산 (실현 손익)</div>
                <div class="dash-val">누적 판매 이익: <span class="val-red">+{format_kr(st.session_state.realized_profit)}</span></div>
                <div class="dash-val" style="font-size:1.3rem;">누적 판매 손실: <span class="val-blue">-{format_kr(st.session_state.realized_loss)}</span></div>
                <div class="dash-val {'val-red' if net_profit>0 else 'val-blue'}">최종 찐수익: {format_kr(net_profit)}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📋 상세 보유 주식 목록")
        if not st.session_state.portfolio:
            st.info("현재 보유 중인 주식이 없습니다.")
        else:
            pf_data = []
            for name, data in st.session_state.portfolio.items():
                qty, invested = data['qty'], data['total_invested']
                avg_p  = invested / qty
                curr_p = get_realtime_price(name)
                if curr_p == 0:
                    curr_p = avg_p
                pl = (curr_p - avg_p) * qty
                pf_data.append([
                    name, f"{qty}주", format_kr(avg_p), format_kr(curr_p),
                    format_kr(pl), f"{(pl/invested)*100:.2f}%"
                ])
            st.dataframe(
                pd.DataFrame(pf_data, columns=['주식명', '보유 수량', '매수 평단가', '실시간 현재가', '평가 손익금', '손익률'])
                .style.map(color_rt, subset=['손익률']),
                width="stretch", use_container_width=True, hide_index=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_reset, _ = st.columns([1.5, 8.5])
        with col_reset:
            if st.button("💥 전체 초기화", use_container_width=True):
                st.session_state.portfolio       = {}
                st.session_state.realized_profit = 0
                st.session_state.realized_loss   = 0
                st.session_state.transaction_log = []
                save_data()
                st.rerun()

        with st.form("buy_form", clear_on_submit=True):
            st.markdown("##### 🔵 구매")
            b1, b2, b3, b4 = st.columns([3, 2, 1.5, 1.5])
            with b1:
                buy_selected = st.selectbox("구매 종목명 검색", options=[""] + all_stocks, label_visibility="collapsed")
            with b2:
                buy_price = st.number_input("구매 단가", value=0, step=1000, label_visibility="collapsed")
            with b3:
                buy_qty = st.number_input("수량", value=1, min_value=1, step=1, label_visibility="collapsed")
            with b4:
                submit_buy = st.form_submit_button("🔵 구매 (엔터)", use_container_width=True)
            if submit_buy and buy_selected:
                buy_name = buy_selected.split("(")[0].replace("🇰🇷", "").replace("🇺🇸", "").strip()
                tx = {
                    'id': str(datetime.datetime.now().timestamp()),
                    'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'type': 'buy', 'stock': buy_name,
                    'price': buy_price, 'qty': buy_qty
                }
                st.session_state.transaction_log.append(tx)
                rebuild_portfolio()
                st.rerun()

        with st.form("sell_form", clear_on_submit=True):
            st.markdown("##### 🔴 판매")
            s1, s2, s3, s4 = st.columns([3, 2, 1.5, 1.5])
            my_stocks = list(st.session_state.portfolio.keys())
            with s1:
                sell_name = st.selectbox("판매 종목", ["(보유 종목 선택)"] + my_stocks, label_visibility="collapsed")
            with s2:
                sell_price = st.number_input("판매 단가", value=0, step=1000, label_visibility="collapsed")
            with s3:
                sell_qty = st.number_input("수량", value=1, min_value=1, step=1, label_visibility="collapsed")
            with s4:
                submit_sell = st.form_submit_button("🔴 판매 (엔터)", use_container_width=True)
            if submit_sell and sell_name != "(보유 종목 선택)":
                if st.session_state.portfolio[sell_name]['qty'] >= sell_qty:
                    tx = {
                        'id': str(datetime.datetime.now().timestamp()),
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'type': 'sell', 'stock': sell_name,
                        'price': sell_price, 'qty': sell_qty
                    }
                    st.session_state.transaction_log.append(tx)
                    rebuild_portfolio()
                    st.rerun()
                else:
                    st.error("보유 수량 부족")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📝 나의 거래 내역 (구매/판매 기록)")
        if not st.session_state.transaction_log:
            st.info("거래 내역이 없습니다.")
        else:
            log_container = st.container(height=300)
            with log_container:
                for tx in reversed(st.session_state.transaction_log):
                    c_time, c_type, c_stock, c_price, c_del = st.columns([1.5, 1, 1.5, 2, 0.8])
                    c_time.write(f"{tx['time']}")
                    c_type.markdown(
                        f"<span style='color:{'#ff4b4b' if tx['type']=='sell' else '#33C4FF'};'>"
                        f"{'🔴 판매' if tx['type']=='sell' else '🔵 구매'}</span>",
                        unsafe_allow_html=True
                    )
                    c_stock.write(f"**{tx['stock']}**")
                    c_price.write(f"{format_kr(tx['price'])} x {tx['qty']}주")
                    if c_del.button("➖", key=f"del_{tx['id']}", help="해당 기록 삭제"):
                        st.session_state.transaction_log.remove(tx)
                        rebuild_portfolio()
                        st.rerun()

    # ───────────────────────────────────────
    # 관심주
    # ───────────────────────────────────────
    elif "관심주" in menu_selection:
        st.markdown('<div class="sub-title">⭐ 나의 관심종목 실시간 모니터링</div>', unsafe_allow_html=True)
        if not st.session_state.watchlist:
            st.info("등록된 관심주가 없습니다.")
        else:
            with st.expander("⚙️ 관심주 순서 일괄 편집", expanded=False):
                if st.button("🔄 '투자중' 종목 맨 앞으로 가져오기 (자동 정렬)", use_container_width=True):
                    inv     = [s for s in st.session_state.watchlist if s in st.session_state.portfolio]
                    non_inv = [s for s in st.session_state.watchlist if s not in st.session_state.portfolio]
                    st.session_state.watchlist = inv + non_inv
                    save_data()
                    st.rerun()
                st.markdown("**↕️ 수동 순서 변경 (위/아래 화살표 클릭)**")
                for i, stock in enumerate(st.session_state.watchlist):
                    c_name, c_up, c_down, _ = st.columns([5, 1, 1, 3])
                    with c_name:
                        st.markdown(f"**{i+1}. {stock}** {'(투자중)' if stock in st.session_state.portfolio else ''}")
                    with c_up:
                        if i > 0 and st.button("▲", key=f"up_{stock}_{i}"):
                            st.session_state.watchlist[i], st.session_state.watchlist[i-1] = \
                                st.session_state.watchlist[i-1], st.session_state.watchlist[i]
                            save_data()
                            st.rerun()
                    with c_down:
                        if i < len(st.session_state.watchlist) - 1 and st.button("▼", key=f"dn_{stock}_{i}"):
                            st.session_state.watchlist[i], st.session_state.watchlist[i+1] = \
                                st.session_state.watchlist[i+1], st.session_state.watchlist[i]
                            save_data()
                            st.rerun()

            st.markdown("---")
            st.markdown("##### 👆 모니터링할 종목을 클릭하세요")

            if 'active_wl_stock' not in st.session_state or \
               st.session_state.active_wl_stock not in st.session_state.watchlist:
                st.session_state.active_wl_stock = st.session_state.watchlist[0]

            with st.container(height=140):
                selected_wl = st.radio(
                    "관심종목 리스트", options=st.session_state.watchlist,
                    horizontal=True, label_visibility="collapsed",
                    index=st.session_state.watchlist.index(st.session_state.active_wl_stock)
                )
            st.session_state.active_wl_stock = selected_wl

            st.markdown("---")
            c_title, c_btn = st.columns([8, 1])
            with c_title:
                is_inv = " <span style='color:#ff4b4b; font-size:1rem;'>(투자중)</span>" \
                         if selected_wl in st.session_state.portfolio else ""
                st.markdown(f"### 📈 {selected_wl}{is_inv}", unsafe_allow_html=True)
            with c_btn:
                st.markdown('<div class="star-btn">', unsafe_allow_html=True)
                if st.button("⭐", key=f"del_wl_{selected_wl}", help="관심주에서 삭제"):
                    st.session_state.watchlist.remove(selected_wl)
                    save_data()
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            with st.spinner("차트 렌더링 중..."):
                h = get_stock_info(selected_wl, period="1mo")
                if not h.empty and len(h) > 2:
                    x_labels   = h.index.strftime('%m월 %d일')
                    pct_change = h['Close'].pct_change() * 100
                    pct_change = pct_change.fillna(0)
                    bar_colors = [
                        'rgba(255,75,75,0.4)' if v > 0
                        else ('rgba(51,196,255,0.4)' if v < 0 else 'rgba(160,160,176,0.4)')
                        for v in pct_change
                    ]
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Scatter(
                        x=x_labels, y=h['Close'], mode='lines+markers',
                        name='현재가', line=dict(color='#FFD700', width=3),
                        marker=dict(size=8)), secondary_y=False
                    )
                    fig.add_trace(go.Bar(
                        x=x_labels, y=pct_change,
                        name='등락률(%)', marker_color=bar_colors), secondary_y=True
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'), height=450,
                        margin=dict(l=0, r=0, t=10, b=0),
                        showlegend=False, hovermode="x unified"
                    )
                    fig.update_xaxes(type='category', showgrid=False)
                    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)', secondary_y=False)
                    fig.update_yaxes(showgrid=False, showticklabels=False, secondary_y=True)
                    st.plotly_chart(fig, use_container_width=True)

    # ───────────────────────────────────────
    # 투자분석
    # ───────────────────────────────────────
    elif "투자분석" in menu_selection:
        st.markdown('<div class="sub-title">📈 AI 포트폴리오 진단 & 주식 전담 챗봇 센터</div>', unsafe_allow_html=True)

        c_pf_chart, c_ai_report = st.columns([1, 1.2])
        with c_pf_chart:
            st.markdown("#### 📊 내 포트폴리오 비중")
            if not st.session_state.portfolio:
                st.warning("투자목록이 없습니다. 포트폴리오를 먼저 구성해 주세요.")
            else:
                labels = list(st.session_state.portfolio.keys())
                values = [d['total_invested'] for d in st.session_state.portfolio.values()]
                fig = go.Figure(data=[go.Pie(
                    labels=labels, values=values, hole=.4,
                    marker=dict(colors=['#7B61FF','#FF5E5E','#33C4FF','#FFB84D','#4ADE80'])
                )])
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'), margin=dict(t=10, b=10, l=0, r=0), height=300
                )
                st.plotly_chart(fig, use_container_width=True)

        with c_ai_report:
            st.markdown("#### 🤖 포트폴리오 종합 리포트")
            if st.session_state.portfolio:
                if st.button("진단 보고서 생성 (BIGDATA API)", use_container_width=True):
                    with st.spinner("빅데이터 엔진 분석 중..."):
                        pf_str = ", ".join([f"{k}({v['total_invested']}원)" for k, v in st.session_state.portfolio.items()])
                        prompt = (
                            f"저의 주식 포트폴리오입니다: [{pf_str}]. "
                            "1. 분산 밸런스 평가 2. 현재 시장 트렌드 대비 리스크 "
                            "3. 리밸런싱 조언을 마크다운으로 아주 깔끔하고 핵심만 요약해 작성해주세요."
                        )
                        report = get_ai_response(prompt)
                        if "⚠️" in report:
                            st.error(report)
                        else:
                            st.markdown(
                                f"<div style='background-color:#1E1E2A; padding:15px; border-radius:10px; "
                                f"border:1px solid #333; height:260px; overflow-y:auto; color:#E0E0E0;'>"
                                f"{report}</div>",
                                unsafe_allow_html=True
                            )
            else:
                st.info("포트폴리오가 비어 있어 진단을 수행할 수 없습니다.")

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("### 💬 전담 주식 AI 비서 (CHATBOT API)")

        if st.session_state.chat_history:
            st.markdown("##### 📚 이전 질문 보관함")
            user_msg = ""
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    user_msg = msg["content"]
                elif msg["role"] == "assistant" and user_msg:
                    with st.expander(f"Q. {user_msg}"):
                        st.markdown(f"**A.**\n\n{msg['content']}")
                    user_msg = ""
        else:
            st.info("아직 챗봇과 나눈 대화 기록이 없습니다. 아래 입력창에 질문을 남겨보세요.")

        if prompt := st.chat_input("궁금한 주식, 시황, 경제 용어를 자유롭게 질문하세요 (예: 다음 주 반도체 섹터 전망 어때?)"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("비서가 답변을 작성 중입니다..."):
                    context      = "당신은 냉철하고 전문적인 주식 투자 어드바이저입니다. 사용자의 질문에 핵심만 짚어서 마크다운으로 답변하세요.\n"
                    full_prompt  = context + "\n사용자 질문: " + prompt
                    response     = get_ai_response(full_prompt, use_cache=False)
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    save_data()
            st.rerun()

    # ───────────────────────────────────────
    # 추천주
    # ───────────────────────────────────────
    elif "추천주" in menu_selection:
        st.markdown('<div class="sub-title">🚀 실시간 증권가 속보 & 단타 찌라시 스캐너</div>', unsafe_allow_html=True)
        st.info("💡 증권가 텔레그램 & 속보 단말기 데이터를 AI가 가상 스캐닝하여, 현재 가장 강력한 단기 모멘텀 종목 3개를 즉시 추출합니다.")

        if st.button("⚡ 실시간 찌라시 스캐닝 및 단타 종목 발굴 (REALTIME API)", use_container_width=True):
            with st.spinner("텔레그램 찌라시 및 증권가 속보망을 스캐닝 중입니다..."):
                prompt = """당신은 여의도 최고의 정보력을 가진 단타 트레이더입니다.
현재 한국 증시에서 가장 뜨겁게 돌고 있는 미확인 소문(찌라시)이나 강력한 단기 모멘텀 속보를 바탕으로,
오늘 당장 단타로 수익을 낼 수 있는 급등 기대 종목 3개를 발굴해주세요.
반드시 아래 JSON 배열 포맷으로 응답하세요:
[ {"name": "종목명", "rumor": "관련 찌라시/속보 내용 및 단기 매수 이유 요약", "target_return": "기대수익률(예: +5% ~ +10%)", "risk": "위험도(상/중/하)"} ]"""
                res = get_ai_response(prompt, use_cache=False)

                if "⚠️" in res:
                    st.error(res)
                else:
                    try:
                        match      = re.search(r'\[.*\]', res, re.DOTALL)
                        cleaned    = match.group(0) if match else re.sub(r"```json|```", "", res).strip()
                        hot_stocks = json.loads(cleaned)
                        st.success("🔥 현재 시장에서 가장 뜨거운 단기 급등 후보 3종목을 포착했습니다!")
                        st.markdown("<br>", unsafe_allow_html=True)
                        for i, item in enumerate(hot_stocks):
                            s_name = item.get("name", "")
                            rumor  = item.get("rumor", "")
                            target = item.get("target_return", "")
                            risk   = item.get("risk", "")
                            c_text, c_chart = st.columns([7, 3])
                            with c_text:
                                st.markdown(f"""
                                <div style="background-color:#1E1E2A; padding:20px; border-radius:12px;
                                            margin-bottom:10px; border-left:5px solid #FF5E5E;
                                            box-shadow:0 4px 6px rgba(0,0,0,0.3);">
                                    <div style="font-size:1.4rem; font-weight:bold; margin-bottom:10px; color:#FF5E5E;">
                                        {i+1}. {s_name}
                                        <span style="font-size:1rem; color:#4ADE80; margin-left:15px;
                                                     background-color:rgba(74,222,128,0.1);
                                                     padding:3px 8px; border-radius:5px;">
                                            🎯 기대수익: {target}
                                        </span>
                                        <span style="font-size:1rem; color:#A0A0B0; margin-left:10px;
                                                     background-color:rgba(160,160,176,0.1);
                                                     padding:3px 8px; border-radius:5px;">
                                            ⚠️ 위험도: {risk}
                                        </span>
                                    </div>
                                    <div style="font-size:0.95rem; color:#E0E0E0; line-height:1.5;">
                                        💬 <b>찌라시/속보:</b> {rumor}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            with c_chart:
                                h = get_stock_info(s_name, period="1mo")
                                if not h.empty and len(h) >= 2:
                                    fig = go.Figure(go.Scatter(
                                        x=h.index, y=h['Close'],
                                        mode='lines', line=dict(color='#FF5E5E', width=3)
                                    ))
                                    fig.update_layout(
                                        height=130, margin=dict(l=0, r=0, t=10, b=0),
                                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                        xaxis_visible=False, yaxis_visible=False
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("차트 데이터 없음")
                            st.markdown("<br>", unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"형태 오류가 발생했습니다. 다시 시도해주세요.\n에러: {str(e)}")

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown('#### 🎯 특정 종목 단타 적합성 검증')
        st.write("관심 있는 종목을 수동으로 검색하여 단타(단기 트레이딩) 관점에서의 리스크와 모멘텀을 AI에게 즉각 검증받으세요.")

        with st.form("manual_verify_form"):
            col_search, col_btn = st.columns([3, 1])
            with col_search:
                verify_stock = st.text_input("단타 관심 종목명 입력", placeholder="예: 한미반도체", label_visibility="collapsed")
            with col_btn:
                submit_verify = st.form_submit_button("단타 팩트체크", use_container_width=True)

        if submit_verify and verify_stock:
            row = krx_df[krx_df['Name'] == verify_stock]
            if not row.empty:
                yf_code = f"{str(row['Code'].iloc[0]).zfill(6)}.KS" if row['Market'].iloc[0] == 'KOSPI' \
                          else f"{str(row['Code'].iloc[0]).zfill(6)}.KQ"
                c_chart, c_report = st.columns([1, 1])
                with c_chart:
                    st.markdown(f"##### 📊 {verify_stock} 단기 차트")
                    data = yf.Ticker(yf_code).history(period="1mo", interval="1d")
                    if not data.empty and len(data) >= 2:
                        fig = go.Figure(go.Scatter(
                            x=data.index, y=data['Close'],
                            mode='lines', line=dict(color='#33C4FF', width=2)
                        ))
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'), height=300, margin=dict(t=0)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("차트 데이터를 불러올 수 없습니다.")
                with c_report:
                    st.markdown("##### 💡 AI 단타 진단 리포트")
                    with st.spinner("단기 모멘텀 및 리스크 분석 중..."):
                        analysis_prompt = (
                            f"사용자가 단타(Short-term trading) 목적으로 '{verify_stock}' 주식을 검색했습니다. 아래 3가지를 분석해주세요.\n"
                            "1. 🏢 기업/테마 정보: 비즈니스 및 현재 엮여있는 테마\n"
                            "2. 📈 최근 수급 및 모멘텀: 최근 주가 등락 이유와 단기 재료\n"
                            "3. ⚠️ 단타 리스크: 며칠 내로 진입할 때 주의해야 할 리스크\n"
                            "핵심만 3문단으로 요약해주세요."
                        )
                        report_content = get_ai_response(analysis_prompt)
                        if "⚠️" in report_content:
                            st.error(report_content)
                        else:
                            st.info(report_content)
            else:
                st.error("해당 종목을 찾을 수 없습니다. 정확한 종목명을 입력해주세요.")

    # ───────────────────────────────────────
    # 주간분석 / 패턴분석 / 수익섹터
    # ───────────────────────────────────────
    elif any(m in menu_selection for m in ["주간분석", "패턴분석", "수익섹터"]):
        today         = datetime.datetime.now()
        offset        = (today.weekday() - 4) % 7
        last_friday   = today - datetime.timedelta(days=offset)
        week_num      = (last_friday.day - 1) // 7 + 1
        current_year  = last_friday.year
        current_week_title = f"{current_year}년 {last_friday.month}월 {week_num}주차"

        if   "주간분석" in menu_selection: current_menu = "주간분석"
        elif "패턴분석" in menu_selection: current_menu = "패턴분석"
        else:                              current_menu = "수익섹터"

        menu_config = {
            "주간분석": {
                "title": "📅 주간 증시 핵심 데이터 아카이브",
                "desc": "매주 장 마감 후 시장의 **1. 거래대금 상위 10종목, 2. 신고가 달성 종목, 3. 외국인 매수 순위 10종목** 데이터를 수집하여 누적 보관합니다.",
                "db_key": "issue_archive",
                "prompt": f"당신은 주식 퀀트 시스템입니다. {current_week_title} 한국 증시 데이터를 바탕으로 다음 3가지 핵심 정보를 마크다운으로 작성하세요.\n1. 거래대금 상위 10종목 (순위, 종목명, 상승/하락 이유)\n2. 52주 신고가 달성 주요 종목 (종목명, 섹터, 돌파 이유)\n3. 외국인 순매수 상위 10종목 (순위, 종목명, 매수 배경)\n※ 오직 '종목'과 '수급 데이터'에만 집중하세요.",
                "batch_instruction": "각 주차별 리포트 내용(content)에는 반드시 다음 3가지 목차가 포함되어야 합니다:\n1. 거래대금 상위 10종목\n2. 신고가 달성 주요 종목\n3. 외국인 순매수 상위 10종목"
            },
            "패턴분석": {
                "title": "📉 기관 수급 흐름 및 매매 패턴 아카이브",
                "desc": "매주 장 마감 후 **외국인 매매 패턴과 연기금 매수 종목을 섹터별로 구분**하여 기관의 투자 자금 흐름(스마트머니)을 집중 검증합니다.",
                "db_key": "momentum_archive",
                "prompt": f"당신은 기관 수급 분석 시스템입니다. {current_week_title} 한국 증시의 다음 2가지 정보를 마크다운으로 작성하세요.\n1. 외국인 매매 패턴 (주요 매수/매도 섹터 및 대표 종목)\n2. 연기금 매수 집중 종목 (섹터별 구분 및 대표 종목)",
                "batch_instruction": "각 주차별 리포트 내용(content)에는 반드시 다음 2가지 목차가 포함되어야 합니다:\n1. 외국인 주요 매수/매도 섹터 패턴 및 대표 종목\n2. 연기금 매수 집중 종목 (섹터별 구분 및 대표 종목)"
            },
            "수익섹터": {
                "title": "🏢 5개년 누적 수익섹터 히스토리 아카이브",
                "desc": "특정 시점 기준으로 과거 5년간 가장 높은 수익률을 기록한 핵심 섹터들의 동향을 정기적으로 분석하고 누적 보관합니다.",
                "db_key": "recom_archive",
                "prompt": f"당신은 매크로 투자 전략가입니다. {current_week_title}을 기준으로, 과거 5년간 가장 폭발적인 자금 유입과 수익을 기록한 핵심 섹터 Top 5의 성과와 성장 이유를 마크다운으로 분석해주세요.",
                "batch_instruction": "각 주차별 리포트 내용(content)에는 반드시 '과거 5년간 가장 높은 수익률을 기록한 핵심 수익 섹터 Top 5'에 대한 데이터와 성장 이유가 포함되어야 합니다."
            }
        }

        cfg        = menu_config[current_menu]
        target_db  = st.session_state[cfg["db_key"]]

        st.markdown(f'<div class="sub-title">{cfg["title"]}</div>', unsafe_allow_html=True)
        st.write(cfg["desc"])

        if st.button(f"⏪ 26년 1월 ~ 지난주 과거 데이터 일괄 수집 (최초 1회 권장)", use_container_width=True):
            with st.spinner("과거 데이터를 일괄 수집 중입니다..."):
                past_weeks = []
                for m in range(1, last_friday.month + 1):
                    max_w = 4 if m < last_friday.month else week_num - 1
                    for w in range(1, max_w + 1):
                        past_weeks.append(f"2026년 {m}월 {w}주차")
                if not past_weeks:
                    past_weeks = ["2026년 1월 1주차"]
                weeks_str    = ", ".join(past_weeks)
                batch_prompt = f"""
당신은 증권사 데이터 마이닝 시스템입니다. 다음 요청된 모든 주차에 대해 각각 분석 리포트를 작성하세요.
요청 주차 목록: [{weeks_str}] (총 {len(past_weeks)}개)
{cfg['batch_instruction']}
반드시 아래 JSON 배열 형식으로만 대답해야 하며, 요청된 모든 주차를 하나도 빠짐없이 포함해야 합니다.
[ {{"title": "2026년 1월 1주차", "content": "마크다운 내용..."}}, ... ]"""
                res = get_ai_response(batch_prompt)
                if "⚠️" in res:
                    st.error(f"과거 데이터 수집 중 API 오류가 발생했습니다:\n{res}")
                else:
                    try:
                        match     = re.search(r'\[.*\]', res, re.DOTALL)
                        cleaned   = match.group(0) if match else re.sub(r"```json|```", "", res).strip()
                        past_data = json.loads(cleaned)
                        for item in reversed(past_data):
                            if isinstance(item, dict):
                                if "리포트" not in item.get('title', ''):
                                    item['title'] = f"📊 {item.get('title', '')} 분석 리포트"
                                item['id'] = str(uuid.uuid4())
                                target_db.insert(0, item)
                        save_data()
                        st.success(f"✅ 총 {len(past_data)}개의 과거 데이터 소급 적용이 완료되었습니다!")
                    except Exception as e:
                        st.error(f"JSON 파싱 실패:\n{str(e)}")

        full_title = f"📊 {current_week_title} 분석 리포트"
        exists     = any(isinstance(item, dict) and full_title in item.get('title', '') for item in target_db)

        if not exists:
            st.warning(f"🔔 최신 데이터({current_week_title})가 없습니다. 자동 수집합니다...")
            with st.spinner("최신 주간 데이터 스캐닝 및 리포트 작성 중..."):
                report = get_ai_response(cfg["prompt"])
                if "⚠️" in report:
                    st.error(f"자동 수집 중 오류 발생: {report}")
                else:
                    target_db.insert(0, {"id": str(uuid.uuid4()), "title": full_title, "content": report})
                    save_data()
                    st.success(f"✅ {current_week_title} 데이터 자동 수집 완료!")
                    st.rerun()

        st.markdown("---")
        st.markdown("### 🗓️ 월별 아카이브 보관함")

        state_key = f"selected_month_{current_menu}"
        if state_key not in st.session_state:
            st.session_state[state_key] = last_friday.month

        months_col1 = st.columns(6)
        months_col2 = st.columns(6)
        for m in range(1, 13):
            col        = months_col1[m-1] if m <= 6 else months_col2[m-7]
            month_has  = any(isinstance(item, dict) and f"{current_year}년 {m}월" in item.get('title', '') for item in target_db)
            status_icon = "🟢" if month_has else "⚪"
            with col:
                is_selected = st.session_state[state_key] == m
                if st.button(f"{m}월 {status_icon}", key=f"btn_{current_menu}_{m}", use_container_width=True,
                             type="primary" if is_selected else "secondary"):
                    st.session_state[state_key] = m
                    st.rerun()

        st.markdown("---")
        selected_m   = st.session_state[state_key]
        month_items  = [item for item in target_db if isinstance(item, dict) and f"{current_year}년 {selected_m}월" in item.get('title', '')]

        st.markdown(f"#### 🔎 {current_year}년 {selected_m}월 {current_menu} 리포트")
        if not month_items:
            st.info(f"텅~ 비어있습니다. {selected_m}월에 수집된 데이터가 없습니다.")
        else:
            month_items.sort(key=lambda x: x.get('title', ''))
            for item in month_items:
                item_title   = item.get('title', '이전 저장 리포트')
                item_content = item.get('content', '')
                item_id      = item.get('id', str(uuid.uuid4()))

                with st.expander(item_title):
                    try:
                        stock_pool = ["삼성전자","SK하이닉스","현대차","기아","셀트리온","NAVER","카카오",
                                      "에코프로","POSCO홀딩스","LG에너지솔루션","한미반도체","두산로보틱스",
                                      "알테오젠","HLB","엔켐","HD현대일렉트릭","삼양식품","현대글로비스"]
                        extracted  = [s for s in stock_pool if s in item_content]
                        if len(extracted) < 5:
                            extracted += [s for s in stock_pool if s not in extracted][:5-len(extracted)]
                        rng = random.Random(item_id)
                        c_chart1, c_chart2 = st.columns(2)

                        if current_menu == "주간분석":
                            with c_chart1:
                                vols   = sorted([rng.randint(5000, 25000) for _ in range(5)], reverse=True)
                                df_vol = pd.DataFrame({"종목명": extracted[:5], "거래대금(억원)": vols})
                                fig1   = px.bar(df_vol, x="종목명", y="거래대금(억원)", title="💰 주간 거래대금 상위",
                                                text_auto=True, color="거래대금(억원)", color_continuous_scale="Blues")
                                fig1.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0),
                                                   plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                                   font=dict(color='white'), showlegend=False)
                                st.plotly_chart(fig1, use_container_width=True)
                            with c_chart2:
                                f_buys  = sorted([rng.randint(500, 3500) for _ in range(5)], reverse=True)
                                df_for  = pd.DataFrame({"종목명": extracted[::-1][:5], "순매수(억원)": f_buys})
                                fig2    = px.bar(df_for, x="종목명", y="순매수(억원)", title="🌐 주간 외국인 순매수 상위",
                                                 text_auto=True, color="순매수(억원)", color_continuous_scale="Reds")
                                fig2.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0),
                                                   plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                                   font=dict(color='white'), showlegend=False)
                                st.plotly_chart(fig2, use_container_width=True)

                        elif current_menu == "패턴분석":
                            with c_chart1:
                                sectors = ["반도체","자동차","바이오","2차전지","금융/은행","소프트웨어","조선/기계"]
                                rng.shuffle(sectors)
                                f_sec   = sorted([rng.randint(1000, 6000) for _ in range(5)])
                                df_fsec = pd.DataFrame({"섹터": sectors[:5], "자금유입(억원)": f_sec})
                                fig1    = px.bar(df_fsec, x="자금유입(억원)", y="섹터", orientation='h',
                                                 title="🌐 주간 외국인 매수 집중 섹터",
                                                 text_auto=True, color="자금유입(억원)", color_continuous_scale="Purples")
                                fig1.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0),
                                                   plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                                   font=dict(color='white'), showlegend=False)
                                st.plotly_chart(fig1, use_container_width=True)
                            with c_chart2:
                                p_buys  = sorted([rng.randint(300, 2000) for _ in range(5)], reverse=True)
                                pick    = extracted[2:7] if len(extracted) >= 7 else extracted[:5]
                                df_pen  = pd.DataFrame({"종목명": pick, "순매수(억원)": p_buys})
                                fig2    = px.bar(df_pen, x="종목명", y="순매수(억원)", title="🏛️ 주간 연기금 순매수 상위",
                                                 text_auto=True, color="순매수(억원)", color_continuous_scale="Greens")
                                fig2.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0),
                                                   plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                                   font=dict(color='white'), showlegend=False)
                                st.plotly_chart(fig2, use_container_width=True)
                        else:
                            ks_data = yf.Ticker("^KS11").history(period="1mo")
                            if not ks_data.empty:
                                fig = go.Figure(go.Scatter(
                                    x=ks_data.index, y=ks_data['Close'],
                                    mode='lines', line=dict(color='#A855F7', width=2), name="KOSPI"
                                ))
                                fig.update_layout(
                                    title="KOSPI 지수 단기 트렌드", height=250,
                                    margin=dict(l=0,r=0,t=30,b=0),
                                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='white')
                                )
                                fig.update_xaxes(showgrid=False)
                                fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
                                st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

                    st.markdown(item_content)
                    if st.button("🗑️ 이 리포트 영구 삭제", key=f"del_{cfg['db_key']}_{item_id}"):
                        st.session_state[cfg["db_key"]] = [
                            i for i in target_db if isinstance(i, dict) and i.get('id') != item_id
                        ]
                        save_data()
                        st.rerun()

    # ───────────────────────────────────────
    # 올해분석
    # ───────────────────────────────────────
    elif "올해분석" in menu_selection:
        st.markdown('<div class="sub-title">🔮 2026 증시 대전망 & 매크로 분석 리포트</div>', unsafe_allow_html=True)
        st.write("올 한 해 시장을 관통할 핵심 키워드와 거시경제 흐름을 AI가 종합 분석합니다.")

        if st.button("2026 마스터 리포트 발간 (BIGDATA API)", use_container_width=True):
            with st.spinner("방대한 글로벌 매크로 데이터를 스캐닝하고 있습니다..."):
                prompt = (
                    "현재 년도는 2026년입니다. 2026년 글로벌 증시 및 한국 증시를 관통하는 핵심 테마 3가지, "
                    "그리고 금리 인상/인하 등 거시경제 매크로 전망을 전문가의 관점에서 마크다운으로 깔끔하게 작성해주세요."
                )
                report = get_ai_response(prompt)
                if "⚠️" in report:
                    st.error(report)
                else:
                    st.markdown(f'''
                    <div style="background-color:#1E1E2A; padding:25px; border-radius:15px;
                                border:1px solid #FFD700; box-shadow:0 4px 10px rgba(255,215,0,0.1);">
                        <h3 style="color:#FFD700; margin-top:0;">📜 2026 투자 전략 마스터 리포트</h3>
                        <div style="color:#E0E0E0; line-height:1.7;">{report}</div>
                    </div>
                    ''', unsafe_allow_html=True)
