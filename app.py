import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
import requests
import base64
import gzip
import hashlib
from datetime import datetime, timedelta
import jdatetime

from styles import FONTS, inject_login, inject_app

# ================== ثابت‌های پایه ==================
DEFAULT_NAV_ICONS = {
    "overview": {"icon": "fa-chart-pie", "color": "#3b82f6"},
    "journal": {"icon": "fa-circle-plus", "color": "#10b981"},
    "usd": {"icon": "fa-dollar-sign", "color": "#f59e0b"},
    "gold": {"icon": "fa-coins", "color": "#eab308"},
    "synthetic": {"icon": "fa-arrow-right-arrow-left", "color": "#8b5cf6"},
    "monthly": {"icon": "fa-calendar-days", "color": "#ec4899"},
    "settings": {"icon": "fa-gear", "color": "#6b7280"},
}
NAV_LABELS = {
    "overview": "نمای کلی", "journal": "افزودن دارایی", "usd": "دلار",
    "gold": "صندوق‌های طلا", "synthetic": "جفت مصنوعی",
    "monthly": "بازده ماهانه", "settings": "تنظیمات",
}
NAV_EMOJI = {
    "overview": "📊", "journal": "➕", "usd": "💵", "gold": "🥇",
    "synthetic": "🔀", "monthly": "📅", "settings": "⚙️",
}

FALLBACK_ICONS = [
    {"class": "fa-folder", "label": "Folder"}, {"class": "fa-coins", "label": "Coins"},
    {"class": "fa-wallet", "label": "Wallet"}, {"class": "fa-money-bill-wave", "label": "Money"},
    {"class": "fa-dollar-sign", "label": "Dollar"}, {"class": "fa-building-columns", "label": "Bank"},
    {"class": "fa-piggy-bank", "label": "Piggy Bank"}, {"class": "fa-vault", "label": "Vault"},
    {"class": "fa-gem", "label": "Gem"}, {"class": "fa-crown", "label": "Crown"},
    {"class": "fa-house", "label": "House"}, {"class": "fa-building", "label": "Building"},
    {"class": "fa-car", "label": "Car"}, {"class": "fa-chart-line", "label": "Chart Line"},
    {"class": "fa-chart-pie", "label": "Chart Pie"}, {"class": "fa-bitcoin-sign", "label": "Bitcoin"},
    {"class": "fa-ethereum", "label": "Ethereum"}, {"class": "fa-landmark", "label": "Landmark"},
    {"class": "fa-industry", "label": "Industry"}, {"class": "fa-seedling", "label": "Seedling"},
    {"class": "fa-briefcase", "label": "Briefcase"}, {"class": "fa-store", "label": "Store"},
    {"class": "fa-sack-dollar", "label": "Sack Dollar"}, {"class": "fa-receipt", "label": "Receipt"},
    {"class": "fa-tag", "label": "Tag"}, {"class": "fa-fire", "label": "Fire"},
    {"class": "fa-bolt", "label": "Bolt"}, {"class": "fa-box", "label": "Box"},
    {"class": "fa-gear", "label": "Gear"}, {"class": "fa-circle-plus", "label": "Circle Plus"},
    {"class": "fa-arrow-right-arrow-left", "label": "Exchange"},
]

CATEGORY_KEYWORDS = {
    "money": ["coin", "dollar", "money", "wallet", "bank", "cash", "currency", "credit-card", "payment", "receipt", "invoice", "sack", "piggy", "vault", "tax", "donate", "hand-holding", "tip", "price-tag", "bitcoin", "ethereum", "euro", "sterling", "yen", "rupee", "ruble", "won", "lira", "peso", "shekel", "tenge", "exchange", "money-bill", "money-check", "arrow-right-arrow-left"],
    "chart": ["chart", "graph", "trend", "analytics", "presentation-chart", "arrow-trend", "magnifying-glass-chart", "square-poll", "ranking", "signal", "wifi", "spinner", "percent"],
    "gems": ["gem", "crown", "diamond", "gift", "award", "medal", "star", "trophy", "ribbon", "certificate"],
    "building": ["building", "house", "home", "office", "factory", "industry", "warehouse", "store", "shop", "landmark", "church", "mosque", "hotel", "school", "hospital", "motel", "tent", "campground"],
    "transport": ["car", "truck", "plane", "ship", "train", "bus", "bike", "motorcycle", "taxi", "rocket", "helicopter", "boat", "tram", "subway", "van", "tractor", "trailer", "wheelchair"],
    "goods": ["box", "package", "shipping", "cart", "basket", "bag-shopping", "boxes", "cubes", "cube"],
    "business": ["briefcase", "handshake", "user-tie", "file-invoice", "file-contract", "clipboard-check", "check-double"],
    "file": ["folder", "file", "save", "download", "upload", "disk", "document", "paper", "clipboard", "notebook", "book", "bookmark", "newspaper", "scroll", "envelope", "mail"],
    "user": ["user", "person", "people", "group", "team", "users"],
    "system": ["gear", "cog", "tool", "wrench", "hammer", "screwdriver", "key", "lock", "shield", "bell", "power-off", "right-from-bracket", "arrow-right-from-bracket", "ellipsis", "bars"],
    "media": ["camera", "photo", "image", "video", "music", "headphone", "play", "pause", "stop", "record", "microphone", "film", "compact-disc", "volume", "speaker"],
    "symbol": ["circle-check", "circle-xmark", "circle-plus", "circle-minus", "circle", "square", "triangle", "heart", "plus", "minus", "equals", "question", "info", "exclamation", "ban", "check"],
    "time": ["clock", "calendar", "time", "hourglass", "stopwatch", "timer", "watch"],
    "nature": ["fire", "bolt", "sun", "leaf", "tree", "seedling", "water", "droplet", "wind", "snow", "cloud", "moon", "snowflake", "mountain"],
}

CATEGORY_LABELS = {
    "money": "💰 پول و ارز", "chart": "📊 سرمایه و نمودار", "gems": "🥇 طلا و جواهر",
    "building": "🏢 ملک و ساختمان", "transport": "🚗 حمل و نقل", "goods": "📦 کالا",
    "business": "💼 کسب و کار", "file": "📁 فایل و سند", "user": "👤 کاربر",
    "system": "⚙️ تنظیمات", "media": "🎬 رسانه", "symbol": "🔷 نماد",
    "time": "⏰ زمان", "nature": "🌿 طبیعت", "other": "📌 سایر",
}

def categorize_icon(icon_class, label):
    text = f"{icon_class} {label}".lower()
    cats = []
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                cats.append(cat)
                break
    return cats or ["other"]

# ================== تنظیمات صفحه ==================
st.set_page_config(page_title="داشبورد مالی", layout="wide", initial_sidebar_state="expanded")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
APP_PASSWORD = st.secrets.get("APP_PASSWORD") or "S@mnet11970"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "data.json"
GITHUB_BRANCH = "main"

def get_auth_token():
    return hashlib.sha256((APP_PASSWORD + "_salt_v2_2024").encode()).hexdigest()

AUTH_TOKEN = get_auth_token()

# ================== آیکون‌ها ==================
@st.cache_data(ttl=86400, show_spinner=False)
def load_fa_icons(cache_v="v7"):
    try:
        r = requests.get("https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/metadata/icons.json", timeout=15)
        if r.status_code == 200:
            meta = r.json()
            icons = []
            for name, info in meta.items():
                if "solid" not in info.get("free", []):
                    continue
                label = info.get("label", name)
                icons.append({"class": f"fa-{name}", "label": label,
                              "categories": categorize_icon(f"fa-{name}", label)})
            if icons:
                return sorted(icons, key=lambda x: x["label"].lower())
    except Exception:
        pass
    return [{"class": ic["class"], "label": ic["label"],
             "categories": categorize_icon(ic["class"], ic["label"])} for ic in FALLBACK_ICONS]

def icon_emoji(fa_class):
    _EMOJI = {
        "fa-folder": "📁", "fa-coins": "🪙", "fa-wallet": "👛", "fa-dollar-sign": "💲",
        "fa-building-columns": "🏦", "fa-gem": "💎", "fa-crown": "👑", "fa-house": "🏠",
        "fa-car": "🚗", "fa-chart-line": "📈", "fa-chart-pie": "📊", "fa-bitcoin-sign": "₿",
        "fa-briefcase": "💼", "fa-store": "🏪", "fa-sack-dollar": "💰", "fa-fire": "🔥",
        "fa-bolt": "⚡", "fa-box": "📦", "fa-gear": "⚙️", "fa-circle-plus": "➕",
        "fa-arrow-right-arrow-left": "🔀",
    }
    return _EMOJI.get(fa_class, "📁")

# ================== توابع تاریخ ==================
def today_jalali_str():
    return jdatetime.date.today().strftime("%Y/%m/%d")

def iso_to_jalali(iso_str, with_time=True):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        j = jdatetime.datetime.fromgregorian(datetime=dt)
        return j.strftime("%Y/%m/%d - %H:%M") if with_time else j.strftime("%Y/%m/%d")
    except Exception:
        return "—"

def parse_jalali(s):
    try:
        s = s.strip().replace("-", "/").replace(".", "/")
        parts = s.split("/")
        if len(parts) != 3: return None
        y, m, d = map(int, parts)
        return jdatetime.date(y, m, d)
    except Exception:
        return None

def jalali_to_gregorian_iso(jdate, time_str="00:00"):
    g = jdate.togregorian()
    return f"{g.strftime('%Y-%m-%d')}T{time_str}:00"

def fmt_num(x):
    try:
        f = float(x)
        return f"{int(f):,}" if f == int(f) else f"{f:,.2f}"
    except Exception:
        return str(x)

def _compact_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def _decompress_if_needed(raw_bytes):
    if len(raw_bytes) >= 2 and raw_bytes[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw_bytes)
        except Exception:
            pass
    return raw_bytes

def _short_id():
    return str(int(datetime.now().timestamp() * 1000))

def _rate_at(data, date_str):
    """آخرین نرخ دلار ثبت‌شده تا تاریخ مشخص (شامل همان روز)."""
    rate = None
    for item in sorted(data.get("usd_rates", []), key=lambda row: row.get("created_at", "")):
        if item.get("created_at", "")[:10] <= date_str:
            try:
                value = float(item.get("rate", 0) or 0)
                if value > 0:
                    rate = value
            except (TypeError, ValueError):
                continue
        else:
            break
    return rate

