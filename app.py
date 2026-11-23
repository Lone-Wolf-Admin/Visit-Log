import calendar
import io
import re
import smtplib
from datetime import date, datetime
from email.message import EmailMessage
import pandas as pd
import streamlit as st
from fpdf import FPDF

st.set_page_config(
    page_title="Lone Wolf Field Portal",
    page_icon="🐺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

VEHICLE_CHECKLIST_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSfCzvudWQIQ1CwfNm4CFThLVaklEv3sz2JVIQ6HCjsQw0xHrw/"
    "viewform?usp=sharing&ouid=118278623880257833513"
)

# Mobile-first CSS: clears the top Streamlit banner, keeps the 7-column calendar grid on 1 row, and styles buttons
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { background: transparent !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    .block-container { padding-top: 3.5rem; padding-bottom: 3.5rem; max-width: 680px; }

    /* Force 7-column calendar rows to stay side-by-side on mobile phones instead of stacking */
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stColumn"]:nth-child(7)) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stColumn"]:nth-child(7)) > div[data-testid="stColumn"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: auto !important;
    }

    /* Calendar day buttons */
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stColumn"]:nth-child(7)) button {
        min-height: 2.6rem !important;
        padding: 0.15rem 0 !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        width: 100% !important;
    }

    /* Highlight selected calendar dates in green */
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stColumn"]:nth-child(7)) button[kind="primary"] {
        background-color: #16a34a !important;
        border-color: #15803d !important;
        color: #ffffff !important;
    }

    /* Main action buttons */
    div[data-testid="stDownloadButton"] button {
        min-height: 3.2rem;
        font-size: 1.05rem;
        font-weight: 700;
        border-radius: 10px;
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Master rate card (40 items grouped by Account -> Location -> Service, with street fragments for DMG Pro matching)
RATE_CARD = [
    {"id": "bb_mex_swp", "account": "Best Buy", "location": "Mexico", "service": "Sweeping", "rate": 30.00, "addr_keys": ["4100 e mexico"]},
    {"id": "bb_mex_qc", "account": "Best Buy", "location": "Mexico", "service": "QC", "rate": 7.00, "addr_keys": ["4100 e mexico"]},
    {"id": "bb_wad_swp", "account": "Best Buy", "location": "Wadsworth", "service": "Sweeping", "rate": 30.00, "addr_keys": ["5395 s wadsworth"]},
    {"id": "bb_wad_qc", "account": "Best Buy", "location": "Wadsworth", "service": "QC", "rate": 7.00, "addr_keys": ["5395 s wadsworth"]},
    {"id": "hr_prt", "account": "Highlands Ranch / Safeway", "location": "Highlands Ranch", "service": "Porter", "rate": 50.00, "addr_keys": ["9255 s broadway"]},
    {"id": "hr_saf_swp", "account": "Highlands Ranch / Safeway", "location": "Highlands Ranch Safeway", "service": "Sweeping", "rate": 50.00, "addr_keys": ["9255 s broadway"]},
    {"id": "ks_ark_swp", "account": "King Soopers", "location": "Arkansas", "service": "Sweeping", "rate": 40.00, "addr_keys": ["4201 e arkansas"]},
    {"id": "ks_ark_qc", "account": "King Soopers", "location": "Arkansas", "service": "QC", "rate": 7.00, "addr_keys": ["4201 e arkansas"]},
    {"id": "ks_ark_blk", "account": "King Soopers", "location": "Arkansas", "service": "Bulk Trash", "rate": 500.00, "addr_keys": ["4201 e arkansas"]},
    {"id": "ks_eva_swp", "account": "King Soopers", "location": "Evans", "service": "Sweeping", "rate": 40.00, "addr_keys": ["2727 w evans"]},
    {"id": "ks_eva_qc", "account": "King Soopers", "location": "Evans", "service": "QC", "rate": 7.00, "addr_keys": ["2727 w evans"]},
    {"id": "ks_fed_swp", "account": "King Soopers", "location": "Federal", "service": "Sweeping", "rate": 40.00, "addr_keys": ["5050 s federal"]},
    {"id": "ks_fed_qc", "account": "King Soopers", "location": "Federal", "service": "QC", "rate": 7.00, "addr_keys": ["5050 s federal"]},
    {"id": "ks_ham_qc", "account": "King Soopers", "location": "Hampden", "service": "QC", "rate": 5.00, "addr_keys": ["6470 e hampden"]},
    {"id": "ks_lee_swp", "account": "King Soopers", "location": "Leetsdale", "service": "Sweeping", "rate": 40.00, "addr_keys": ["4600 leetsdale"]},
    {"id": "ks_lee_qc", "account": "King Soopers", "location": "Leetsdale", "service": "QC", "rate": 7.00, "addr_keys": ["4600 leetsdale"]},
    {"id": "ks_lit_qc", "account": "King Soopers", "location": "Littleton", "service": "QC", "rate": 5.00, "addr_keys": ["100 w littleton"]},
    {"id": "ks_lit_prt", "account": "King Soopers", "location": "Littleton", "service": "Porter", "rate": 7.00, "addr_keys": ["100 w littleton"]},
    {"id": "ks_qui_qc", "account": "King Soopers", "location": "Quincy", "service": "QC", "rate": 5.00, "addr_keys": ["19001 e quincy"]},
    {"id": "ks_sho_prt", "account": "King Soopers", "location": "S Holly", "service": "Porter", "rate": 7.00, "addr_keys": ["6000 south holly", "6000 s holly"]},
    {"id": "ko_20m_swp", "account": "Kohl's", "location": "20 Mile", "service": "Sweeping", "rate": 35.00, "addr_keys": ["11485 s twenty mile"]},
    {"id": "ko_20m_qc", "account": "Kohl's", "location": "20 Mile", "service": "QC", "rate": 7.00, "addr_keys": ["11485 s twenty mile"]},
    {"id": "ko_cas_swp", "account": "Kohl's", "location": "Castle Rock", "service": "Sweeping", "rate": 35.00, "addr_keys": ["4800 milestone"]},
    {"id": "ko_cas_qc", "account": "Kohl's", "location": "Castle Rock", "service": "QC", "rate": 7.00, "addr_keys": ["4800 milestone"]},
    {"id": "ko_kip_swp", "account": "Kohl's", "location": "Kipling", "service": "Sweeping", "rate": 35.00, "addr_keys": ["8444 s kipling"]},
    {"id": "ko_kip_qc", "account": "Kohl's", "location": "Kipling", "service": "QC", "rate": 7.00, "addr_keys": ["8444 s kipling"]},
    {"id": "ko_que_swp", "account": "Kohl's", "location": "Quebec", "service": "Sweeping", "rate": 35.00, "addr_keys": ["8660 s quebec"]},
    {"id": "ko_que_qc", "account": "Kohl's", "location": "Quebec", "service": "QC", "rate": 7.00, "addr_keys": ["8660 s quebec"]},
    {"id": "ko_bus_trh", "account": "Kohl's", "location": "All Kohl's", "service": "Bus Trash", "rate": 15.00, "addr_keys": ["kohl"]},
    {"id": "lo_20m_swp", "account": "Lowe's", "location": "20 Mile", "service": "Sweeping", "rate": 50.00, "addr_keys": ["10000 s twenty mile"]},
    {"id": "lo_buc_swp", "account": "Lowe's", "location": "Buckley", "service": "Sweeping", "rate": 50.00, "addr_keys": ["4455 south buckley", "4455 s buckley"]},
    {"id": "lo_pea_swp", "account": "Lowe's", "location": "Peakview", "service": "Sweeping", "rate": 50.00, "addr_keys": ["9100 east peakview", "9100 e peakview"]},
    {"id": "lo_san_swp", "account": "Lowe's", "location": "Santa Fe", "service": "Sweeping", "rate": 50.00, "addr_keys": ["5095 s santa fe"]},
    {"id": "lo_whe_swp", "account": "Lowe's", "location": "Wheatlands", "service": "Sweeping", "rate": 50.00, "addr_keys": ["24505 e wheatlands"]},
    {"id": "sc_wad_swp", "account": "Sam's Club", "location": "Wadsworth", "service": "Sweeping", "rate": 50.00, "addr_keys": ["4827 s wadsworth"]},
    {"id": "wg_ara_swp", "account": "Walgreens", "location": "Arapahoe", "service": "Sweeping", "rate": 25.00, "addr_keys": ["16440 e arapahoe"]},
    {"id": "wg_bel_swp", "account": "Walgreens", "location": "Belleview", "service": "Sweeping", "rate": 25.00, "addr_keys": ["2697 w belleview"]},
    {"id": "wg_hgr_swp", "account": "Walgreens", "location": "Highlands Ranch", "service": "Sweeping", "rate": 25.00, "addr_keys": ["9390 s colorado"]},
    {"id": "wg_hgr_qc", "account": "Walgreens", "location": "Highlands Ranch", "service": "QC", "rate": 7.00, "addr_keys": ["9390 s colorado"]},
    {"id": "wg_kip_swp", "account": "Walgreens", "location": "Kipling", "service": "Sweeping", "rate": 25.00, "addr_keys": ["5870 s kipling"]},
]

# Denver Route Stops
HOME_BASE = {
    "name": "Home Base (Lakewood)",
    "address": "2345 Allison St, Lakewood, CO 80214",
    "lat": 39.7517,
    "lon": -105.0861,
}

ROUTE_STOPS = [
    {"id": "r_hr_saf", "store": "Highlands Ranch Safeway", "address": "9255 S Broadway, Highlands Ranch, CO 80129", "line": "Dual", "flex": "NO", "days": ["Mon", "Wed", "Fri"], "lat": 39.5481, "lon": -104.9877},
    {"id": "r_ks_ham", "store": "King Soopers - Hampden", "address": "6470 E Hampden Ave, Denver, CO 80222", "line": "Dual", "flex": "NO", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "lat": 39.6534, "lon": -104.9126},
    {"id": "r_ks_eva", "store": "King Soopers - Evans", "address": "2727 W Evans Ave, Denver, CO 80219", "line": "Sweep", "flex": "NO", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "lat": 39.6787, "lon": -105.0216},
    {"id": "r_ks_sho", "store": "King Soopers - S Holly", "address": "6000 S Holly St, Greenwood Village, CO 80111", "line": "Dual", "flex": "NO", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "lat": 39.6075, "lon": -104.9225},
    {"id": "r_ks_fed", "store": "King Soopers - Federal", "address": "5050 S Federal Blvd, Englewood, CO 80110", "line": "Sweep", "flex": "NO", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "lat": 39.6248, "lon": -105.0253},
    {"id": "r_ks_lee", "store": "King Soopers - Leetsdale", "address": "4600 Leetsdale Dr, Glendale, CO 80246", "line": "Sweep", "flex": "NO", "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "lat": 39.7011, "lon": -104.9336},
    {"id": "r_ks_ark", "store": "King Soopers - Arkansas (2x/wk)", "address": "4201 E Arkansas Ave, Denver, CO 80222", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.6908, "lon": -104.9383},
    {"id": "r_ks_qui", "store": "King Soopers - Quincy (1x/wk)", "address": "19001 E Quincy Ave, Aurora, CO 80015", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.6384, "lon": -104.7663},
    {"id": "r_ks_lit", "store": "King Soopers - Littleton", "address": "100 W Littleton Blvd, Littleton, CO 80120", "line": "Dual", "flex": "NO", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "lat": 39.6135, "lon": -105.0177},
    {"id": "r_bb_mex", "store": "Best Buy - Mexico", "address": "4100 E Mexico Ave Ste A, Denver, CO 80222", "line": "Sweep", "flex": "NO", "days": ["Tue", "Thu"], "lat": 39.6836, "lon": -104.9398},
    {"id": "r_bb_wad", "store": "Best Buy - Wadsworth", "address": "5395 S Wadsworth Blvd, Littleton, CO 80123", "line": "Sweep", "flex": "NO", "days": ["Tue", "Thu"], "lat": 39.6186, "lon": -105.0815},
    {"id": "r_ko_que", "store": "Kohl's 2 - Quebec (2x/wk)", "address": "8660 S Quebec St, Lone Tree, CO 80124", "line": "Dual", "flex": "Yes", "days": [], "lat": 39.5594, "lon": -104.9036},
    {"id": "r_ko_kip", "store": "Kohl's 3 - Kipling (2x/wk)", "address": "8444 S Kipling Pkwy, Littleton, CO 80127", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.5638, "lon": -105.1101},
    {"id": "r_ko_cas", "store": "Kohl's 4 - Castle Rock (2x/wk)", "address": "4800 Milestone Ln, Castle Rock, CO 80104", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.4106, "lon": -104.8814},
    {"id": "r_ko_20m", "store": "Kohl's 5 - 20 Mile (2x/wk)", "address": "11485 S Twenty Mile Rd, Parker, CO 80134", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.5082, "lon": -104.7654},
    {"id": "r_sc_wad", "store": "Sam's Club - Wadsworth (2x/wk)", "address": "4827 S Wadsworth Way, Littleton, CO 80123", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.6285, "lon": -105.0814},
    {"id": "r_wg_ara", "store": "Walgreens - Arapahoe (1x/wk)", "address": "16440 E Arapahoe Rd, Foxfield, CO 80016", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.5955, "lon": -104.7963},
    {"id": "r_wg_kip", "store": "Walgreens - Kipling (1x/wk)", "address": "5870 S Kipling Pkwy, Littleton, CO 80127", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.6104, "lon": -105.1099},
    {"id": "r_wg_hgr", "store": "Walgreens - Highlands Ranch (2x/wk)", "address": "9390 S Colorado Blvd, Highlands Ranch, CO 80126", "line": "Dual", "flex": "Yes", "days": [], "lat": 39.5461, "lon": -104.9432},
    {"id": "r_wg_bel", "store": "Walgreens - Belleview (1x/wk)", "address": "2697 W Belleview Ave, Littleton, CO 80123", "line": "Sweep", "flex": "Yes", "days": [], "lat": 39.6238, "lon": -105.0209},
    {"id": "r_lo_pea", "store": "Lowe's - Peakview (Mon + 1 Flex)", "address": "9100 E Peakview Ave, Greenwood Village, CO 80111", "line": "Sweep", "flex": "Mon + Wed-Fri", "days": ["Mon"], "lat": 39.5979, "lon": -104.8825},
    {"id": "r_lo_san", "store": "Lowe's - Santa Fe (Mon + 1 Flex)", "address": "5095 S Santa Fe Dr, Littleton, CO 80120", "line": "Sweep", "flex": "Mon + Wed-Fri", "days": ["Mon"], "lat": 39.6244, "lon": -105.0232},
    {"id": "r_lo_buc", "store": "Lowe's - Buckley (Mon + 1 Flex)", "address": "4455 S Buckley Rd, Aurora, CO 80015", "line": "Sweep", "flex": "Mon + Wed-Fri", "days": ["Mon"], "lat": 39.6355, "lon": -104.7915},
    {"id": "r_lo_20m", "store": "Lowe's - 20 Mile (Mon + 1 Flex)", "address": "10000 S Twenty Mile Rd, Parker, CO 80134", "line": "Sweep", "flex": "Mon + Wed-Fri", "days": ["Mon"], "lat": 39.5342, "lon": -104.7652},
    {"id": "r_lo_whe", "store": "Lowe's - Wheatlands (Mon + 1 Flex)", "address": "24505 E Wheatlands Pkwy, Aurora, CO 80016", "line": "Sweep", "flex": "Mon + Wed-Fri", "days": ["Mon"], "lat": 39.5919, "lon": -104.7024},
]

# Site Directory Notes (Customize gate codes, water hookups, and noise curfews per store ID)
EMERGENCY_CONTACTS = [
    {"role": "Lone Wolf Dispatch / Operations", "contact": "Check team thread or email dispatch"},
    {"role": "DMG Pro Support (Work Orders)", "contact": "Log check-in/out inside DMG Pro app before leaving lot"},
    {"role": "Non-Emergency Police (Denver Metro)", "contact": "Denver: (720) 913-2000 | Aurora: (303) 627-3100 | Arapahoe/Douglas: (303) 795-4711"},
]

SITE_NOTES = {
    "r_ks_ark": {
        "gate": "Open lot — check rear dock & perimeter for bulk dumping",
        "water": "Standard tank fill at HQ before departure",
        "curfew": "Watch residential border on east side; keep blower idle down near homes",
    },
    "r_ks_lee": {
        "gate": "7-day/wk high-traffic lot — sweep after midnight close",
        "water": "Fill at HQ",
        "curfew": "High pedestrian/late-night traffic; run amber strobes",
    },
    "r_lo_pea": {
        "gate": "Pro canopy & garden center perimeter — watch for pallet stacks",
        "water": "Fill at HQ",
        "curfew": "Mandatory Monday + 1 Flex (Wed–Fri); check lumber aisle apron",
    },
    "r_lo_san": {
        "gate": "Check south lumber gate & rear receiving lane",
        "water": "Fill at HQ",
        "curfew": "Mandatory Monday + 1 Flex (Wed–Fri)",
    },
    "r_lo_buc": {
        "gate": "Check rear dock & garden center curb line",
        "water": "Fill at HQ",
        "curfew": "Mandatory Monday + 1 Flex (Wed–Fri)",
    },
    "r_lo_20m": {
        "gate": "Check rear loading dock & contractor parking",
        "water": "Fill at HQ",
        "curfew": "Mandatory Monday + 1 Flex (Wed–Fri)",
    },
    "r_lo_whe": {
        "gate": "Open perimeter — watch windblown debris along east fence",
        "water": "Fill at HQ",
        "curfew": "Mandatory Monday + 1 Flex (Wed–Fri)",
    },
}

# --- SESSION STATE INITIALIZATION ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "confirm_leave_log" not in st.session_state:
    st.session_state.confirm_leave_log = False
if "log_submitted" not in st.session_state:
    st.session_state.log_submitted = False

if "visits" not in st.session_state or not isinstance(st.session_state.visits, dict):
    st.session_state.visits = {}
for row in RATE_CARD:
    st.session_state.visits.setdefault(row["id"], [])

if "open_account" not in st.session_state:
    st.session_state.open_account = None
if "open_calendar" not in st.session_state:
    st.session_state.open_calendar = None
if "extra_items" not in st.session_state:
    st.session_state.extra_items = []
if "extra_temp_days" not in st.session_state:
    st.session_state.extra_temp_days = []


def navigate_to(page_name: str):
    st.session_state.current_page = page_name
    st.session_state.confirm_leave_log = False
    st.rerun()


def reset_visit_log_data():
    for row in RATE_CARD:
        st.session_state.visits[row["id"]] = []
    st.session_state.extra_items = []
    st.session_state.extra_temp_days = []
    st.session_state.open_account = None
    st.session_state.open_calendar = None
    st.session_state.log_submitted = False
    st.session_state.confirm_leave_log = False


def render_calendar_picker(selected_days: list[int], year: int, month_num: int, key_prefix: str) -> list[int]:
    """Renders a 7-column Sun-Sat calendar grid where tapping a day toggles it on/off and stays open."""
    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month_num)
    updated = set(selected_days)

    hdr_cols = st.columns(7)
    for i, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
        hdr_cols[i].markdown(
            f"<div style='text-align:center; font-size:0.75rem; font-weight:700; color:#64748b;'>{day_name}</div>",
            unsafe_allow_html=True,
        )

    for week in weeks:
        cols = st.columns(7)
        for d_idx, day_num in enumerate(week):
            with cols[d_idx]:
                if day_num == 0:
                    st.markdown("<div style='height:2.6rem;'></div>", unsafe_allow_html=True)
                else:
                    is_selected = day_num in updated
                    label = f"✓{day_num}" if is_selected else str(day_num)
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(label, key=f"{key_prefix}_d{day_num}", type=btn_type):
                        if is_selected:
                            updated.remove(day_num)
                        else:
                            updated.add(day_num)
                        return sorted(updated)

    return sorted(updated)


def build_summary_df() -> pd.DataFrame:
    rows = []
    for item in RATE_CARD:
        days = sorted(st.session_state.visits.get(item["id"], []))
        qty = len(days)
        rows.append(
            {
                "Account": item["account"],
                "Store": f"{item['account']} - {item['location']}",
                "Line Item": f"{item['account']} - {item['location']} - {item['service']}",
                "Visits": qty,
                "Rate": item["rate"],
                "Amount": round(qty * item["rate"], 2),
                "Dates Visited": ", ".join(str(d) for d in days),
            }
        )
    for extra in st.session_state.extra_items:
        days = sorted(extra.get("days", []))
        qty = len(days)
        rows.append(
            {
                "Account": "Extra / One-Off",
                "Store": extra["name"],
                "Line Item": extra["name"],
                "Visits": qty,
                "Rate": extra["rate"],
                "Amount": round(qty * extra["rate"], 2),
                "Dates Visited": ", ".join(str(d) for d in days),
            }
        )
    return pd.DataFrame(rows)


def generate_invoice_pdf(df: pd.DataFrame, billing_month: str, invoice_num: str, tech_name: str = "") -> bytes:
    active_df = df[df["Visits"] > 0].copy()
    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(30, 41, 59)
    pdf.rect(10, 10, 196, 22, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(14, 14)
    header_title = f"{tech_name.strip().upper()} - MONTHLY VISIT LOG" if tech_name.strip() else "MONTHLY VISIT LOG"
    pdf.cell(135, 7, header_title[:42])
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(14, 22)
    pdf.cell(135, 6, f"Bill To: Lone Wolf Parking Lot Services LLC  |  Period: {billing_month}")
    pdf.set_xy(150, 16)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(50, 8, f"Invoice #{invoice_num}", align="R")

    total_visits = int(active_df["Visits"].sum()) if not active_df.empty else 0
    total_amount = float(active_df["Amount"].sum()) if not active_df.empty else 0.0

    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(10, 36)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(98, 8, f"Total Verified Visits: {total_visits}", border=1)
    pdf.cell(98, 8, f"Total Invoice Amount: ${total_amount:,.2f}", border=1, align="R")

    pdf.set_xy(10, 48)
    pdf.set_fill_color(15, 76, 129)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    col_w = [68, 14, 20, 24, 70]
    headers = ["Service Line Item", "Visits", "Rate", "Amount", "Days Visited"]
    for w, h in zip(col_w, headers):
        align = "R" if h in ("Visits", "Rate", "Amount") else "L"
        pdf.cell(w, 8, h, border=1, fill=True, align=align)
    pdf.ln()

    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 8.5)
    fill = False
    for _, r in active_df.iterrows():
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        dates_str = r["Dates Visited"] if len(r["Dates Visited"]) <= 44 else r["Dates Visited"][:41] + "..."
        pdf.cell(col_w[0], 7, r["Line Item"][:38], border=1, fill=True)
        pdf.cell(col_w[1], 7, str(int(r["Visits"])), border=1, fill=True, align="R")
        pdf.cell(col_w[2], 7, f"${r['Rate']:,.2f}", border=1, fill=True, align="R")
        pdf.cell(col_w[3], 7, f"${r['Amount']:,.2f}", border=1, fill=True, align="R")
        pdf.cell(col_w[4], 7, dates_str, border=1, fill=True)
        pdf.ln()
        fill = not fill

    pdf.set_fill_color(226, 232, 240)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(col_w[0], 8, "TOTAL", border=1, fill=True, align="R")
    pdf.cell(col_w[1], 8, str(total_visits), border=1, fill=True, align="R")
    pdf.cell(col_w[2], 8, "", border=1, fill=True)
    pdf.cell(col_w[3], 8, f"${total_amount:,.2f}", border=1, fill=True, align="R")
    pdf.cell(col_w[4], 8, "Attach to Novo Invoice", border=1, fill=True)

    return bytes(pdf.output())


def generate_hazard_pdf(
    tech_name: str,
    store_name: str,
    store_address: str,
    timestamp_str: str,
    issues: list[str],
    severity: str,
    details: str,
    photo_bytes: bytes | None = None,
    photo_ext: str = "jpg",
) -> bytes:
    """Generates a timestamped Lot Hazard / Illegal Dumping PDF with optional embedded photo."""
    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(153, 27, 27)
    pdf.rect(10, 10, 196, 22, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(14, 14)
    pdf.cell(188, 7, "LONE WOLF - LOT HAZARD & ACCESS EXCEPTION REPORT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(14, 22)
    pdf.cell(188, 6, f"Reported: {timestamp_str}  |  Tech: {tech_name.strip() or 'Field Tech'}")

    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(10, 38)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(196, 7, f"Location: {store_name}")
    pdf.ln()
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(196, 6, f"Address: {store_address}")
    pdf.ln()
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(196, 7, f"Priority / Impact: {severity}")
    pdf.ln(9)

    pdf.set_x(10)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(196, 7, "Reported Issues:", border=1, fill=True)
    pdf.ln()
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(196, 6, ", ".join(issues) if issues else "General Site Exception", border=1)
    pdf.ln(3)

    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(196, 7, "Field Notes / Description:", border=1, fill=True)
    pdf.ln()
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(196, 6, details.strip() if details.strip() else "No additional notes provided.", border=1)

    if photo_bytes:
        pdf.ln(5)
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(196, 7, "Photographic Proof Attached:")
        pdf.ln(8)
        try:
            img_stream = io.BytesIO(photo_bytes)
            fmt = "PNG" if photo_ext.lower() == "png" else "JPEG"
            pdf.image(img_stream, x=15, w=130, type=fmt)
        except Exception:
            pdf.set_x(10)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(196, 6, "(Photo attached separately to email)")

    return bytes(pdf.output())


def send_completion_email(
    pdf_bytes: bytes,
    billing_month: str,
    invoice_num: str,
    total_visits: int,
    total_amount: float,
    tech_name: str = "",
    tech_copy_email: str = "",
):
    smtp_host = st.secrets["email"]["smtp_host"]
    smtp_port = int(st.secrets["email"]["smtp_port"])
    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    recipient = st.secrets["email"]["recipient_email"]

    recipients = [recipient]
    if tech_copy_email and tech_copy_email.strip() and tech_copy_email.strip().lower() != recipient.lower():
        recipients.append(tech_copy_email.strip())

    sender_label = tech_name.strip() if tech_name.strip() else "Tech"

    msg = EmailMessage()
    msg["Subject"] = f"Monthly Visit Log Ready ({sender_label}) — {billing_month} (Inv #{invoice_num} | ${total_amount:,.2f})"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        f"Hi Team,\n\n"
        f"{sender_label} has completed the monthly visit log for {billing_month}.\n\n"
        f"- Tech / Vendor: {sender_label}\n"
        f"- Invoice #: {invoice_num}\n"
        f"- Total Verified Visits: {total_visits}\n"
        f"- Total Invoice Amount: ${total_amount:,.2f}\n\n"
        f"The clean PDF visit log is attached to this email for your records, attach a copy to your invoice and bill the total as shown on this document. All payments require valid proof of service and may not be paid if proof is not rendered.\n"
    )
    filename = f"Monthly_Visit_Log_{billing_month.replace(' ', '_')}_Inv_{invoice_num}.pdf"
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.send_message(msg)


def send_insurance_email(
    pdf_bytes: bytes,
    pdf_filename: str,
    tech_name: str,
    company_name: str,
    policy_type: str,
    carrier_name: str,
    policy_number: str,
    expiration_date: str,
    coverage_limit: str,
    notes: str = "",
    tech_copy_email: str = "",
):
    smtp_host = st.secrets["email"]["smtp_host"]
    smtp_port = int(st.secrets["email"]["smtp_port"])
    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    recipient = st.secrets["email"]["recipient_email"]

    recipients = [recipient]
    if tech_copy_email and tech_copy_email.strip() and tech_copy_email.strip().lower() != recipient.lower():
        recipients.append(tech_copy_email.strip())

    entity_label = company_name.strip() if company_name.strip() else tech_name.strip()

    msg = EmailMessage()
    msg["Subject"] = f"Insurance Policy / COI Uploaded — {entity_label} ({policy_type} | Exp: {expiration_date})"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        f"Hi Team,\n\n"
        f"A new Insurance Policy / Certificate of Insurance (COI) has been submitted via the Lone Wolf Field Portal.\n\n"
        f"- Tech / Contact Name: {tech_name.strip()}\n"
        f"- Business / LLC Name: {company_name.strip() or 'N/A'}\n"
        f"- Policy Type: {policy_type}\n"
        f"- Insurance Carrier: {carrier_name.strip()}\n"
        f"- Policy Number: {policy_number.strip()}\n"
        f"- Expiration Date: {expiration_date}\n"
        f"- Coverage Limit: {coverage_limit.strip() or 'See attached PDF'}\n"
        f"- Notes: {notes.strip() or 'None'}\n\n"
        f"The uploaded PDF policy document ({pdf_filename}) is attached to this email.\n"
    )
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_filename)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.send_message(msg)


