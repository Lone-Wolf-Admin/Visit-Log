import calendar
import smtplib
from datetime import datetime
from email.message import EmailMessage
import pandas as pd
import streamlit as st
from fpdf import FPDF

st.set_page_config(
    page_title="Backwoods Services — Monthly Visit Log",
    page_icon="🧹",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Mobile-first CSS: keeps the 7-column calendar grid on 1 row on Android screens and styles green selected dates
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 680px; }

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

# Master rate card from Invoice #0025 (34 items grouped by Account -> Location -> Service)
RATE_CARD = [
    {"id": "bb_mex_swp", "account": "Best Buy", "location": "Mexico", "service": "Sweeping", "rate": 30.00},
    {"id": "bb_mex_qc", "account": "Best Buy", "location": "Mexico", "service": "QC", "rate": 7.00},
    {"id": "bb_wad_swp", "account": "Best Buy", "location": "Wadsworth", "service": "Sweeping", "rate": 30.00},
    {"id": "bb_wad_qc", "account": "Best Buy", "location": "Wadsworth", "service": "QC", "rate": 7.00},
    {"id": "hr_prt", "account": "Highlands Ranch / Safeway", "location": "Highlands Ranch", "service": "Porter", "rate": 50.00},
    {"id": "hr_saf_swp", "account": "Highlands Ranch / Safeway", "location": "Highlands Ranch Safeway", "service": "Sweeping", "rate": 50.00},
    {"id": "ks_ark_swp", "account": "King Soopers", "location": "Arkansas", "service": "Sweeping", "rate": 40.00},
    {"id": "ks_ark_qc", "account": "King Soopers", "location": "Arkansas", "service": "QC", "rate": 7.00},
    {"id": "ks_ark_blk", "account": "King Soopers", "location": "Arkansas", "service": "Bulk Trash", "rate": 500.00},
    {"id": "ks_eva_swp", "account": "King Soopers", "location": "Evans", "service": "Sweeping", "rate": 40.00},
    {"id": "ks_eva_qc", "account": "King Soopers", "location": "Evans", "service": "QC", "rate": 7.00},
    {"id": "ks_fed_swp", "account": "King Soopers", "location": "Federal", "service": "Sweeping", "rate": 40.00},
    {"id": "ks_fed_qc", "account": "King Soopers", "location": "Federal", "service": "QC", "rate": 7.00},
    {"id": "ks_ham_qc", "account": "King Soopers", "location": "Hampden", "service": "QC", "rate": 5.00},
    {"id": "ks_lee_swp", "account": "King Soopers", "location": "Leetsdale", "service": "Sweeping", "rate": 40.00},
    {"id": "ks_lee_qc", "account": "King Soopers", "location": "Leetsdale", "service": "QC", "rate": 7.00},
    {"id": "ks_lit_qc", "account": "King Soopers", "location": "Littleton", "service": "QC", "rate": 5.00},
    {"id": "ks_lit_prt", "account": "King Soopers", "location": "Littleton", "service": "Porter", "rate": 7.00},
    {"id": "ks_qui_qc", "account": "King Soopers", "location": "Quincy", "service": "QC", "rate": 5.00},
    {"id": "ks_sho_prt", "account": "King Soopers", "location": "S Holly", "service": "Porter", "rate": 7.00},
    {"id": "ko_20m_swp", "account": "Kohl's", "location": "20 Mile", "service": "Sweeping", "rate": 35.00},
    {"id": "ko_20m_qc", "account": "Kohl's", "location": "20 Mile", "service": "QC", "rate": 7.00},
    {"id": "ko_cas_swp", "account": "Kohl's", "location": "Castle Rock", "service": "Sweeping", "rate": 35.00},
    {"id": "ko_cas_qc", "account": "Kohl's", "location": "Castle Rock", "service": "QC", "rate": 7.00},
    {"id": "ko_kip_swp", "account": "Kohl's", "location": "Kipling", "service": "Sweeping", "rate": 35.00},
    {"id": "ko_kip_qc", "account": "Kohl's", "location": "Kipling", "service": "QC", "rate": 7.00},
    {"id": "ko_que_swp", "account": "Kohl's", "location": "Quebec", "service": "Sweeping", "rate": 35.00},
    {"id": "ko_que_qc", "account": "Kohl's", "location": "Quebec", "service": "QC", "rate": 7.00},
    {"id": "ko_bus_trh", "account": "Kohl's", "location": "All Kohl's", "service": "Bus Trash", "rate": 15.00},
    {"id": "lo_20m_swp", "account": "Lowe's", "location": "20 Mile", "service": "Sweeping", "rate": 50.00},
    {"id": "lo_buc_swp", "account": "Lowe's", "location": "Buckley", "service": "Sweeping", "rate": 50.00},
    {"id": "lo_pea_swp", "account": "Lowe's", "location": "Peakview", "service": "Sweeping", "rate": 50.00},
    {"id": "lo_san_swp", "account": "Lowe's", "location": "Santa Fe", "service": "Sweeping", "rate": 50.00},
    {"id": "lo_whe_swp", "account": "Lowe's", "location": "Wheatlands", "service": "Sweeping", "rate": 50.00},
]