def _apply_chart_style(fig, dark, height=360):
    fig.update_layout(
        height=height,
        font=dict(family="Vazirmatn, Tahoma", size=13,
                  color="#e6edf3" if dark else "#1f2937"),
        paper_bgcolor="rgba(0,0,0,0)" if dark else "white",
        plot_bgcolor="rgba(0,0,0,0)" if dark else "white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25,
                    xanchor="center", x=0.5),
        margin=dict(t=30, b=20, l=10, r=10),
        hovermode="x unified",
    )
    return fig

def _cleanup_synthetic_pairs(data, removed_instrument_ids):
    """حذف جفت‌های مصنوعی که به ابزارهای حذف‌شده ارجاع می‌دهند."""
    if not data.get("synthetic_pairs"):
        return 0
    before = len(data["synthetic_pairs"])
    data["synthetic_pairs"] = [
        p for p in data["synthetic_pairs"]
        if p.get("left") not in removed_instrument_ids
        and p.get("right") not in removed_instrument_ids
    ]
    return before - len(data["synthetic_pairs"])

# ================== احراز هویت ==================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    qp_auth = st.query_params.get("auth")
    if qp_auth and qp_auth == AUTH_TOKEN:
        st.session_state.authenticated = True

if not st.session_state.authenticated:
    inject_login()
    st.markdown("<div style='height: 6vh;'></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center; padding: 24px 0 16px 0; direction: rtl;">
            <div style="font-size: 3.2rem; line-height: 1; margin-bottom: 8px;">🔐</div>
            <h1 style="margin: 0; color: #1e40af;">داشبورد مالی</h1>
            <p style="color: #6b7280; margin-top: 8px;">لطفاً رمز عبور را وارد کنید</p>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            with st.form("login_form"):
                password = st.text_input("رمز", type="password", placeholder="••••••••", label_visibility="collapsed")
                if st.form_submit_button("🚪 ورود", use_container_width=True):
                    if password == APP_PASSWORD:
                        st.session_state.authenticated = True
                        st.query_params["auth"] = AUTH_TOKEN
                        st.rerun()
                    else:
                        st.error("❌ رمز عبور اشتباه است.")
    st.stop()

# ================== GitHub API ==================
def github_headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

@st.cache_data(ttl=60, show_spinner=False)
def check_github_status(token, repo):
    if not token and not repo: return "no_config", "تنظیم نشده"
    if not token: return "no_token", "توکن ندارد"
    if not repo: return "no_repo", "مخزن ندارد"
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}",
                         headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, timeout=8)
        if r.status_code == 200: return "ok", f"متصل به {repo}"
        if r.status_code == 401: return "error", "توکن نامعتبر (401)"
        if r.status_code == 404: return "error", "مخزن یافت نشد (404)"
        return "error", f"HTTP {r.status_code}"
    except Exception as e:
        return "error", f"خطای شبکه: {str(e)[:40]}"

def load_local_file():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                raw = f.read()
            decompressed = _decompress_if_needed(raw)
            return json.loads(decompressed.decode("utf-8"))
    except Exception:
        pass
    return None