def send_hazard_email(
    pdf_bytes: bytes,
    tech_name: str,
    store_name: str,
    store_address: str,
    timestamp_str: str,
    issues: list[str],
    severity: str,
    details: str,
    photo_bytes: bytes | None = None,
    photo_filename: str = "hazard_photo.jpg",
):
    smtp_host = st.secrets["email"]["smtp_host"]
    smtp_port = int(st.secrets["email"]["smtp_port"])
    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    recipient = st.secrets["email"]["recipient_email"]

    msg = EmailMessage()
    msg["Subject"] = f"LOT HAZARD / ACCESS REPORT — {store_name} ({severity})"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Hi Team,\n\n"
        f"A Lot Hazard / Access Exception Report was submitted from the field.\n\n"
        f"- Tech: {tech_name.strip() or 'Field Tech'}\n"
        f"- Time: {timestamp_str}\n"
        f"- Store: {store_name}\n"
        f"- Address: {store_address}\n"
        f"- Impact / Priority: {severity}\n"
        f"- Issues: {', '.join(issues)}\n"
        f"- Details: {details.strip() or 'None'}\n\n"
        f"A timestamped PDF report (and original photo, if captured) is attached.\n"
    )
    safe_store = re.sub(r"[^A-Za-z0-9]+", "_", store_name)[:28]
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=f"Hazard_Report_{safe_store}.pdf")

    if photo_bytes:
        subtype = "png" if photo_filename.lower().endswith(".png") else "jpeg"
        msg.add_attachment(photo_bytes, maintype="image", subtype=subtype, filename=photo_filename)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.send_message(msg)