if "visits" not in st.session_state:
    st.session_state.visits = {row["id"]: [] for row in RATE_CARD}
if "open_account" not in st.session_state:
    st.session_state.open_account = None
if "open_calendar" not in st.session_state:
    st.session_state.open_calendar = None
if "extra_items" not in st.session_state:
    st.session_state.extra_items = []
if "extra_temp_days" not in st.session_state:
    st.session_state.extra_temp_days = []


def render_calendar_picker(selected_days: list[int], year: int, month_num: int, key_prefix: str) -> list[int]:
    """Renders a 7-column Sun-Sat calendar grid where tapping a day toggles it on/off and stays open."""
    cal = calendar.Calendar(firstweekday=6)  # Start weeks on Sunday
    weeks = cal.monthdayscalendar(year, month_num)
    updated = set(selected_days)

    # Day-of-week header row
    hdr_cols = st.columns(7)
    for i, day_name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
        hdr_cols[i].markdown(
            f"<div style='text-align:center; font-size:0.75rem; font-weight:700; color:#64748b;'>{day_name}</div>",
            unsafe_allow_html=True,
        )

    # Calendar date rows
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
                "Line Item": f"{item['account']} - {item['location']} - {item['service']}",
                "Visits": qty,
                "Rate": item["rate"],
                "Amount": round(qty * item["rate"], 2),
                "Dates Visited": ", ".join(str(d) for d in days),
            }
        )
    for extra in st.session_state.extra_items:
        days = sorted(extra["days"])
        qty = len(days)
        rows.append(
            {
                "Account": "Extra / One-Off",
                "Line Item": extra["name"],
                "Visits": qty,
                "Rate": extra["rate"],
                "Amount": round(qty * extra["rate"], 2),
                "Dates Visited": ", ".join(str(d) for d in days),
            }
        )
    return pd.DataFrame(rows)


def generate_invoice_pdf(df: pd.DataFrame, billing_month: str, invoice_num: str) -> bytes:
    active_df = df[df["Visits"] > 0].copy()
    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header Banner
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(10, 10, 196, 22, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(14, 14)
    pdf.cell(120, 7, "BACKWOODS SERVICES - MONTHLY VISIT LOG")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(14, 22)
    pdf.cell(120, 6, f"Bill To: Lone Wolf Parking Lot Services LLC  |  Period: {billing_month}")
    pdf.set_xy(145, 16)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(55, 8, f"Invoice #{invoice_num}", align="R")

    # Summary KPIs
    total_visits = int(active_df["Visits"].sum()) if not active_df.empty else 0
    total_amount = float(active_df["Amount"].sum()) if not active_df.empty else 0.0

    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(10, 36)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(98, 8, f"Total Verified Visits: {total_visits}", border=1)
    pdf.cell(98, 8, f"Total Invoice