def save_local_file(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(_compact_json(data))
        return True
    except Exception:
        return False

def load_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO: return None
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(api_url, headers=github_headers(), timeout=20)
        if r.status_code != 200: return None
        info = r.json()
        content_b64 = info.get("content", "")
        if not content_b64:
            raw_url = info.get("download_url") or f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
            raw_resp = requests.get(raw_url, timeout=30)
            if raw_resp.status_code != 200: return None
            content_bytes = raw_resp.content
        else:
            content_bytes = base64.b64decode(content_b64)
        decompressed = _decompress_if_needed(content_bytes)
        return json.loads(decompressed.decode("utf-8"))
    except Exception:
        return None

def save_github_file(data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False, "GitHub تنظیم نشده"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    sha = None
    try:
        r = requests.get(url, headers=github_headers(), timeout=15)
        if r.status_code == 200: sha = r.json()["sha"]
        elif r.status_code == 401: return False, "توکن نامعتبر (401)"
    except Exception as e:
        return False, f"خطای شبکه: {str(e)[:50]}"
    raw = _compact_json(data).encode("utf-8")
    compressed = gzip.compress(raw, mtime=0)
    encoded = base64.b64encode(compressed).decode()
    payload = {
        "message": f"update {today_jalali_str()} {datetime.now().strftime('%H:%M')} ({len(compressed):,}B gz)",
        "content": encoded, "branch": GITHUB_BRANCH,
    }
    if sha: payload["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=payload, timeout=30)
        if r.status_code in (200, 201): return True, ""
        if r.status_code == 401: return False, "توکن نامعتبر (401)"
        if r.status_code == 403: return False, "دسترسی write ندارد (403)"
        if r.status_code == 404: return False, "مخزن یافت نشد (404)"
        if r.status_code == 409: return False, "تضاد SHA (409)"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"خطای شبکه: {str(e)[:50]}"

def verify_github_save(expected_data):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False, "GitHub تنظیم نشده", None
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?ref={GITHUB_BRANCH}"
    try:
        r = requests.get(api_url, headers=github_headers(), timeout=20)
        if r.status_code != 200: return False, f"HTTP {r.status_code}", None
        info = r.json()
        sha = info.get("sha", "")[:8]
        size_bytes = info.get("size", 0)
        content_b64 = info.get("content", "")
        if not content_b64:
            raw_url = info.get("download_url") or f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
            raw_resp = requests.get(raw_url, timeout=30)
            if raw_resp.status_code != 200: return False, "خواندن ناموفق", sha
            content_bytes = raw_resp.content
        else:
            content_bytes = base64.b64decode(content_b64)
        decompressed = _decompress_if_needed(content_bytes)
        gh_data = json.loads(decompressed.decode("utf-8"))
        if gh_data.get("last_saved") != expected_data.get("last_saved"):
            return False, "timestamp متفاوت", sha
        kind = "gzip" if content_bytes[:2] == b"\x1f\x8b" else "plain"
        return True, f"تأیید شد — {size_bytes:,}B ({kind})", sha
    except Exception as e:
        return False, str(e)[:50], None

# ================== مهاجرت ==================
def migrate_data(data):
    if not isinstance(data, dict) or not data:
        return {"assets": [], "usd_rates": [], "gold_funds": [], "synthetic_pairs": [], "settings": {
            "font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(),
            "custom_fonts": {}, "dark_mode": False}}
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list):
        old = data.get("usd_rate")
        data["usd_rates"] = []
        if old:
            data["usd_rates"].append({"id": _short_id(), "rate": old, "note": "منتقل‌شده",
                                     "created_at": datetime.now().isoformat(),
                                     "created_at_jalali": today_jalali_str()})
        data.pop("usd_rate", None)
    if "journals" in data and isinstance(data.get("journals"), list):
        if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
        for j in data.get("journals", []):
            aid = j.get("id") or _short_id()
            ciso = j.get("created_at_gregorian") or j.get("created_at") or datetime.now().isoformat()
            cjal = j.get("created_at_jalali") or iso_to_jalali(ciso, with_time=False)
            data["assets"].append({
                "id": aid, "name": j.get("asset_name", "بدون نام"), "icon": "fa-folder",
                "color": "#3b82f6", "overview_emoji": "", "currency": j.get("currency", "IRR"),
                "created_at_gregorian": ciso, "created_at_jalali": cjal,
                "records": [{"id": aid + "_r", "date_gregorian": ciso, "date_jalali": cjal,
                            "quantity": j.get("amount", 0), "unit_price": 1, "note": "منتقل‌شده"}]})
        data.pop("journals", None)
    if "assets" not in data or not isinstance(data.get("assets"), list): data["assets"] = []
    if "usd_rates" not in data or not isinstance(data.get("usd_rates"), list): data["usd_rates"] = []
    if "gold_funds" not in data or not isinstance(data.get("gold_funds"), list): data["gold_funds"] = []
    if "synthetic_pairs" not in data or not isinstance(data.get("synthetic_pairs"), list):
        data["synthetic_pairs"] = []
    if "settings" not in data or not isinstance(data.get("settings"), dict):
        data["settings"] = {"font": "vazirmatn", "nav_icons": DEFAULT_NAV_ICONS.copy(),
                            "custom_fonts": {}, "dark_mode": False}
    data["settings"].setdefault("font", "vazirmatn")
    data["settings"].setdefault("dark_mode", False)
    if "nav_icons" not in data["settings"]: data["settings"]["nav_icons"] = DEFAULT_NAV_ICONS.copy()
    for k, v in DEFAULT_NAV_ICONS.items(): data["settings"]["nav_icons"].setdefault(k, v.copy())
    if "custom_fonts" not in data["settings"]: data["settings"]["custom_fonts"] = {}
    seen = set(); unique = []
    for a in data["assets"]:
        if a.get("id") and a["id"] not in seen:
            seen.add(a["id"]); unique.append(a)
    data["assets"] = unique
    for a in data["assets"]:
        if not isinstance(a.get("icon"), str) or not a["icon"].startswith("fa-"): a["icon"] = "fa-folder"
        a.setdefault("color", "#3b82f6"); a.setdefault("overview_emoji", "")
    seen_g = set(); unique_g = []
    for gf in data["gold_funds"]:
        if gf.get("id") and gf["id"] not in seen_g:
            seen_g.add(gf["id"]); unique_g.append(gf)
    data["gold_funds"] = unique_g
    # پاکسازی جفت‌های مصنوعی که منابعشان دیگر وجود ندارد
    valid_ids = {f"asset:{a['id']}" for a in data["assets"]}
    valid_ids |= {f"gold:{g['id']}" for g in data["gold_funds"]}
    if data.get("usd_rates"):
        valid_ids.add("usd")
    data["synthetic_pairs"] = [
        p for p in data["synthetic_pairs"]
        if p.get("left") in valid_ids and p.get("right") in valid_ids
    ]
    return data

def load_all():
    local = load_local_file()
    gh = load_github_file()
    l_has = local and (local.get("assets") or local.get("usd_rates") or local.get("gold_funds"))
    g_has = gh and (gh.get("assets") or gh.get("usd_rates") or gh.get("gold_funds"))
    if l_has and g_has:
        l_saved = local.get("last_saved", ""); g_saved = gh.get("last_saved", "")
        chosen = (local if l_saved > g_saved else gh) if (l_saved and g_saved) else gh
        save_local_file(chosen); return migrate_data(chosen)
    if g_has: save_local_file(gh); return migrate_data(gh)
    if l_has: return migrate_data(local)
    return migrate_data({})

def save_all(data, verify=True):
    data["last_saved"] = datetime.now().isoformat()
    data["last_saved_jalali"] = jdatetime.datetime.fromgregorian(datetime=datetime.now()).strftime("%Y/%m/%d - %H:%M")
    local_ok = save_local_file(data)
    gh_ok, gh_err = save_github_file(data)
    if gh_ok:
        if verify:
            v_ok, v_msg, _ = verify_github_save(data)
            if v_ok: st.toast("✅ ذخیره و تأیید شد", icon="✅"); return True
            st.warning(f"⚠️ ذخیره شد ولی تأیید ناقص: {v_msg}"); return False
        st.toast("✅ ذخیره شد"); return True
    else:
        if local_ok:
            st.error(f"❌ **ذخیره GitHub ناموفق!** {gh_err}")
            st.warning("⚠️ فقط در حافظه موقت — با ری‌استارت از دست می‌رود!")
        else:
            st.error(f"❌ **هیچ جا ذخیره نشد!** {gh_err}")
        return False

# ================== توابع کمکی ==================
def get_settings(data):
    s = data.get("settings") or {}
    return {"font": s.get("font", "vazirmatn"),
            "nav_icons": s.get("nav_icons", DEFAULT_NAV_ICONS),
            "custom_fonts": s.get("custom_fonts", {}) or {},
            "dark_mode": bool(s.get("dark_mode", False))}

def get_all_fonts(data):
    fonts = {}
    for k, (name, url) in FONTS.items(): fonts[k] = {"name": name, "family": name, "builtin": True}
    custom = (data.get("settings") or {}).get("custom_fonts", {}) or {}
    for k, info in custom.items(): fonts[k] = {"name": info.get("display_name", k), "family": k, "builtin": False}
    return fonts

def asset_icon(asset):
    ic = asset.get("icon", "fa-folder")
    return ic if isinstance(ic, str) and ic.startswith("fa-") else "fa-folder"

def asset_color(asset): return asset.get("color", "#3b82f6")

def asset_overview_emoji(asset):
    custom = (asset.get("overview_emoji") or "").strip()
    return custom if custom else icon_emoji(asset_icon(asset))

def get_current_usd_rate(data):
    rates = data.get("usd_rates", [])
    if not rates: return None, None
    latest = max(rates, key=lambda x: x.get("created_at", ""))
    return latest["rate"], latest.get("created_at_jalali", "—")

def latest_record(asset):
    records = asset.get("records", [])
    if not records: return None
    return max(records, key=lambda r: (r.get("date_gregorian", ""), r.get("id", "")))

def compute_asset_value(asset, usd_rate):
    rec = latest_record(asset)
    if not rec: return 0, None, None
    value = rec["quantity"] * rec["unit_price"]
    if asset["currency"] == "IRR":
        usd = (value / usd_rate) if (usd_rate and usd_rate > 0) else None
    else:
        usd = value
    return value, usd, rec

def currency_label(cur): return "ریال" if cur == "IRR" else "دلار"

def get_version(key):
    if key not in st.session_state: st.session_state[key] = 0
    return st.session_state[key]

def bump_version(key): st.session_state[key] = st.session_state.get(key, 0) + 1

def sync_usd_rates_to_gold_funds(data):
    rates = sorted(data.get("usd_rates", []), key=lambda x: x.get("created_at", ""))
    updated = 0; missing = 0
    for gf in data.get("gold_funds", []):
        for rec in gf.get("records", []):
            rec_date = rec.get("date_gregorian", "")[:10]
            if not rec_date: continue
            rate_at = None
            for ur in rates:
                if ur.get("created_at", "")[:10] <= rec_date: rate_at = ur["rate"]
                else: break
            if rate_at is not None:
                if rec.get("usd_rate_used") != rate_at:
                    rec["usd_rate_used"] = rate_at; updated += 1
            else: missing += 1
    return updated, missing

def build_portfolio_timeline(data):
    assets = data.get("assets", [])
    usd_rates = sorted(data.get("usd_rates", []), key=lambda x: x.get("created_at", ""))
    all_dates = set()
    for a in assets:
        for r in a.get("records", []):
            if r.get("date_gregorian"): all_dates.add(r["date_gregorian"][:10])
    for r in usd_rates:
        if r.get("created_at"): all_dates.add(r["created_at"][:10])
    if not all_dates: return pd.DataFrame()
    rows = []
    for d in sorted(all_dates):
        rate_at = None
        for ur in usd_rates:
            if ur.get("created_at", "")[:10] <= d: rate_at = ur["rate"]
            else: break
        t_irr = 0.0; t_usd = 0.0
        for a in assets:
            recs = [r for r in a.get("records", []) if r.get("date_gregorian", "")[:10] <= d]
            if not recs: continue
            latest = max(recs, key=lambda r: r.get("date_gregorian", ""))
            val = latest["quantity"] * latest["unit_price"]
            if a["currency"] == "IRR":
                t_irr += val
                if rate_at and rate_at > 0: t_usd += val / rate_at
            else:
                t_usd += val
                if rate_at and rate_at > 0: t_irr += val * rate_at
        try:
            dt = datetime.fromisoformat(d + "T00:00:00")
            jd = jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
        except Exception: jd = d
        rows.append({"date_gregorian": d, "date_jalali": jd, "total_irr": t_irr, "total_usd": t_usd})
    return pd.DataFrame(rows)

def render_html_table(df, dark=False):
    bg_head = "#161b22" if dark else "#f3f4f6"
    bg_odd = "#0d1117" if dark else "#f9fafb"
    bg_even = "#161b22" if dark else "#ffffff"
    border = "#30363d" if dark else "#e5e7eb"
    text_col = "#e6edf3" if dark else "#1f2937"
    html = (f'<div style="overflow-x:auto; margin:8px 0;">'
            f'<table style="width:100%; border-collapse:collapse; direction:rtl; '
            f'font-family:inherit; font-size:0.9rem; color:{text_col};">')
    html += f'<thead><tr style="background:{bg_head}; font-weight:bold;">'
    for col in df.columns:
        html += f'<th style="padding:10px 12px; text-align:right; border-bottom:2px solid {border}; white-space:nowrap;">{col}</th>'
    html += '</tr></thead><tbody>'
    for idx, row in df.iterrows():
        bg = bg_odd if idx % 2 == 0 else bg_even
        html += f'<tr style="background:{bg};">'
        for val in row:
            html += f'<td style="padding:8px 12px; text-align:right; border-bottom:1px solid {border};">{val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

# ================== تحلیل صندوق طلا ==================
def unit_usd_equivalent(record):
    rate = record.get("usd_rate_used", 0)
    if rate <= 0: return None
    return record["unit_price"] / rate

def gold_gram_per_unit(record):
    if record.get("ounce_price_usd", 0) <= 0 or record.get("usd_rate_used", 0) <= 0 or record.get("unit_price", 0) <= 0:
        return None
    return (record["unit_price"] * 31.1035) / (record["ounce_price_usd"] * record["usd_rate_used"])

def gold_fund_analytics(fund):
    records = sorted(fund.get("records", []), key=lambda r: r.get("date_gregorian", ""))
    if not records: return []
    rows = []
    first_usd = None
    for i, r in enumerate(records):
        usd_eq = unit_usd_equivalent(r)
        if first_usd is None and usd_eq: first_usd = usd_eq
        ounce_change = None; usd_change = None
        if i > 0:
            prev = records[i-1]
            if prev.get("ounce_price_usd", 0) > 0:
                ounce_change = (r["ounce_price_usd"] / prev["ounce_price_usd"] - 1) * 100
            if prev.get("usd_rate_used", 0) > 0 and r.get("usd_rate_used", 0) > 0:
                usd_change = (r["usd_rate_used"] / prev["usd_rate_used"] - 1) * 100
        usd_return = None
        if first_usd and usd_eq: usd_return = (usd_eq / first_usd - 1) * 100
        gram = gold_gram_per_unit(r)
        rows.append({"record": r, "usd_equivalent": usd_eq, "usd_return_pct": usd_return,
                     "ounce_change_pct": ounce_change, "usd_change_pct": usd_change,
                     "gram_per_unit": gram})
    return rows

def dollar_trap_analysis(fund, days=30):
    records = sorted(fund.get("records", []), key=lambda r: r.get("date_gregorian", ""))
    if len(records) < 2: return None
    last = records[-1]
    last_date_str = last.get("date_gregorian", "")[:10]
    if not last_date_str: return None
    try:
        dt_last = datetime.fromisoformat(last_date_str + "T00:00:00")
        cutoff = (dt_last - timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception: return None
    older = None
    for r in records:
        if r.get("date_gregorian", "")[:10] >= cutoff:
            older = r; break
    if not older or older.get("id") == last.get("id"): return None
    ounce_change = 0; usd_change = 0
    if older.get("ounce_price_usd", 0) > 0:
        ounce_change = (last["ounce_price_usd"] / older["ounce_price_usd"] - 1) * 100
    if older.get("usd_rate_used", 0) > 0:
        usd_change = (last["usd_rate_used"] / older["usd_rate_used"] - 1) * 100
    return {"usd_change": usd_change, "ounce_change": ounce_change,
            "gap": usd_change - ounce_change, "days": days,
            "older_date": older.get("date_jalali"), "last_date": last.get("date_jalali")}

def ounce_signal(fund, days=90):
    records = sorted(fund.get("records", []), key=lambda r: r.get("date_gregorian", ""))
    if len(records) < 3: return "⚪ داده کافی نیست"
    last = records[-1]
    last_date_str = last.get("date_gregorian", "")[:10]
    if not last_date_str: return "⚪"
    try:
        dt_last = datetime.fromisoformat(last_date_str + "T00:00:00")
        cutoff = (dt_last - timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception:
        return "⚪"
    recent = [r for r in records if r.get("date_gregorian", "")[:10] >= cutoff and r.get("ounce_price_usd", 0) > 0]
    if len(recent) < 3:
        recent = [r for r in records if r.get("ounce_price_usd", 0) > 0]
    if not recent: return "⚪ داده انس کافی نیست"
    avg = sum(r["ounce_price_usd"] for r in recent) / len(recent)
    current = last.get("ounce_price_usd", 0)
    if current <= 0 or avg <= 0: return "⚪ داده معتبر نیست"
    diff = (current / avg - 1) * 100
    if diff > 5: return f"🔴 انس {diff:+.1f}% بالای میانگین {days}روزه — فروش"
    elif diff > 0: return f"🟡 انس {diff:+.1f}% بالای میانگین — کمی فروش"
    elif diff > -5: return f"🟢 انس {diff:+.1f}% زیر میانگین — کمی خرید"
    else: return f"🟢🟢 انس {diff:+.1f}% زیر میانگین — خرید قوی"

# ================== محاسبه بازده ماهانه ==================
def compute_monthly_returns(data, year_jalali):
    usd_rates_sorted = sorted(data.get("usd_rates", []), key=lambda x: x.get("created_at", ""))
    def get_rate_at(date_str):
        rate = None
        for ur in usd_rates_sorted:
            if ur.get("created_at", "")[:10] <= date_str:
                try:
                    candidate = float(ur.get("rate", 0) or 0)
                    if candidate > 0: rate = candidate
                except (TypeError, ValueError): continue
            else: break
        return rate
    def price_irr_for_record(record, item_type, item_currency):
        try: unit_price = float(record.get("unit_price", 0) or 0)
        except (TypeError, ValueError): return None
        if unit_price <= 0: return None
        if item_type == "gold" or item_currency == "IRR": return unit_price
        date_str = record.get("date_gregorian", "")[:10]
        rate = get_rate_at(date_str)
        return unit_price * rate if rate and rate > 0 else None
    items = []
    for asset in data.get("assets", []):
        items.append({"id": f"asset_{asset['id']}", "name": asset["name"], "type": "asset",
                      "currency": asset.get("currency", "IRR"), "records": asset.get("records", [])})
    for fund in data.get("gold_funds", []):
        items.append({"id": f"gold_{fund['id']}", "name": f"🥇 {fund['name']}", "type": "gold",
                      "currency": "IRR", "records": fund.get("records", [])})
    results = {}
    for item in items:
        records = sorted(item["records"], key=lambda r: r.get("date_gregorian", ""))
        monthly = {}
        for month in range(1, 13):
            try:
                start_boundary = jdatetime.date(year_jalali, month, 1)
                end_boundary = (jdatetime.date(year_jalali + 1, 1, 1) if month == 12
                                else jdatetime.date(year_jalali, month + 1, 1))
                start_g = start_boundary.togregorian().strftime("%Y-%m-%d")
                end_g = end_boundary.togregorian().strftime("%Y-%m-%d")
            except Exception:
                monthly[month] = None; continue
            month_records = [r for r in records if start_g <= r.get("date_gregorian", "")[:10] < end_g]
            if not month_records:
                monthly[month] = None; continue
            start_candidates = [r for r in records if r.get("date_gregorian", "")[:10] < start_g]
            start_rec = start_candidates[-1] if start_candidates else month_records[0]
            end_rec = month_records[-1]
            if start_rec is end_rec:
                monthly[month] = None; continue
            start_price_irr = price_irr_for_record(start_rec, item["type"], item["currency"])
            end_price_irr = price_irr_for_record(end_rec, item["type"], item["currency"])
            if start_price_irr is None or end_price_irr is None or start_price_irr <= 0:
                monthly[month] = None; continue
            return_pct = ((end_price_irr / start_price_irr) - 1) * 100
            try: start_quantity = float(start_rec.get("quantity", 0) or 0)
            except (TypeError, ValueError): start_quantity = 0.0
            profit_irr = (end_price_irr - start_price_irr) * start_quantity
            monthly[month] = {"return_pct": return_pct, "profit_irr": profit_irr,
                              "start_price_irr": start_price_irr, "end_price_irr": end_price_irr,
                              "start_quantity": start_quantity}
        results[item["id"]] = {"name": item["name"], "monthly": monthly, "type": item["type"]}
    return results


def render_monthly_returns_page(data):
    st.header("📅 بازده ماهانه")
    st.caption("محاسبه بازده بر مبنای تغییر ارزش ریالی هر واحد؛ "
               "اگر سابقه‌ای پیش از ماه وجود نداشته باشد، بازده از اولین ثبت همان ماه "
               "تا آخرین ثبت ماه محاسبه می‌شود.")
    _dark = get_settings(data)["dark_mode"]
    all_dates = []
    for asset in data.get("assets", []):
        for record in asset.get("records", []):
            if record.get("date_jalali"): all_dates.append(record["date_jalali"])
    for fund in data.get("gold_funds", []):
        for record in fund.get("records", []):
            if record.get("date_jalali"): all_dates.append(record["date_jalali"])
    years = sorted(set(int(d[:4]) for d in all_dates if d[:4].isdigit()), reverse=True)
    if not years:
        st.info("هنوز داده‌ای ثبت نشده."); return
    month_names_full = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    c1, c2, c3 = st.columns(3)
    selected_year = c1.selectbox("سال (شمسی)", years, key="mr_year")
    type_filter = c2.selectbox("نوع", ["همه", "دارایی‌ها", "صندوق‌های طلا"], key="mr_type")
    month_from = c3.selectbox("از ماه", month_names_full, index=0, key="mr_from")
    month_to = st.selectbox("تا ماه", month_names_full, index=11, key="mr_to")
    from_idx = month_names_full.index(month_from) + 1
    to_idx = month_names_full.index(month_to) + 1
    if from_idx > to_idx:
        st.warning("ماه شروع باید قبل از ماه پایان باشد."); return
    results = compute_monthly_returns(data, selected_year)
    if type_filter == "دارایی‌ها":
        results = {k: v for k, v in results.items() if v["type"] == "asset"}
    elif type_filter == "صندوق‌های طلا":
        results = {k: v for k, v in results.items() if v["type"] == "gold"}
    if not results:
        st.info("داده‌ای برای این انتخاب وجود ندارد."); return
    month_labels = month_names_full[from_idx - 1:to_idx]
    plot_data = {}
    for item_id, info in results.items():
        monthly_values = [info["monthly"].get(m) for m in range(from_idx, to_idx + 1)]
        if any(value is not None for value in monthly_values):
            plot_data[info["name"]] = monthly_values
    if not plot_data:
        st.info("برای این بازه، بازده قابل محاسبه‌ای وجود ندارد."); return
    mode = st.radio("نوع نمایش", ["📊 درصد بازده", "💰 سود / زیان به ریال"],
                    horizontal=True, key="mr_mode")
    fig = go.Figure()
    for name, values in plot_data.items():
        if mode.startswith("📊"):
            y_vals = [v["return_pct"] if v is not None else 0 for v in values]
            text_vals = [f'{v["return_pct"]:+.2f}%' if v is not None else "—" for v in values]
            y_title = "بازده ماهانه (%)"
        else:
            y_vals = [v["profit_irr"] if v is not None else 0 for v in values]
            text_vals = [f'{v["profit_irr"]:+,.0f} ریال' if v is not None else "—" for v in values]
            y_title = "سود / زیان ماهانه (ریال)"
        fig.add_trace(go.Bar(name=name, x=month_labels, y=y_vals, text=text_vals,
                             textposition="outside",
                             hovertemplate="%{x}<br>%{fullData.name}<br>%{text}<extra></extra>"))
    fig.update_layout(
        barmode="group", title=f"بازده ماهانه سال {selected_year}",
        xaxis_title="ماه", yaxis_title=y_title,
        font=dict(family="Vazirmatn, Tahoma", size=12, color="#e6edf3" if _dark else "#1f2937"),
        paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
        plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
        hovermode="x unified", height=500,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("📋 جدول بازده ماهانه")
    df_table = pd.DataFrame({"ماه": month_labels})
    for name, values in plot_data.items():
        if mode.startswith("📊"):
            df_table[name] = [f'{v["return_pct"]:+.2f}%' if v is not None else "—" for v in values]
        else:
            df_table[name] = [f'{v["profit_irr"]:+,.0f} ریال' if v is not None else "—" for v in values]
    render_html_table(df_table, dark=_dark)
    st.subheader("📊 خلاصه بازده در بازه انتخابی")
    summary_rows = []
    for name, values in plot_data.items():
        valid = [v for v in values if v is not None]
        if not valid: continue
        cumulative = 1.0
        for value in valid: cumulative *= 1 + value["return_pct"] / 100
        total_profit_irr = sum(v["profit_irr"] for v in valid)
        pct_values = [v["return_pct"] for v in valid]
        summary_rows.append({
            "نام": name,
            "سود / زیان ریالی بازه": f"{total_profit_irr:+,.0f} ریال",
            "بازده کل بازه": f"{(cumulative - 1) * 100:+.2f}%",
            "میانگین ماهانه": f"{sum(pct_values) / len(pct_values):+.2f}%",
            "بهترین ماه": f"{max(pct_values):+.2f}%",
            "بدترین ماه": f"{min(pct_values):+.2f}%",
            "تعداد ماه": len(valid)})
    if summary_rows:
        render_html_table(pd.DataFrame(summary_rows), dark=_dark)


# ================== 🔀 جفت ارز مصنوعی ==================
def get_synthetic_instruments(data):
    """لیست ابزارهای دارای تاریخچه برای ساخت جفت مصنوعی."""
    instruments = []
    for asset in data.get("assets", []):
        records = [row for row in asset.get("records", []) if float(row.get("unit_price", 0) or 0) > 0]
        if not records:
            continue
        instruments.append({
            "id": f"asset:{asset['id']}",
            "label": f"{asset_overview_emoji(asset)} {asset.get('name', 'بدون نام')}",
            "kind": "asset",
            "color": asset.get("color", "#3b82f6"),
            "records": records,
            "currency": asset.get("currency", "IRR"),
        })
    for fund in data.get("gold_funds", []):
        records = [row for row in fund.get("records", []) if float(row.get("unit_price", 0) or 0) > 0]
        if not records:
            continue
        instruments.append({
            "id": f"gold:{fund['id']}",
            "label": f"{fund.get('icon', '🥇')} {fund['name']}",
            "kind": "gold",
            "color": "#eab308",
            "records": records,
            "currency": "IRR",
        })
    if data.get("usd_rates"):
        instruments.append({
            "id": "usd",
            "label": "💵 دلار آزاد",
            "kind": "usd",
            "color": "#f59e0b",
            "records": data["usd_rates"],
            "currency": "IRR",
        })
    return instruments


def _price_history(data, instrument_id):
    """سری زمانی قیمت یک ابزار به ریال — مرتب‌شده بر اساس تاریخ."""
    kind, _, raw_id = instrument_id.partition(":")
    rows = []
    if instrument_id == "usd":
        for item in data.get("usd_rates", []):
            rate = float(item.get("rate", 0) or 0)
            if rate > 0:
                rows.append((item.get("created_at", "")[:10], rate))
    elif kind == "gold":
        fund = next((item for item in data.get("gold_funds", []) if item["id"] == raw_id), None)
        for record in (fund or {}).get("records", []):
            price = float(record.get("unit_price", 0) or 0)
            if price > 0:
                rows.append((record.get("date_gregorian", "")[:10], price))
    else:
        asset = next((item for item in data.get("assets", []) if item["id"] == raw_id), None)
        for record in (asset or {}).get("records", []):
            unit = float(record.get("unit_price", 0) or 0)
            if unit <= 0:
                continue
            rate = _rate_at(data, record.get("date_gregorian", "")[:10])
            price = unit if (asset or {}).get("currency", "IRR") != "USD" else unit * (rate or 0)
            if price > 0:
                rows.append((record.get("date_gregorian", "")[:10], price))
    return sorted(rows, key=lambda item: item[0])


def _price_on(history, date_str):
    """آخرین قیمت موجود تا تاریخ مشخص."""
    value = None
    for date, price in history:
        if date <= date_str:
            value = price
        else:
            break
    return value


def build_pair_series(data, left_id, right_id):
    """ساخت DataFrame با نسبت و شاخص‌های نرمال‌شده برای دو ابزار."""
    left = _price_history(data, left_id)
    right = _price_history(data, right_id)
    dates = sorted({date for date, _ in left} | {date for date, _ in right})
    rows = []
    for date in dates:
        left_price = _price_on(left, date)
        right_price = _price_on(right, date)
        if not left_price or not right_price or left_price <= 0 or right_price <= 0:
            continue
        rows.append({
            "date": date,
            "left": left_price,
            "right": right_price,
            "ratio": left_price / right_price,
        })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    base = frame.iloc[0]
    frame["left_index"] = frame["left"] / base["left"] * 100
    frame["right_index"] = frame["right"] / base["right"] * 100
    frame["ratio_index"] = frame["ratio"] / base["ratio"] * 100
    frame["label"] = frame["date"].map(lambda v: iso_to_jalali(v + "T00:00:00", with_time=False))
    return frame


def render_synthetic_page(data, dark):
    st.header("🔀 جفت ارز مصنوعی")
    st.caption("نسبت قیمت دو ابزار دارای تاریخچه؛ برای نمونه «صندوق طلا / دلار» یا «وبملت / صندوق طلا». "
               "قیمت‌ها برای مقایسه به ریال تبدیل می‌شوند.")
    instruments = get_synthetic_instruments(data)
    if len(instruments) < 2:
        st.info("برای ساخت جفت، دست‌کم دو ابزار دارای داده لازم است. "
                "یک دارایی، صندوق طلا یا نرخ دلار ثبت کنید.")
        return

    labels = {item["id"]: item["label"] for item in instruments}

    with st.container(border=True):
        st.subheader("➕ ساخت جفت جدید")
        c1, c2 = st.columns(2)
        left_id = c1.selectbox("سمت اول (صورت)", list(labels), format_func=labels.get, key="pair_left")
        right_id = c2.selectbox("سمت دوم (مخرج)", list(labels),
                                index=min(1, len(labels) - 1),
                                format_func=labels.get, key="pair_right")
        duplicate = any(
            pair.get("left") == left_id and pair.get("right") == right_id
            for pair in data.get("synthetic_pairs", [])
        )
        if st.button("🔀 ساخت جفت مصنوعی", use_container_width=True,
                     disabled=(left_id == right_id or duplicate), key="create_pair_btn"):
            data.setdefault("synthetic_pairs", []).append({
                "id": _short_id(),
                "left": left_id,
                "right": right_id,
                "name": f"{labels[left_id]} / {labels[right_id]}",
                "created_at": datetime.now().isoformat(),
            })
            st.session_state.data = data
            save_all(data)
            st.rerun()
        if left_id == right_id:
            st.caption("دو سمت باید متفاوت باشند.")
        elif duplicate:
            st.caption("این جفت قبلاً ساخته شده است.")

    pairs = data.get("synthetic_pairs", [])
    if not pairs:
        st.info("هنوز جفتی نساخته‌اید.")
        return

    pair_labels = {pair["id"]: pair.get("name", "") for pair in pairs}
    selected_pair_id = st.selectbox("جفت‌های ذخیره‌شده", list(pair_labels),
                                    format_func=pair_labels.get, key="pair_select")
    pair = next(item for item in pairs if item["id"] == selected_pair_id)
    left_label = labels.get(pair.get("left"), pair.get("left", ""))
    right_label = labels.get(pair.get("right"), pair.get("right", ""))

    frame = build_pair_series(data, pair.get("left"), pair.get("right"))
    c1, c2, c3 = st.columns(3)
    if frame.empty:
        c1.metric("نسبت فعلی", "—")
        c2.metric("تغییر از ابتدا", "—")
        c3.metric("تعداد نقاط", "0")
        st.warning("داده‌ای برای این جفت موجود نیست؛ ممکن است منبع حذف شده باشد.")
    else:
        last = frame.iloc[-1]
        c1.metric("نسبت فعلی", f"{last['ratio']:,.5f}",
                  help=f"{left_label} ÷ {right_label}")
        c2.metric("تغییر نسبت از ابتدا", f"{last['ratio_index'] - 100:+.2f}٪")
        c3.metric("تعداد نقاط", f"{len(frame):,}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=frame["label"], y=frame["ratio"], mode="lines+markers",
            name="نسبت مصنوعی", line={"color": "#8b5cf6", "width": 3},
            fill="tozeroy"))
        fig.update_layout(yaxis_title="نسبت", xaxis_title="تاریخ")
        _apply_chart_style(fig, dark, height=400)
        st.plotly_chart(fig, use_container_width=True)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=frame["label"], y=frame["left_index"], mode="lines+markers",
            name=left_label, line={"color": "#3b82f6", "width": 3}))
        fig2.add_trace(go.Scatter(
            x=frame["label"], y=frame["right_index"], mode="lines+markers",
            name=right_label, line={"color": "#10b981", "width": 3}))
        fig2.update_layout(yaxis_title="شاخص (پایه = ۱۰۰)")
        _apply_chart_style(fig2, dark, height=360)
        st.plotly_chart(fig2, use_container_width=True)

        table = frame[["label", "left", "right", "ratio", "ratio_index"]].copy()
        table.columns = ["تاریخ", left_label, right_label, "نسبت", "شاخص"]
        render_html_table(table.sort_values("تاریخ", ascending=False).head(15), dark=dark)

        with st.expander("🗑️ حذف این جفت"):
            if st.button("حذف جفت مصنوعی", key=f"del_pair_{pair['id']}", use_container_width=True):
                data["synthetic_pairs"] = [item for item in pairs if item["id"] != pair["id"]]
                st.session_state.data = data
                save_all(data)
                st.rerun()


# ================== گرید آیکون ==================
def _icon_grid_picker(prefix, current, on_save):
    icons = load_fa_icons()
    all_cats = set()
    for ic in icons:
        for c in ic.get("categories", []): all_cats.add(c)
    cat_order = [k for k in CATEGORY_LABELS.keys() if k in all_cats]
    cat_order += sorted([c for c in all_cats if c not in CATEGORY_LABELS])
    cat_options = ["__all__"] + cat_order
    c1, c2 = st.columns([2, 3])
    cat = c1.selectbox("📂 دسته", cat_options,
                       format_func=lambda x: "🌐 همه" if x == "__all__" else CATEGORY_LABELS.get(x, x),
                       key=f"{prefix}_cat")
    s = c2.text_input("🔍", key=f"{prefix}_search", placeholder="جستجو...", label_visibility="collapsed")
    filtered = icons if cat == "__all__" else [i for i in icons if cat in i.get("categories", [])]
    if s:
        q = s.lower()
        filtered = [i for i in filtered if q in i["label"].lower() or q in i["class"].lower()]
    per_page = 48; total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    pk = f"{prefix}_page"; catk = f"{prefix}_cat_prev"
    if catk not in st.session_state or st.session_state[catk] != cat:
        st.session_state[pk] = 0; st.session_state[catk] = cat
    if st.session_state.get(pk, 0) >= pages: st.session_state[pk] = 0
    page = st.session_state.get(pk, 0)
    display = filtered[page * per_page:(page + 1) * per_page]
    st.caption(f"**{total}** آیکون — صفحه **{page + 1}** از **{pages}**")
    if total == 0: st.info("آیکونی یافت نشد."); return
    for row in range(0, len(display), 8):
        cols = st.columns(8)
        for j, ic in enumerate(display[row:row + 8]):
            with cols[j]:
                is_cur = (ic["class"] == current)
                border = "3px solid #22c55e" if is_cur else "1px solid #e5e7eb"
                st.markdown(
                    f'<div style="text-align:center; padding:10px 4px; border:{border}; '
                    f'border-radius:8px; margin-bottom:4px; background:#f9fafb;">'
                    f'<i class="fa-solid {ic["class"]}" style="font-size:1.6rem; color:#3b82f6;"></i></div>',
                    unsafe_allow_html=True)
                lbl = "✅" if is_cur else "انتخاب"
                if st.button(lbl, key=f"{prefix}_btn_{ic['class']}", use_container_width=True, disabled=is_cur):
                    on_save(ic["class"]); st.rerun()
    if pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("◀ قبلی", key=f"{prefix}_prev", use_container_width=True, disabled=(page == 0)):
                st.session_state[pk] = page - 1; st.rerun()
        with pc2:
            st.markdown(f'<div style="text-align:center; padding-top:8px; font-weight:600;">صفحه {page + 1} / {pages}</div>', unsafe_allow_html=True)
        with pc3:
            if st.button("بعدی ▶", key=f"{prefix}_next", use_container_width=True, disabled=(page >= pages - 1)):
                st.session_state[pk] = page + 1; st.rerun()

def _emoji_grid_picker(prefix, current, on_save):
    EMOJIS = ["📁", "🪙", "💎", "👑", "💰", "💵", "💴", "💶", "💷", "🏦",
              "🏠", "🏢", "🚗", "🚚", "📈", "📊", "📉", "⚡", "🔥", "💧",
              "🌾", "🏭", "🎁", "🥇", "🥈", "🥉", "🌱", "💼", "🏪", "🧾",
              "🏷️", "⚖️", "🛡️", "⛽", "🔐", "👛", "💲", "₿", "Ξ", "📦",
              "🎯", "🎨", "🌍", "⭐", "❤️", "💡", "🔑", "🎓", "🎵", "🎮"]
    for row in range(0, len(EMOJIS), 10):
        cols = st.columns(10)
        for j, em in enumerate(EMOJIS[row:row + 10]):
            with cols[j]:
                is_cur = (em == current)
                lbl = f"{'✅' if is_cur else ''}{em}"
                if st.button(lbl, key=f"{prefix}_em_{row + j}", use_container_width=True):
                    on_save(em); st.rerun()
    st.divider()
    c1, c2 = st.columns([3, 1])
    custom = c1.text_input("ایموجی دلخواه", value=current or "", max_chars=8, key=f"{prefix}_custom")
    if c2.button("💾 ذخیره", key=f"{prefix}_save_custom", use_container_width=True):
        on_save(custom.strip()[:8]); st.rerun()
    if st.button("🔄 خودکار", key=f"{prefix}_clear", use_container_width=True):
        on_save(""); st.rerun()

# ================== مقداردهی ==================
if "data" not in st.session_state:
    st.session_state.data = load_all()
st.session_state.data = migrate_data(st.session_state.data)
data = st.session_state.data
data.setdefault("assets", []); data.setdefault("usd_rates", [])
data.setdefault("gold_funds", []); data.setdefault("synthetic_pairs", [])

inject_app(data)
_dark = get_settings(data)["dark_mode"]
assets = data.get("assets", [])

# ================== سایدبار ==================
with st.sidebar:
    c_date, c_mode, c_logout = st.columns([3, 1, 1])
    with c_date: st.markdown(f"### 🗓️ {today_jalali_str()}")
    with c_mode:
        if st.button("☀️" if _dark else "🌙", key="dark_toggle_btn", help="روز/شب", use_container_width=True):
            data["settings"]["dark_mode"] = not _dark
            st.session_state.data = data; save_all(data); st.rerun()
    with c_logout:
        if st.button("🚪", key="logout_btn", help="خروج", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.pop("data", None)
            st.query_params.clear(); st.rerun()
    st.divider()

    rate, rate_date = get_current_usd_rate(data)
    if rate:
        bg_card = "#1f6feb" if _dark else "#3b82f6"
        bg_grad = "linear-gradient(135deg, #1a2332 0%, #1f2937 100%)" if _dark else "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)"
        title_col = "#8b949e" if _dark else "#6b7280"
        value_col = "#58a6ff" if _dark else "#1e40af"
        st.markdown(f"""
        <div style="background: {bg_grad}; padding: 14px 16px; border-radius: 10px; border-right: 4px solid {bg_card}; margin-bottom: 12px; direction: rtl; text-align: right;">
            <div style="font-size: 0.82rem; color: {title_col}; margin-bottom: 6px;">💵 نرخ فعلی دلار</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: {value_col};">{rate:,.0f}<span style="font-size: 0.95rem; color: {title_col};"> ریال</span></div>
            <div style="font-size: 0.72rem; color: {title_col}; margin-top: 6px;">آخرین: {rate_date}</div>
        </div>
        """, unsafe_allow_html=True)
    else: st.info("💡 هنوز نرخی ثبت نشده.")

    st.divider()
    st.markdown("**💾 وضعیت ذخیره‌سازی**")
    if data.get("last_saved"): st.caption(f"✅ آخرین ذخیره: {data.get('last_saved_jalali', '—')}")
    else: st.caption("⚠️ هنوز ذخیره نشده")
    local_ok = os.path.exists(DATA_FILE)
    gh_status, gh_message = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
    c1, c2 = st.columns(2)
    c1.caption(f"{'✅' if local_ok else '❌'} محلی")
    c2.caption(f"{'✅' if gh_status == 'ok' else '❌'} GitHub")
    if gh_status != "ok": st.error(f"⚠️ {gh_message}")
    if st.button("💾 ذخیره فوری + تأیید", use_container_width=True, key="force_save"):
        if save_all(data): st.rerun()

    st.divider()
    with st.expander("📥 پشتیبان / 📤 بازیابی", expanded=False):
        st.download_button("📥 دانلود JSON", data=json.dumps(data, ensure_ascii=False, indent=2),
                          file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                          mime="application/json", use_container_width=True)
        uploaded = st.file_uploader("📤 آپلود JSON", type=["json"], key="uploader")
        if uploaded is not None:
            try:
                imported = migrate_data(json.loads(uploaded.read().decode("utf-8")))
                if st.button("✅ اعمال", use_container_width=True):
                    st.session_state.data = imported; save_all(imported); st.rerun()
            except Exception as e: st.error(f"فایل معتبر نیست: {e}")

# ================== ناوبری ==================
nav_options = (
    ["overview", "journal", "usd", "gold", "synthetic", "monthly"]
    + [f"asset_{a['id']}" for a in assets]
    + ["settings"]
)
nav_labels = {
    "overview": f"{NAV_EMOJI['overview']} {NAV_LABELS['overview']}",
    "journal": f"{NAV_EMOJI['journal']} {NAV_LABELS['journal']}",
    "usd": f"{NAV_EMOJI['usd']} {NAV_LABELS['usd']}",
    "gold": f"{NAV_EMOJI['gold']} {NAV_LABELS['gold']}",
    "synthetic": f"{NAV_EMOJI['synthetic']} {NAV_LABELS['synthetic']}",
    "monthly": f"{NAV_EMOJI['monthly']} {NAV_LABELS['monthly']}",
    "settings": f"{NAV_EMOJI['settings']} {NAV_LABELS['settings']}",
}
for a in assets: nav_labels[f"asset_{a['id']}"] = f"{asset_overview_emoji(a)} {a['name']}"

if "nav_version" not in st.session_state: st.session_state.nav_version = 0
if "pending_nav" in st.session_state:
    pending = st.session_state.pending_nav
    del st.session_state.pending_nav
    if pending in nav_options:
        st.session_state.nav_version += 1
        st.session_state[f"nav_pills_v{st.session_state.nav_version}"] = pending

_widget_key = f"nav_pills_v{st.session_state.nav_version}"
if _widget_key not in st.session_state: st.session_state[_widget_key] = "overview"
if st.session_state[_widget_key] not in nav_options: st.session_state[_widget_key] = "overview"

if hasattr(st, "pills"):
    selected = st.pills("ناوبری", options=nav_options, format_func=lambda x: nav_labels.get(x, x),
                       selection_mode="single", label_visibility="collapsed", key=_widget_key)
    if selected is None: selected = st.session_state[_widget_key]
else:
    selected = st.radio("ناوبری", options=nav_options, format_func=lambda x: nav_labels.get(x, x),
                       horizontal=True, label_visibility="collapsed", key=_widget_key + "_radio")

# ================== صفحه تنظیمات ==================
def render_settings_page(data):
    st.header("⚙️ تنظیمات")
    settings = get_settings(data)
    all_fonts = get_all_fonts(data)
    dark = settings["dark_mode"]
    t_font, t_nav, t_assets, t_emoji, t_lib, t_verify, t_storage = st.tabs([
        "🔤 فونت", "🎨 آیکون منو", "📦 آیکون دارایی", "😀 ایموجی", "📚 کتابخانه", "🔍 تأیید ذخیره", "💾 وضعیت"])

    with t_font:
        st.subheader("🔤 فونت برنامه")
        font_keys = list(all_fonts.keys())
        cur_font = settings["font"] if settings["font"] in font_keys else "vazirmatn"
        c1, c2 = st.columns([3, 1])
        new_font = c1.selectbox("فونت", font_keys, index=font_keys.index(cur_font),
                               format_func=lambda k: all_fonts[k]["name"] + (" (سفارشی)" if not all_fonts[k]["builtin"] else ""),
                               key="font_select_v2")
        if c2.button("💾 ذخیره فونت", use_container_width=True, key="apply_font_btn"):
            data["settings"]["font"] = new_font
            st.session_state.data = data; save_all(data); st.rerun()
        preview_family = all_fonts[new_font]["family"]
        bg_prev = "#161b22" if dark else "#f9fafb"; border_prev = "#30363d" if dark else "#3b82f6"
        st.markdown(
            f'<div style="padding:20px; border:2px solid {border_prev}; border-radius:10px; margin:16px 0; background:{bg_prev}; direction:rtl;">'
            f'<div style="font-family:\'{preview_family}\', Tahoma; font-size:1.8rem;">داشبورد مالی — ۱۲۳۴۵</div>'
            f'<div style="font-family:\'{preview_family}\', Tahoma; font-size:1.05rem;">متن نمونه: ۱۲۳۴۵۶۷۸۹۰ | 1234567890</div></div>',
            unsafe_allow_html=True)
        st.divider()
        st.subheader("📤 بارگذاری فونت سفارشی")
        st.caption("TTF, OTF, WOFF, WOFF2 — حداکثر ۱۰MB")
        with st.form("upload_font_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("فایل", type=["ttf", "otf", "woff", "woff2"], key="custom_font_uploader")
            display_name = st.text_input("نام نمایشی")
            if st.form_submit_button("📤 بارگذاری", use_container_width=True):
                if uploaded_file is None: st.error("فایل انتخاب کنید.")
                elif uploaded_file.size > 10 * 1024 * 1024: st.error("حجم بیش از ۱۰MB.")
                else:
                    try:
                        fb = uploaded_file.read()
                        ext = uploaded_file.name.lower().rsplit(".", 1)[-1]
                        fmap = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}
                        mmap = {"ttf": "font/ttf", "otf": "font/otf", "woff": "font/woff", "woff2": "font/woff2"}
                        base_name = uploaded_file.name.rsplit(".", 1)[0]
                        safe = re.sub(r"[^a-z0-9_]", "_", base_name.lower())[:40]
                        fkey = f"custom_{safe}"; c = 1; orig = fkey
                        existing = data["settings"].get("custom_fonts", {})
                        while fkey in existing: c += 1; fkey = f"{orig}_{c}"
                        data["settings"].setdefault("custom_fonts", {})[fkey] = {
                            "display_name": (display_name.strip() or base_name)[:60],
                            "data": base64.b64encode(fb).decode(),
                            "format": fmap.get(ext, "truetype"), "mime": mmap.get(ext, "font/ttf"),
                            "filename": uploaded_file.name, "size_bytes": len(fb),
                            "uploaded_at": datetime.now().isoformat()}
                        st.session_state.data = data; save_all(data)
                        st.success("✅ بارگذاری شد."); st.rerun()
                    except Exception as e: st.error(f"خطا: {e}")
        custom_fonts = data["settings"].get("custom_fonts", {})
        if custom_fonts:
            st.divider(); st.subheader("📚 فونت‌های سفارشی")
            for key, info in list(custom_fonts.items()):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
                    c1.markdown(f'<div style="text-align:center; font-family:\'{key}\', Tahoma; font-size:2.2rem; color:#3b82f6;">آ</div>', unsafe_allow_html=True)
                    c2.markdown(f"**{info.get('display_name', key)}**")
                    c2.caption(f"{info.get('size_bytes', 0) // 1024:,} KB")
                    c3.success("✅ فعال") if settings["font"] == key else c3.caption(f"`{key[:25]}`")
                    if c4.button("🗑️", key=f"del_font_{key}"):
                        del data["settings"]["custom_fonts"][key]
                        if data["settings"]["font"] == key: data["settings"]["font"] = "vazirmatn"
                        st.session_state.data = data; save_all(data); st.rerun()

    with t_nav:
        st.subheader("🎨 آیکون منو")
        st.caption("روی هر آیکون کلیک کنید. ✅ = فعلی")
        for nav_key in ["overview", "journal", "usd", "gold", "synthetic", "monthly", "settings"]:
            cfg = settings["nav_icons"].get(nav_key, DEFAULT_NAV_ICONS[nav_key])
            with st.container(border=True):
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f'<div style="text-align:center; padding:10px;"><i class="fa-solid {cfg["icon"]}" style="color:{cfg["color"]}; font-size:2.5rem;"></i></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{NAV_LABELS[nav_key]}**")
                    new_color = st.color_picker("رنگ", value=cfg["color"], key=f"color_nav_{nav_key}")
                with st.expander("🖼️ انتخاب آیکون از گرید"):
                    def _save_nav(icon_class, _k=nav_key):
                        current_color = data["settings"]["nav_icons"].get(_k, DEFAULT_NAV_ICONS[_k])["color"]
                        data["settings"]["nav_icons"][_k] = {"icon": icon_class, "color": current_color}
                        st.session_state.data = data; save_all(data)
                    _icon_grid_picker(f"nav_{nav_key}", cfg["icon"], _save_nav)
                if st.button("💾 ذخیره رنگ", key=f"save_nav_{nav_key}", use_container_width=True):
                    data["settings"]["nav_icons"][nav_key] = {"icon": cfg["icon"], "color": new_color}
                    st.session_state.data = data; save_all(data); st.rerun()

    with t_assets:
        st.subheader("📦 آیکون دارایی‌ها")
        if not assets: st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            for a in assets:
                cur_ic, cur_col = asset_icon(a), asset_color(a)
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.markdown(f'<div style="text-align:center; padding:10px;"><i class="fa-solid {cur_ic}" style="color:{cur_col}; font-size:2.5rem;"></i></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**{a['name']}**")
                        new_color = st.color_picker("رنگ", value=cur_col, key=f"color_asset_{a['id']}")
                    with st.expander("🖼️ انتخاب آیکون از گرید"):
                        def _save_asset(icon_class, _id=a["id"]):
                            for i, x in enumerate(data["assets"]):
                                if x["id"] == _id: data["assets"][i]["icon"] = icon_class; break
                            st.session_state.data = data; save_all(data)
                        _icon_grid_picker(f"asset_{a['id']}", cur_ic, _save_asset)
                    if st.button("💾 ذخیره رنگ", key=f"save_asset_{a['id']}", use_container_width=True):
                        for i, x in enumerate(data["assets"]):
                            if x["id"] == a["id"]: data["assets"][i]["color"] = new_color; break
                        st.session_state.data = data; save_all(data); st.rerun()

    with t_emoji:
        st.subheader("😀 ایموجی نمای کلی")
        if not assets: st.info("هنوز دارایی‌ای ثبت نشده.")
        else:
            for a in assets:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.markdown(f'<div style="text-align:center; font-size:2.8rem; padding:8px;">{asset_overview_emoji(a)}</div>', unsafe_allow_html=True)
                    with c2:
                        status = f"`{a['overview_emoji']}`" if a.get("overview_emoji") else "خودکار"
                        st.markdown(f"**{a['name']}** — {status}")
                    with st.expander("🖼️ انتخاب ایموجی"):
                        def _save_em(v, _id=a["id"]):
                            for i, x in enumerate(data["assets"]):
                                if x["id"] == _id: data["assets"][i]["overview_emoji"] = v; break
                            st.session_state.data = data; save_all(data)
                        _emoji_grid_picker(f"emoji_{a['id']}", a.get("overview_emoji", ""), _save_em)

    with t_lib:
        icons = load_fa_icons()
        st.caption(f"**{len(icons)}** آیکون FA")
        s = st.text_input("🔍 جستجو", key="fa_lib_search")
        filtered = [ic for ic in icons if s.lower() in ic["label"].lower() or s.lower() in ic["class"].lower()] if s else icons
        display = filtered[:120]
        for i in range(0, len(display), 8):
            cols = st.columns(8)
            for j, ic in enumerate(display[i:i + 8]):
                with cols[j]:
                    st.markdown(
                        f'<div style="text-align:center; padding:8px; border:1px solid #e5e7eb; border-radius:6px;" title="{ic["class"]}">'
                        f'<i class="fa-solid {ic["class"]}" style="font-size:1.4rem; color:#3b82f6;"></i>'
                        f'<div style="font-size:0.6rem; color:#6b7280; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{ic["label"]}</div></div>',
                        unsafe_allow_html=True)

    with t_verify:
        st.subheader("🔍 تأیید ذخیره")
        if data.get("last_saved"): st.info(f"📅 آخرین: {data.get('last_saved_jalali', '—')}")
        else: st.warning("هنوز ذخیره‌ای انجام نشده")
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔍 تأیید", use_container_width=True, key="verify_gh_btn"):
                v_ok, v_msg, sha = verify_github_save(data)
                (st.success if v_ok else st.error)(f"{'✅' if v_ok else '❌'} {v_msg}")
        with col2:
            if st.button("🔄 بارگذاری از GitHub", use_container_width=True, key="force_load_btn"):
                gh = load_github_file()
                if gh:
                    st.session_state.data = migrate_data(gh)
                    save_local_file(st.session_state.data)
                    st.success("✅ بارگذاری شد"); st.rerun()
                else: st.error("❌ ناموفق")
        with col3:
            if st.button("💾 ذخیره فوری", use_container_width=True, key="force_save_btn"):
                if save_all(data): st.rerun()
        st.divider()
        gh = load_github_file()
        if gh:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**حافظه:**")
                st.caption(f"دارایی: {len(data.get('assets', []))}")
                st.caption(f"صندوق طلا: {len(data.get('gold_funds', []))}")
                st.caption(f"جفت مصنوعی: {len(data.get('synthetic_pairs', []))}")
                st.caption(f"last_saved: {data.get('last_saved', '—')[:19]}")
            with c2:
                st.markdown("**GitHub:**")
                st.caption(f"دارایی: {len(gh.get('assets', []))}")
                st.caption(f"صندوق طلا: {len(gh.get('gold_funds', []))}")
                st.caption(f"جفت مصنوعی: {len(gh.get('synthetic_pairs', []))}")
                st.caption(f"last_saved: {gh.get('last_saved', '—')[:19]}")
            if data.get("last_saved") == gh.get("last_saved"): st.success("✅ یکسان")
            else: st.warning("⚠️ متفاوت — ذخیره فوری بزنید")

    with t_storage:
        st.subheader("💾 وضعیت")
        local_ok = os.path.exists(DATA_FILE)
        if local_ok:
            _sz = os.path.getsize(DATA_FILE); _sz_kb = _sz / 1024; _est_gz = _sz_kb * 0.1
            if _sz_kb > 10240: st.error(f"⚠️ فایل {_sz_kb:,.0f} KB — بسیار بزرگ! GitHub gz: ~{_est_gz:,.0f} KB")
            elif _sz_kb > 5120: st.warning(f"⚠️ فایل {_sz_kb:,.0f} KB — بزرگ. GitHub gz: ~{_est_gz:,.0f} KB")
            else: st.info(f"📦 فایل محلی: **{_sz_kb:,.1f} KB** — GitHub gz تخمینی: **~{_est_gz:,.1f} KB**")
        gh_status, gh_msg = check_github_status(GITHUB_TOKEN, GITHUB_REPO)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📁 محلی**")
            st.success(f"✅ ({os.path.getsize(DATA_FILE):,} بایت)") if local_ok else st.error("❌ یافت نشد")
        with c2:
            st.markdown("**☁️ GitHub (gzip)**")
            st.success(f"✅ {gh_msg}") if gh_status == "ok" else st.error(f"❌ {gh_msg}")
        st.divider()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("دارایی‌ها", len(data.get("assets", [])))
        c2.metric("رکوردها", sum(len(a.get("records", [])) for a in data.get("assets", [])))
        c3.metric("نرخ دلار", len(data.get("usd_rates", [])))
        c4.metric("صندوق طلا", len(data.get("gold_funds", [])))
        c5.metric("جفت مصنوعی", len(data.get("synthetic_pairs", [])))

# ================== صفحه نمای کلی ==================
if selected == "overview":
    st.header("📊 نمای کلی دارایی‌ها")
    rate, _ = get_current_usd_rate(data)
    if not assets: st.info("هنوز دارایی‌ای ثبت نشده.")
    else:
        rows = []; total_usd = 0.0
        for a in assets:
            value, usd_val, rec = compute_asset_value(a, rate)
            if usd_val is not None: total_usd += usd_val
            rows.append({"دارایی": f"{asset_overview_emoji(a)} {a['name']}", "ارز": currency_label(a["currency"]),
                         "تعداد": rec["quantity"] if rec else 0, "قیمت واحد": rec["unit_price"] if rec else 0,
                         "ارزش": value, "معادل_دلاری": usd_val, "آخرین_تاریخ": rec["date_jalali"] if rec else "—"})
        df = pd.DataFrame(rows)
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 کل ارزش (دلاری)", f"${total_usd:,.2f}")
        c2.metric("📁 دارایی‌ها", len(assets))
        c3.metric("💵 نرخ دلار", f"{rate:,.0f} ریال" if rate else "ثبت نشده")
        st.subheader("🥧 ترکیب")
        pie_df = df.dropna(subset=["معادل_دلاری"]); pie_df = pie_df[pie_df["معادل_دلاری"] > 0]
        if not pie_df.empty:
            fig = px.pie(pie_df, values="معادل_دلاری", names="دارایی", hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=14, color="#e6edf3" if _dark else "#1f2937"),
                             legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                             margin=dict(t=20, b=20, l=10, r=10),
                             paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                             plot_bgcolor="rgba(0,0,0,0)" if _dark else "white")
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("📈 روند رشد")
        timeline = build_portfolio_timeline(data)
        if len(timeline) >= 2:
            for metric_key, title, color in [("total_usd", "💵 ارزش به دلار", "#3b82f6"), ("total_irr", "🇮🇷 ارزش به ریال", "#10b981")]:
                fig = px.line(timeline, x="date_jalali", y=metric_key, markers=True,
                             labels={"date_jalali": "تاریخ", metric_key: title}, color_discrete_sequence=[color])
                fig.update_traces(line=dict(width=3), marker=dict(size=7))
                fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                                 yaxis=dict(tickformat=",.0f"), xaxis=dict(title="تاریخ"),
                                 margin=dict(t=30, b=20), hovermode="x unified",
                                 paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 plot_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                                 title=dict(text=title, font=dict(size=14)))
                st.plotly_chart(fig, use_container_width=True)
            fu, lu = timeline["total_usd"].iloc[0], timeline["total_usd"].iloc[-1]
            fi, li = timeline["total_irr"].iloc[0], timeline["total_irr"].iloc[-1]
            g1, g2 = st.columns(2)
            g1.metric("تغییر دلاری", f"${lu:,.2f}", delta=f"{lu-fu:+,.2f}")
            g2.metric("تغییر ریالی", f"{li:,.0f}", delta=f"{li-fi:+,.0f}")
        else: st.info("حداقل دو رکورد لازم است.")
        st.subheader("📋 جدول دارایی‌ها")
        disp = df.copy()
        disp["تعداد"] = disp["تعداد"].apply(fmt_num)
        disp["قیمت واحد"] = disp.apply(lambda r: f"{fmt_num(r['قیمت واحد'])} {r['ارز']}" if r['قیمت واحد'] else "—", axis=1)
        disp["ارزش"] = disp.apply(lambda r: f"{fmt_num(r['ارزش'])} {r['ارز']}" if r['ارزش'] else "—", axis=1)
        disp["معادل_دلاری"] = disp["معادل_دلاری"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
        disp = disp[["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل_دلاری", "آخرین_تاریخ"]]
        disp.columns = ["دارایی", "تعداد", "قیمت واحد", "ارزش", "معادل دلاری", "آخرین بروزرسانی"]
        render_html_table(disp, dark=_dark)

# ================== صفحه افزودن دارایی ==================
elif selected == "journal":
    st.header("+ افزودن دارایی")
    all_icons = load_fa_icons()
    all_classes = [ic["class"] for ic in all_icons]
    labels_map = {ic["class"]: f'{ic["label"]} ({ic["class"]})' for ic in all_icons}
    with st.container(border=True):
        st.subheader("➕ ثبت دارایی جدید")
        with st.form("add_asset_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            name = c1.text_input("نام", placeholder="طلا، سهام...")
            cur = c2.selectbox("ارز", ["IRR", "USD"], format_func=lambda x: "ریال" if x == "IRR" else "دلار")
            init_icon = c3.selectbox("آیکون", all_classes,
                                     index=all_classes.index("fa-coins") if "fa-coins" in all_classes else 0,
                                     format_func=lambda c: labels_map.get(c, c), key="new_asset_icon")
            init_color = st.color_picker("رنگ آیکون", value="#3b82f6", key="new_asset_color")
            st.markdown("**📝 رکورد اولیه (اختیاری)**")
            c6, c7, c8 = st.columns([2, 2, 3])
            q0 = c6.number_input("تعداد", min_value=0.0, format="%.4f", step=1.0)
            p0 = c7.number_input("قیمت واحد", min_value=0.0, format="%.2f", step=1000.0)
            note0 = c8.text_input("توضیح")
            if st.form_submit_button("💾 ایجاد", use_container_width=True):
                if not name.strip(): st.error("نام را وارد کنید.")
                else:
                    aid = _short_id()
                    records = []
                    if q0 > 0 and p0 > 0:
                        records.append({"id": aid + "_r0", "date_gregorian": datetime.now().isoformat(), "date_jalali": today_jalali_str(),
                                       "quantity": q0, "unit_price": p0, "note": note0.strip() or "رکورد اولیه"})
                    data.setdefault("assets", []).append({
                        "id": aid, "name": name.strip(), "icon": init_icon, "color": init_color,
                        "overview_emoji": "", "currency": cur,
                        "created_at_gregorian": datetime.now().isoformat(), "created_at_jalali": today_jalali_str(),
                        "records": records})
                    st.session_state.data = data; save_all(data)
                    st.session_state.pending_nav = f"asset_{aid}"; st.rerun()
    if assets:
        st.subheader("📝 لیست دارایی‌ها")
        rate, _ = get_current_usd_rate(data)
        for a in assets:
            value, _, rec = compute_asset_value(a, rate)
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 3, 2, 1])
                c1.markdown(f'**<i class="fa-solid {asset_icon(a)}" style="color:{asset_color(a)};"></i> {a["name"]}**', unsafe_allow_html=True)
                c2.caption(currency_label(a["currency"]))
                c3.caption(f"آخرین: {rec['date_jalali'] if rec else '—'}")
                c4.write(f"{fmt_num(value)} {currency_label(a['currency'])}" if value else "—")
                if c5.button("🗑️", key=f"del_asset_{a['id']}"):
                    data["assets"] = [x for x in data["assets"] if x["id"] != a["id"]]
                    # 🆕 پاک‌سازی جفت‌های مصنوعی مرتبط
                    _cleanup_synthetic_pairs(data, {f"asset:{a['id']}"})
                    st.session_state.data = data; save_all(data)
                    st.session_state.pending_nav = "overview"; st.rerun()

# ================== صفحه دلار ==================
elif selected == "usd":
    st.header("💵 نرخ دلار")
    st.caption(f"📅 {today_jalali_str()}")
    with st.container(border=True):
        st.subheader("➕ ثبت نرخ")
        with st.form("usd_rate_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 3])
            new_rate = c1.number_input("نرخ (ریال)", min_value=0, step=1000, format="%d")
            note = c2.text_input("توضیح")
            if st.form_submit_button("💾 ثبت", use_container_width=True):
                if new_rate > 0:
                    now = datetime.now().isoformat()
                    data.setdefault("usd_rates", []).append({
                        "id": _short_id(), "rate": new_rate, "note": note.strip(),
                        "created_at": now, "created_at_jalali": today_jalali_str()})
                    _u, _m = sync_usd_rates_to_gold_funds(data)
                    if _u > 0: st.toast(f"🔄 {_u} رکورد صندوق طلا همگام شد", icon="✅")
                    st.session_state.data = data; save_all(data); st.rerun()
    rates = data.get("usd_rates", [])
    if rates:
        sorted_r = sorted(rates, key=lambda x: x.get("created_at", ""))
        current, current_date = get_current_usd_rate(data)
        c1, c2, c3 = st.columns(3)
        c1.metric("نرخ فعلی", f"{current:,.0f} ریال")
        c2.metric("تعداد", len(rates))
        c3.metric("آخرین", current_date or "—")
        st.subheader("📈 روند")
        chart_df = pd.DataFrame(sorted_r); chart_df["تاریخ"] = chart_df["created_at_jalali"]
        fig = px.line(chart_df, x="تاریخ", y="rate", markers=True, labels={"تاریخ": "تاریخ", "rate": "نرخ"})
        fig.update_layout(font=dict(family="Vazirmatn, Tahoma", size=13, color="#e6edf3" if _dark else "#1f2937"),
                         margin=dict(t=20, b=20),
                         paper_bgcolor="rgba(0,0,0,0)" if _dark else "white",
                         plot_bgcolor="rgba(0,0,0,0)" if _dark else "white")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 تاریخچه")
        for r in reversed(sorted_r):
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 3, 3, 1, 1])
                c1.markdown(f"**{r['rate']:,.0f} ریال**")
                c2.caption(f"📅 {r.get('created_at_jalali', '—')}")
                c3.caption(r.get("note", "—") or "—")
                c4.caption(iso_to_jalali(r.get("created_at", ""), with_time=True))
                if c5.button("✏️", key=f"edit_btn_rate_{r['id']}"):
                    st.session_state[f"edit_open_rate_{r['id']}"] = not st.session_state.get(f"edit_open_rate_{r['id']}", False)
                if c6.button("🗑️", key=f"delrate_{r['id']}"):
                    data["usd_rates"] = [x for x in data["usd_rates"] if x["id"] != r["id"]]
                    # 🆕 اگر آخرین نرخ حذف شد و دیگر نرخی نماند، جفت‌های «usd» پاک شوند
                    if not data["usd_rates"]:
                        _cleanup_synthetic_pairs(data, {"usd"})
                    _u, _m = sync_usd_rates_to_gold_funds(data)
                    if _u > 0: st.toast(f"🔄 {_u} رکورد صندوق طلا بازمحاسبه شد", icon="✅")
                    if _m > 0: st.warning(f"⚠️ {_m} رکورد صندوق طلا بدون نرخ معتبر")
                    st.session_state.data = data; save_all(data); st.rerun()
                if st.session_state.get(f"edit_open_rate_{r['id']}", False):
                    vk = f"v_rate_{r['id']}"
                    fk = f"edit_rate_{r['id']}_v{get_version(vk)}"
                    with st.form(fk):
                        ec1, ec2 = st.columns([2, 3])
                        er_date = ec1.text_input("تاریخ", value=r.get("created_at_jalali", today_jalali_str()))
                        er_rate = ec2.number_input("نرخ", value=int(r["rate"]), min_value=1, step=1000, format="%d")
                        er_note = st.text_input("توضیح", value=r.get("note", ""))
                        if st.form_submit_button("💾 ذخیره", use_container_width=True):
                            jd = parse_jalali(er_date)
                            if jd and er_rate > 0:
                                tp = r["created_at"][11:16] if len(r