def send_maintenance_email(
    tech_name: str,
    unit_num: str,
    log_date: str,
    log_types: list[str],
    odometer_hrs: str,
    fuel_gallons: float,
    fuel_cost: float,
    dump_location: str,
    dump_load: str,
    repair_items: list[str],
    notes: str,
    attachment_bytes: bytes | None = None,
    attachment_name: str = "",
):
    smtp_host = st.secrets["email"]["smtp_host"]
    smtp_port = int(st.secrets["email"]["smtp_port"])
    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    recipient = st.secrets["email"]["recipient_email"]

    summary_tag = ", ".join(log_types) if log_types else "Shift Log"
    msg = EmailMessage()
    msg["Subject"] = f"Fleet / Hopper / Fuel Log — {unit_num} ({summary_tag} | {log_date})"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Hi Team,\n\n"
        f"A new Fleet, Fuel & Hopper Dump Log has been submitted.\n\n"
        f"- Tech / Driver: {tech_name.strip()}\n"
        f"- Truck / Unit #: {unit_num.strip()}\n"
        f"- Date: {log_date}\n"
        f"- Odometer / Aux Hours: {odometer_hrs.strip() or 'N/A'}\n"
        f"- Log Categories: {summary_tag}\n\n"
        f"--- FUEL ---\n"
        f"- Gallons: {fuel_gallons:.2f} gal\n"
        f"- Total Cost: ${fuel_cost:,.2f}\n\n"
        f"--- HOPPER DUMP ---\n"
        f"- Dump Site / Facility: {dump_location.strip() or 'N/A'}\n"
        f"- Estimated Load: {dump_load}\n\n"
        f"--- PARTS / MAINTENANCE NEEDED ---\n"
        f"- Flagged Items: {', '.join(repair_items) if repair_items else 'None'}\n"
        f"- Notes / Details: {notes.strip() or 'None'}\n"
    )

    if attachment_bytes and attachment_name:
        lower = attachment_name.lower()
        if lower.endswith(".pdf"):
            msg.add_attachment(attachment_bytes, maintype="application", subtype="pdf", filename=attachment_name)
        elif lower.endswith(".png"):
            msg.add_attachment(attachment_bytes, maintype="image", subtype="png", filename=attachment_name)
        else:
            msg.add_attachment(attachment_bytes, maintype="image", subtype="jpeg", filename=attachment_name)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.send_message(msg)


def order_stops_nearest_neighbor(stops: list[dict], round_trip: bool = True) -> list[dict]:
    """Orders selected stops starting from Home Base (Lakewood) using nearest-neighbor routing."""
    remaining = stops.copy()
    ordered = []
    curr_lat, curr_lon = HOME_BASE["lat"], HOME_BASE["lon"]

    while remaining:
        nearest = min(
            remaining,
            key=lambda s: (s["lat"] - curr_lat) ** 2 + (s["lon"] - curr_lon) ** 2,
        )
        ordered.append(nearest)
        curr_lat, curr_lon = nearest["lat"], nearest["lon"]
        remaining.remove(nearest)

    return ordered


# ==============================================================================
# PAGE 1: LANDING / HUB PAGE
# ==============================================================================
def render_home_page():
    st.title("🐺 Lone Wolf Field Portal")
    st.caption("Select a tool below to get started.")

    summary_df = build_summary_df()
    active_visits = int(summary_df["Visits"].sum())
    active_amt = float(summary_df["Amount"].sum())

    # Card 1: Monthly Visit Log
    with st.container(border=True):
        st.subheader("🧹 Monthly Visit Log")
        st.write("Log store visits by calendar date, export your Novo-ready PDF, and email your completed report.")
        if active_visits > 0 and not st.session_state.log_submitted:
            st.warning(f"In-progress draft: **{active_visits} visits (${active_amt:,.2f})** not yet submitted.")
        if st.button("Open Monthly Visit Log →", type="primary", use_container_width=True):
            navigate_to("visit_log")

    # Card 2: Route Optimizer
    with st.container(border=True):
        st.subheader("🗺️ Denver Route Optimizer")
        st.write("Build your daily sweep & porter route from Lakewood HQ, copy the address list, and launch RouteXL.com.")
        if st.button("Open Route Optimizer →", type="primary", use_container_width=True):
            navigate_to("route_optimizer")

    # Card 3: Vehicle & Equipment Checklist (Logs straight to existing Google Form)
    with st.container(border=True):
        st.subheader("🚚 Vehicle & Equipment Checklist")
        st.write("Complete your pre-trip / post-trip vehicle & sweeper inspection and log it directly to the team sheet.")
        st.link_button("Open Vehicle Checklist →", VEHICLE_CHECKLIST_URL, type="primary", use_container_width=True)

    # Card 4: Insurance Policy & COI Upload
    with st.container(border=True):
        st.subheader("🛡️ Insurance Policy & COI Upload")
        st.write("Submit your policy details, drop a copy of your insurance PDF, and email it directly to the team.")
        if st.button("Upload Insurance Policy →", type="primary", use_container_width=True):
            navigate_to("insurance_upload")

    # Card 5: Lot Hazard & Illegal Dumping Report (#1)
    with st.container(border=True):
        st.subheader("🚨 Lot Hazard & Dumping Report")
        st.write("Snap a photo of blocked lots, illegal bulk dumping, or site damage and email timestamped proof.")
        if st.button("Report Lot Hazard / Dumping →", type="primary", use_container_width=True):
            navigate_to("hazard_report")

    # Card 6: Hopper Dump, Fuel & Maintenance Log (#2)
    with st.container(border=True):
        st.subheader("⛽ Hopper Dump, Fuel & Maintenance")
        st.write("Log fuel receipts, hopper dump loads, and sweeper broom/hydraulic repair requests.")
        if st.button("Open Fleet & Fuel Log →", type="primary", use_container_width=True):
            navigate_to("maintenance_log")

    # Card 7: Site Notes, Gate Codes & Contacts Directory (#5)
    with st.container(border=True):
        st.subheader("🔑 Site Notes, Gate Codes & Contacts")
        st.write("Quick lookup for store addresses, service schedules, gate/water notes, and emergency contacts.")
        if st.button("Open Site Directory →", type="primary", use_container_width=True):
            navigate_to("site_directory")

    # Card 8: Placeholder for Upcoming Pages
    with st.container(border=True):
        st.subheader("🧰 More Tools Coming Soon")
        st.caption("DMG Pro Cross-Reference Audit and Snow / L&L Logs will live right here.")


# ==============================================================================
# PAGE 2: MONTHLY VISIT LOG (WITH UNSAVED DATA PROTECTION)
# ==============================================================================
def render_visit_log_page():
    summary_df = build_summary_df()
    tot_visits = int(summary_df["Visits"].sum())
    tot_amt = float(summary_df["Amount"].sum())
    has_unsaved = (tot_visits > 0) and (not st.session_state.log_submitted)

    nav_col1, _ = st.columns([1.4, 2.6])
    with nav_col1:
        if st.button("← Back to Home", key="top_back_log", use_container_width=True):
            if has_unsaved:
                st.session_state.confirm_leave_log = True
                st.rerun()
            else:
                navigate_to("home")

    if st.session_state.confirm_leave_log and has_unsaved:
        with st.container(border=True):
            st.error(
                f"⚠️ **Data Will Be Lost if Not Submitted!**  \n"
                f"You currently have **{tot_visits} visit(s) (${tot_amt:,.2f})** entered that have not been emailed yet. "
                f"Please scroll down and tap **Email Completed Log to Team** first, or confirm below if you want to discard and return Home."
            )
            w_col1, w_col2 = st.columns(2)
            with w_col1:
                if st.button("Stay & Submit First", type="primary", use_container_width=True):
                    st.session_state.confirm_leave_log = False
                    st.rerun()
            with w_col2:
                if st.button("Discard & Go Home", type="secondary", use_container_width=True):
                    reset_visit_log_data()
                    navigate_to("home")

    st.title("🧹 Monthly Visit Log")
    st.caption("Open a store group below, tap 'Tap to pick dates', select your days, then tap OK.")

    tech_name = st.text_input("Tech / Company Name (Optional)", value="", placeholder="Enter your name or company")

    now = datetime.now()
    prev_year = now.year - 1 if now.month == 1 else now.year
    prev_month = 12 if now.month == 1 else now.month - 1

    period_options = [
        (now.year, now.month, f"{calendar.month_name[now.month]} {now.year}"),
        (prev_year, prev_month, f"{calendar.month_name[prev_month]} {prev_year}"),
    ]

    col_p, col_i = st.columns([2.3, 1.3])
    with col_p:
        selected_period = st.selectbox(
            "Billing Period",
            options=period_options,
            format_func=lambda x: x[2],
            index=0,
        )
    with col_i:
        invoice_num = st.text_input("Invoice #", value="0026")

    selected_year, selected_month_num, billing_month = selected_period

    k1, k2 = st.columns(2)
    k1.metric("Total Visits Logged", f"{tot_visits}")
    k2.metric("Total Invoice Amount", f"${tot_amt:,.2f}")

    st.divider()

    st.subheader("1. Select Dates Visited")
    accounts = [
        "King Soopers",
        "Lowe's",
        "Kohl's",
        "Best Buy",
        "Highlands Ranch / Safeway",
        "Sam's Club",
        "Walgreens",
    ]

    for acct in accounts:
        acct_items = [x for x in RATE_CARD if x["account"] == acct]
        acct_visits = sum(len(st.session_state.visits.get(x["id"], [])) for x in acct_items)
        acct_dollars = sum(len(st.session_state.visits.get(x["id"], [])) * x["rate"] for x in acct_items)
        badge = f" — ✅ {acct_visits} visits (${acct_dollars:,.0f})" if acct_visits > 0 else ""

        is_acct_open = (st.session_state.open_account == acct) or any(
            st.session_state.open_calendar == x["id"] for x in acct_items
        )

        with st.expander(f"{acct}{badge}", expanded=is_acct_open):
            for item in acct_items:
                current_days = st.session_state.visits.get(item["id"], [])
                is_cal_open = st.session_state.open_calendar == item["id"]

                if current_days:
                    days_preview = ", ".join(str(d) for d in current_days)
                    st.markdown(
                        f"**{item['location']} — {item['service']}** (${item['rate']:.0f}/visit)  \n"
                        f"Selected ({len(current_days)}): `{days_preview}`"
                    )
                else:
                    st.markdown(f"**{item['location']} — {item['service']}** (${item['rate']:.0f}/visit)")

                if not is_cal_open:
                    if st.button("📅 Tap to pick dates", key=f"open_{item['id']}", use_container_width=True):
                        st.session_state.open_account = acct
                        st.session_state.open_calendar = item["id"]
                        st.rerun()
                else:
                    with st.container(border=True):
                        new_days = render_calendar_picker(
                            selected_days=current_days,
                            year=selected_year,
                            month_num=selected_month_num,
                            key_prefix=item["id"],
                        )
                        if new_days != current_days:
                            st.session_state.visits[item["id"]] = new_days
                            st.session_state.log_submitted = False
                            st.rerun()

                        if st.button("✅ OK", key=f"ok_{item['id']}", type="primary", use_container_width=True):
                            st.session_state.open_account = acct
                            st.session_state.open_calendar = None
                            st.rerun()

                st.markdown("<hr style='margin:0.5rem 0; border-color:#e2e8f0;'>", unsafe_allow_html=True)

            if st.button(f"Done with {acct} ▲", key=f"done_{acct}", use_container_width=True):
                st.session_state.open_account = None
                st.session_state.open_calendar = None
                st.rerun()

    with st.expander(
        "➕ Add One-Off Job (e.g., Bulk Trash)",
        expanded=(st.session_state.open_account == "extra_job" or st.session_state.open_calendar == "extra_job"),
    ):
        ex_name = st.text_input("Job Description", placeholder="e.g., Arkansas Bulk Trash")
        ex_rate = st.number_input("Price per Visit ($)", min_value=0.0, value=500.0, step=25.0)

        if st.session_state.extra_temp_days:
            st.caption(f"Selected days: {', '.join(str(d) for d in st.session_state.extra_temp_days)}")

        if st.session_state.open_calendar != "extra_job":
            if st.button("📅 Tap to pick dates", key="open_extra_job", use_container_width=True):
                st.session_state.open_account = "extra_job"
                st.session_state.open_calendar = "extra_job"
                st.rerun()
        else:
            with st.container(border=True):
                new_ex_days = render_calendar_picker(
                    selected_days=st.session_state.extra_temp_days,
                    year=selected_year,
                    month_num=selected_month_num,
                    key_prefix="extra_job",
                )
                if new_ex_days != st.session_state.extra_temp_days:
                    st.session_state.extra_temp_days = new_ex_days
                    st.rerun()

                if st.button("✅ OK", key="ok_extra_job", type="primary", use_container_width=True):
                    st.session_state.open_calendar = None
                    st.rerun()

        if st.button("Add One-Off Job to Log", use_container_width=True):
            if ex_name and st.session_state.extra_temp_days:
                st.session_state.extra_items.append(
                    {"name": ex_name, "rate": ex_rate, "days": st.session_state.extra_temp_days}
                )
                st.session_state.extra_temp_days = []
                st.session_state.open_calendar = None
                st.session_state.open_account = None
                st.session_state.log_submitted = False
                st.rerun()
            else:
                st.warning("Enter a job description and tap at least one date on the calendar.")

        if st.session_state.extra_items:
            st.markdown("**Added One-Off Jobs:**")
            for idx, extra in enumerate(st.session_state.extra_items):
                c1, c2 = st.columns([4, 1])
                c1.write(f"• {extra['name']} — {len(extra['days'])} visit(s) @ ${extra['rate']:,.2f}")
                if c2.button("🗑️", key=f"del_extra_{idx}"):
                    st.session_state.extra_items.pop(idx)
                    st.session_state.log_submitted = False
                    st.rerun()

    st.divider()

    st.subheader("2. Download PDF & Email Completed Log")
    active_preview = summary_df[summary_df["Visits"] > 0][["Line Item", "Visits", "Amount", "Dates Visited"]]

    if active_preview.empty:
        st.info("No visits selected yet. Open any store group above and tap 'Tap to pick dates'.")
    else:
        st.dataframe(active_preview, use_container_width=True, hide_index=True)

        pdf_bytes = generate_invoice_pdf(summary_df, billing_month, invoice_num, tech_name=tech_name)
        pdf_filename = f"Monthly_Visit_Log_{billing_month.replace(' ', '_')}_Inv_{invoice_num}.pdf"

        st.download_button(
            label="📄 1. Download PDF to Attach in Novo",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            type="secondary",
        )

        tech_copy_email = st.text_input(
            "Send a PDF copy to yourself (optional — for uploading to Novo):",
            value="",
            placeholder="your.email@gmail.com",
            help="Leave blank if you only want to send to the Team email.",
        )

        if st.button("📧 2. Email Completed Log to Team", type="primary", use_container_width=True):
            try:
                send_completion_email(
                    pdf_bytes,
                    billing_month,
                    invoice_num,
                    tot_visits,
                    tot_amt,
                    tech_name=tech_name,
                    tech_copy_email=tech_copy_email,
                )
                st.session_state.log_submitted = True
                st.session_state.confirm_leave_log = False
                if tech_copy_email.strip():
                    st.success(
                        f"Sent! Completed {billing_month} PDF log (${tot_amt:,.2f} across {tot_visits} visits) "
                        f"emailed to Team and {tech_copy_email.strip()}. You can now safely return Home."
                    )
                else:
                    st.success(
                        f"Sent! Completed {billing_month} PDF log (${tot_amt:,.2f} across {tot_visits} visits) "
                        f"emailed to Team. You can now safely return Home."
                    )
            except Exception as e:
                st.error(f"Could not send email — check Streamlit Secrets email settings. Details: {e}")

    st.divider()
    if st.button("← Back to Home", key="bottom_back_log", use_container_width=True):
        if has_unsaved:
            st.session_state.confirm_leave_log = True
            st.rerun()
        else:
            navigate_to("home")


# ==============================================================================
# PAGE 3: DENVER ROUTE OPTIMIZER
# ==============================================================================
def render_route_optimizer_page():
    if st.button("← Back to Home", key="top_back_route"):
        navigate_to("home")

    st.title("🗺️ Denver Route Optimizer")
    st.caption(f"Starts & ends at **{HOME_BASE['address']}**")

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    today_short = day_names[datetime.now().weekday()]

    col_d, col_rt = st.columns([2, 1.5])
    with col_d:
        selected_day = st.selectbox("Route Day", options=day_names, index=day_names.index(today_short))
    with col_rt:
        st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)
        round_trip = st.checkbox("Return to Lakewood", value=True)

    scheduled_stops = [s for s in ROUTE_STOPS if selected_day in s["days"]]
    flex_stops = [s for s in ROUTE_STOPS if selected_day not in s["days"]]

    st.subheader(f"1. Commonly Scheduled Stops for {selected_day} ({len(scheduled_stops)})")
    selected_stop_ids = []
    if scheduled_stops:
        for s in scheduled_stops:
            if st.checkbox(f"**{s['store']}** ({s['line']}) — {s['address']}", value=True, key=f"sch_{s['id']}"):
                selected_stop_ids.append(s["id"])
    else:
        st.info(f"Only King Soopers Leetsdale is commonly scheduled on {selected_day}s. Add flexible or other stops below.")

    with st.expander(f"➕ Add Flexible / Optional Stops ({len(flex_stops)} available)", expanded=(selected_day in ["Wed", "Thu", "Fri", "Sat"])):
        for s in flex_stops:
            if st.checkbox(f"**{s['store']}** ({s['line']}) — {s['address']}", value=False, key=f"flx_{s['id']}"):
                selected_stop_ids.append(s["id"])

    chosen_stops = [s for s in ROUTE_STOPS if s["id"] in selected_stop_ids]

    st.divider()
    st.subheader(f"2. Optimized Stop Sequence ({len(chosen_stops)} stops)")

    if not chosen_stops:
        st.warning("Select at least one stop above to build your route.")
    else:
        ordered = order_stops_nearest_neighbor(chosen_stops, round_trip=round_trip)

        route_rows = [{"Stop #": "Start", "Location": HOME_BASE["name"], "Service": "-", "Address": HOME_BASE["address"]}]
        for idx, s in enumerate(ordered, start=1):
            route_rows.append(
                {
                    "Stop #": f"#{idx}",
                    "Location": s["store"],
                    "Service": s["line"],
                    "Address": s["address"],
                }
            )
        if round_trip:
            route_rows.append({"Stop #": "End", "Location": HOME_BASE["name"], "Service": "-", "Address": HOME_BASE["address"]})

        st.dataframe(pd.DataFrame(route_rows), use_container_width=True, hide_index=True)

        address_lines = [HOME_BASE["address"]] + [s["address"] for s in ordered]
        if round_trip:
            address_lines.append(HOME_BASE["address"])
        address_list_text = "\n".join(address_lines)

        st.markdown("**📋 Copy Selected Address List (for RouteXL.com):**")
        st.caption("Tap the copy icon in the top-right corner of the address box below, then tap **Launch RouteXL.com** and paste.")
        st.code(address_list_text, language="text")

        c_copy, c_launch = st.columns(2)
        with c_copy:
            if st.button("📋 Copy selected address list", use_container_width=True):
                st.toast("Tap the copy icon in the top-right corner of the address box above, then paste into RouteXL.com!")
                st.info(f"Address list ready ({len(ordered)} stops) — tap the copy icon in the top-right corner of the box above.")
        with c_launch:
            st.link_button("🚀 Launch RouteXL.com", "https://www.routexl.com", type="primary", use_container_width=True)

    st.divider()
    if st.button("← Back to Home", key="bottom_back_route", use_container_width=True):
        navigate_to("home")


# ==============================================================================
# PAGE 4: INSURANCE POLICY & COI UPLOAD
# ==============================================================================
def render_insurance_upload_page():
    if st.button("← Back to Home", key="top_back_ins"):
        navigate_to("home")

    st.title("🛡️ Insurance Policy & COI Upload")
    st.caption("Fill out your policy details below, drop your PDF Certificate of Insurance, and email it to the team.")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            tech_name = st.text_input("Tech / Contact Name *", placeholder="e.g., John Smith")
        with col2:
            company_name = st.text_input("Business / LLC Name", placeholder="e.g., Smith Sweeping LLC")

        col3, col4 = st.columns(2)
        with col3:
            policy_type = st.selectbox(
                "Policy Type *",
                options=[
                    "General Liability (GL)",
                    "Commercial Auto",
                    "Workers' Compensation",
                    "Combined COI / Umbrella",
                    "Other",
                ],
            )
        with col4:
            carrier_name = st.text_input("Insurance Carrier *", placeholder="e.g., Progressive / Hiscox")

        col5, col6 = st.columns(2)
        with col5:
            policy_number = st.text_input("Policy Number *", placeholder="e.g., GL-12345678")
        with col6:
            exp_date = st.date_input("Policy Expiration Date *", value=date.today())

        coverage_limit = st.text_input(
            "Coverage Limit (Optional)",
            placeholder="e.g., $1,000,000 / $2,000,000 Aggregate",
        )
        notes = st.text_area(
            "Additional Notes (Optional)",
            placeholder="Any notes about additional insured status, renewal updates, etc.",
            height=80,
        )

        st.markdown("**📎 Drop or Upload Insurance Policy PDF ***")
        uploaded_pdf = st.file_uploader(
            "Drop your PDF file here",
            type=["pdf"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )

        if uploaded_pdf is not None:
            size_kb = round(len(uploaded_pdf.getvalue()) / 1024, 1)
            st.info(f"Ready to attach: **{uploaded_pdf.name}** ({size_kb} KB)")

        tech_copy_email = st.text_input(
            "Send a confirmation copy to yourself (Optional)",
            placeholder="your.email@gmail.com",
        )

        if st.button("📧 Email Insurance Policy to Team", type="primary", use_container_width=True):
            if not tech_name.strip() or not carrier_name.strip() or not policy_number.strip():
                st.warning("Please fill in your Name, Insurance Carrier, and Policy Number.")
            elif uploaded_pdf is None:
                st.warning("Please drop or upload a PDF copy of your insurance policy / COI before sending.")
            else:
                try:
                    send_insurance_email(
                        pdf_bytes=uploaded_pdf.getvalue(),
                        pdf_filename=uploaded_pdf.name,
                        tech_name=tech_name,
                        company_name=company_name,
                        policy_type=policy_type,
                        carrier_name=carrier_name,
                        policy_number=policy_number,
                        expiration_date=exp_date.strftime("%Y-%m-%d"),
                        coverage_limit=coverage_limit,
                        notes=notes,
                        tech_copy_email=tech_copy_email,
                    )
                    if tech_copy_email.strip():
                        st.success(
                            f"Sent! **{policy_type}** policy (`{uploaded_pdf.name}`) has been emailed to the team "
                            f"and copied to **{tech_copy_email.strip()}**."
                        )
                    else:
                        st.success(
                            f"Sent! **{policy_type}** policy (`{uploaded_pdf.name}`) has been emailed to the team."
                        )
                except Exception as e:
                    st.error(f"Could not send email — check Streamlit Secrets email settings. Details: {e}")

    st.divider()
    if st.button("← Back to Home", key="bottom_back_ins", use_container_width=True):
        navigate_to("home")


# ==============================================================================
# PAGE 5: LOT HAZARD & ILLEGAL DUMPING REPORT (#1)
# ==============================================================================
def render_hazard_report_page():
    if st.button("← Back to Home", key="top_back_haz"):
        navigate_to("home")

    st.title("🚨 Lot Hazard & Dumping Report")
    st.caption("Document blocked areas, illegal bulk dumping, or lot damage with a timestamped photo and email proof.")

    store_options = [f"{s['store']} — {s['address']}" for s in ROUTE_STOPS] + ["Other / Custom Location"]

    with st.container(border=True):
        tech_name = st.text_input("Tech Name *", placeholder="Enter your name", key="haz_tech")
        selected_store = st.selectbox("Select Store / Property *", options=store_options)

        if selected_store == "Other / Custom Location":
            store_name = st.text_input("Custom Location Name *", placeholder="e.g., King Soopers - Colfax")
            store_address = st.text_input("Custom Street Address *", placeholder="e.g., 1234 E Colfax Ave, Denver, CO")
        else:
            store_name, store_address = selected_store.split(" — ", 1)

        st.markdown("**Select Issue(s) Observed ***")
        issue_choices = [
            "Blocked by Parked Vehicles / Semis",
            "Illegal Bulk Dumping (Furniture / Mattresses / Construction)",
            "Pothole / Broken Curb / Asphalt Damage",
            "Parking Lot / Canopy Lighting Outage",
            "Clogged Storm Drain / Standing Water",
            "Construction Fencing / Inaccessible Dock",
        ]
        selected_issues = [ic for ic in issue_choices if st.checkbox(ic, key=f"haz_chk_{ic}")]

        severity = st.selectbox(
            "Impact on Service",
            options=[
                "Partial Access — Swept Around Obstacle",
                "Blocked — Could Not Service Section",
                "Bulk Haul-Off Quote Needed",
                "Safety / Liability Hazard Notice",
            ],
        )

        details = st.text_area(
            "Field Notes / Specific Area",
            placeholder="e.g., Two semi-trailers parked across rear receiving dock; mattress pile behind north garden center.",
            height=90,
        )

        st.markdown("**📸 Photo Proof (Camera or Gallery Upload)**")
        photo_mode = st.radio(
            "Photo Source",
            options=["Upload from Phone / Gallery", "Take Live Photo with Camera"],
            horizontal=True,
            label_visibility="collapsed",
        )
        photo_file = None
        if photo_mode == "Take Live Photo with Camera":
            photo_file = st.camera_input("Snap photo of hazard or blocked area")
        else:
            photo_file = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")

        if st.button("📧 Email Timestamped Hazard Report", type="primary", use_container_width=True):
            if not tech_name.strip() or not store_name.strip():
                st.warning("Please enter your name and select or enter the store location.")
            elif not selected_issues and not details.strip():
                st.warning("Please check at least one issue or enter field notes.")
            else:
                try:
                    ts_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
                    p_bytes = photo_file.getvalue() if photo_file is not None else None
                    p_name = photo_file.name if (photo_file is not None and hasattr(photo_file, "name")) else "hazard_photo.jpg"
                    p_ext = p_name.split(".")[-1] if "." in p_name else "jpg"

                    haz_pdf = generate_hazard_pdf(
                        tech_name=tech_name,
                        store_name=store_name,
                        store_address=store_address,
                        timestamp_str=ts_str,
                        issues=selected_issues,
                        severity=severity,
                        details=details,
                        photo_bytes=p_bytes,
                        photo_ext=p_ext,
                    )
                    send_hazard_email(
                        pdf_bytes=haz_pdf,
                        tech_name=tech_name,
                        store_name=store_name,
                        store_address=store_address,
                        timestamp_str=ts_str,
                        issues=selected_issues,
                        severity=severity,
                        details=details,
                        photo_bytes=p_bytes,
                        photo_filename=p_name,
                    )
                    st.success(f"Sent! Timestamped hazard report for **{store_name}** emailed to the team.")
                except Exception as e:
                    st.error(f"Could not send report — check Streamlit Secrets email settings. Details: {e}")

    st.divider()
    if st.button("← Back to Home", key="bottom_back_haz", use_container_width=True):
        navigate_to("home")


# ==============================================================================
# PAGE 6: HOPPER DUMP, FUEL & MAINTENANCE LOG (#2)
# ==============================================================================
def render_maintenance_log_page():
    if st.button("← Back to Home", key="top_back_maint"):
        navigate_to("home")

    st.title("⛽ Hopper Dump, Fuel & Maintenance")
    st.caption("Log fuel fill-ups, hopper dump loads, and sweeper parts or repair needs.")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            tech_name = st.text_input("Tech / Driver Name *", placeholder="Enter your name", key="mnt_tech")
        with col2:
            unit_num = st.text_input("Truck / Sweeper Unit # *", placeholder="e.g., Unit 1 / Schwarze A4")

        col3, col4 = st.columns(2)
        with col3:
            log_date = st.date_input("Date *", value=date.today(), key="mnt_date")
        with col4:
            odometer_hrs = st.text_input("Odometer / Aux Hours", placeholder="e.g., 84,210 mi / 1,420 hrs")

        log_types = st.multiselect(
            "What are you logging today? *",
            options=["Fuel Fill-Up", "Hopper Dump", "Parts / Repair Needed"],
            default=["Fuel Fill-Up"],
        )

        fuel_gallons = 0.0
        fuel_cost = 0.0
        if "Fuel Fill-Up" in log_types:
            st.markdown("**⛽ Fuel Details**")
            f1, f2 = st.columns(2)
            with f1:
                fuel_gallons = st.number_input("Gallons Pumped", min_value=0.0, value=0.0, step=0.5)
            with f2:
                fuel_cost = st.number_input("Total Fuel Cost ($)", min_value=0.0, value=0.0, step=1.0)

        dump_location = ""
        dump_load = "N/A"
        if "Hopper Dump" in log_types:
            st.markdown("**🗑️ Hopper Dump Details**")
            d1, d2 = st.columns(2)
            with d1:
                dump_location = st.text_input("Dump Site / Transfer Station", placeholder="e.g., HQ Roll-off / DADS Landfill")
            with d2:
                dump_load = st.selectbox("Estimated Hopper Load", options=["1/4 Full", "1/2 Full", "3/4 Full", "Full Load"])

        repair_items = []
        if "Parts / Repair Needed" in log_types:
            st.markdown("**🔧 Flag Parts / Repair Items**")
            part_choices = [
                "Main Tube Broom Worn",
                "Side Gutter Brush Worn",
                "Hydraulic Hose / Fluid Leak",
                "Water Dust-Suppression Nozzle / Pump",
                "Suction Hood / Rubber Flaps",
                "Strobe / Work / Headlights",
                "Tires / Brakes / Suspension",
                "Auxiliary Engine Issue",
            ]
            c_p1, c_p2 = st.columns(2)
            for idx, item in enumerate(part_choices):
                target_col = c_p1 if idx % 2 == 0 else c_p2
                with target_col:
                    if st.checkbox(item, key=f"prt_{idx}"):
                        repair_items.append(item)

        notes = st.text_area(
            "Notes / Receipt Details",
            placeholder="Any station details, urgent repair notes, or part numbers...",
            height=80,
        )

        attachment = st.file_uploader(
            "Attach Fuel Receipt or Repair Photo (Optional)",
            type=["jpg", "jpeg", "png", "pdf"],
        )

        if st.button("📧 Email Fleet & Fuel Log to Team", type="primary", use_container_width=True):
            if not tech_name.strip() or not unit_num.strip():
                st.warning("Please enter your Name and Truck / Sweeper Unit #.")
            elif not log_types:
                st.warning("Select at least one log category above.")
            else:
                try:
                    att_bytes = attachment.getvalue() if attachment is not None else None
                    att_name = attachment.name if attachment is not None else ""
                    send_maintenance_email(
                        tech_name=tech_name,
                        unit_num=unit_num,
                        log_date=log_date.strftime("%Y-%m-%d"),
                        log_types=log_types,
                        odometer_hrs=odometer_hrs,
                        fuel_gallons=fuel_gallons,
                        fuel_cost=fuel_cost,
                        dump_location=dump_location,
                        dump_load=dump_load,
                        repair_items=repair_items,
                        notes=notes,
                        attachment_bytes=att_bytes,
                        attachment_name=att_name,
                    )
                    st.success(f"Sent! Fleet & Fuel log for **{unit_num}** emailed to the team.")
                except Exception as e:
                    st.error(f"Could not send log — check Streamlit Secrets email settings. Details: {e}")

    st.divider()
    if st.button("← Back to Home", key="bottom_back_maint", use_container_width=True):
        navigate_to("home")


# ==============================================================================
# PAGE 7: SITE NOTES, GATE CODES & CONTACTS DIRECTORY (#5)
# ==============================================================================
def render_site_directory_page():
    if st.button("← Back to Home", key="top_back_dir"):
        navigate_to("home")

    st.title("🔑 Site Notes, Gate Codes & Contacts")
    st.caption("Quick reference for store addresses, service lines, gate/water access, and dispatch contacts.")

    with st.container(border=True):
        st.subheader("📞 Dispatch & Emergency Contacts")
        for ec in EMERGENCY_CONTACTS:
            st.markdown(f"**{ec['role']}:** {ec['contact']}")

    st.divider()

    f_col1, f_col2 = st.columns([2.2, 1.2])
    with f_col1:
        search_q = st.text_input("Search Store or Address", placeholder="e.g., Lowe's, Holly, 80120...")
    with f_col2:
        line_filter = st.selectbox("Service Line", options=["All", "Sweep", "Dual"])

    filtered_stops = []
    for s in ROUTE_STOPS:
        if line_filter != "All" and s["line"] != line_filter:
            continue
        if search_q.strip():
            q = search_q.strip().lower()
            if q not in s["store"].lower() and q not in s["address"].lower():
                continue
        filtered_stops.append(s)

    st.caption(f"Showing **{len(filtered_stops)}** of {len(ROUTE_STOPS)} locations")

    for s in filtered_stops:
        sched_label = ", ".join(s["days"]) if s["days"] else f"Flexible ({s['flex']})"
        note_info = SITE_NOTES.get(
            s["id"],
            {
                "gate": "Standard open parking lot / check rear receiving dock",
                "water": "Fill dust-control tank at Lakewood HQ",
                "curfew": "Run amber strobes; follow standard overnight noise courtesy",
            },
        )
        with st.expander(f"**{s['store']}** ({s['line']}) — {sched_label}"):
            st.markdown(f"📍 **Address:** `{s['address']}`")
            st.markdown(f"📅 **Schedule:** {sched_label}  |  **Flex Rule:** {s['flex']}")
            st.markdown(f"🔐 **Gate / Lot Access:** {note_info['gate']}")
            st.markdown(f"💧 **Water Hookup:** {note_info['water']}")
            st.markdown(f"🌙 **Nightly Notes:** {note_info['curfew']}")

    st.divider()
    if st.button("← Back to Home", key="bottom_back_dir", use_container_width=True):
        navigate_to("home")


# ==============================================================================
# ROUTER
# ==============================================================================
if st.session_state.current_page == "home":
    render_home_page()
elif st.session_state.current_page == "visit_log":
    render_visit_log_page()
elif st.session_state.current_page == "route_optimizer":
    render_route_optimizer_page()
elif st.session_state.current_page == "insurance_upload":
    render_insurance_upload_page()
elif st.session_state.current_page == "hazard_report":
    render_hazard_report_page()
elif st.session_state.current_page == "maintenance_log":
    render_maintenance_log_page()
elif st.session_state.current_page == "site_directory":
    render_site_directory_page()
