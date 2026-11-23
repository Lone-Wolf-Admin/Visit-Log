import calendar
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
import pandas as pd
import streamlit as st
from fpdf import FPDF

st.set_page_config(
    page_title="Monthly Visit Log",
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

# Always ensure every RATE_CARD id exists in session_state.visits
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


def match_store_from_text(text_block: str) -> str:
    """Matches a DMG Pro address or store name snippet to our canonical Store label."""
    low = text_block.lower()
    for item in RATE_CARD:
        for key in item["addr_keys"]:
            if key in low:
                return f"{item['account']} - {item['location']}"
    return "Unmapped / Out-of-Route Store"


def parse_dmg_pasted_text(raw_text: str) -> pd.DataFrame:
    """Parses copied screen text from either DMG Pro Invoices cards or Job Details pages."""
    records = []
    if not raw_text or not raw_text.strip():
        return pd.DataFrame()

    # Check if this is a Job Details page ("Job details / JOB-...")
    job_detail_match = re.search(r"Job details\s*/\s*(JOB-[A-Z0-9-]+)", raw_text)
    if job_detail_match:
        job_id = job_detail_match.group(1)
        store_label = match_store_from_text(raw_text)
        elig_match = re.search(r"Eligible visits\s+(\d+)", raw_text)
        elig_visits = int(elig_match.group(1)) if elig_match else 0

        # Extract Visit check-ins (e.g., "Visit 1 Check-in: Nov 10, 2026 9:38 PM")
        visit_matches = re.findall(
            r"Visit\s+\d+.*?Check-in:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            raw_text,
            flags=re.DOTALL,
        )
        day_nums = []
        for dt_str in visit_matches:
            try:
                day_nums.append(datetime.strptime(dt_str, "%b %d, %Y").day)
            except ValueError:
                pass

        # Extract dollar totals on the job detail page
        amounts = [float(a.replace(",", "")) for a in re.findall(r"Total\s*\n?\s*\$([\d,]+\.\d{2})", raw_text)]
        total_amt = sum(amounts)

        records.append(
            {
                "Store": store_label,
                "Job Number": job_id,
                "DMG Eligible Visits": elig_visits if elig_visits > 0 else len(day_nums),
                "DMG Check-In Days": ", ".join(str(d) for d in sorted(set(day_nums))),
                "DMG Amount": round(total_amt, 2),
            }
        )
        return pd.DataFrame(records)

    # Otherwise parse Invoices & Payments card list (split by "Invoice number")
    chunks = re.split(r"(?=Invoice number\s+I\d+-)", raw_text)
    for chunk in chunks:
        job_m = re.search(r"Job number\s+(JOB-[A-Z0-9-]+)", chunk)
        amt_m = re.search(r"Amount\s+\$([\d,]+\.\d{2})", chunk)
        if job_m and amt_m:
            store_label = match_store_from_text(chunk)
            records.append(
                {
                    "Store": store_label,
                    "Job Number": job_m.group(1),
                    "DMG Eligible Visits": None,
                    "DMG Check-In Days": "(Open job in DMG to view days)",
                    "DMG Amount": float(amt_m.group(1).replace(",", "")),
                }
            )
    return pd.DataFrame(records)


# --- APP HEADER ---
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

# --- LIVE SUMMARY BANNER ---
summary_df = build_summary_df()
tot_visits = int(summary_df["Visits"].sum())
tot_amt = float(summary_df["Amount"].sum())

k1, k2 = st.columns(2)
k1.metric("Total Visits Logged", f"{tot_visits}")
k2.metric("Total Invoice Amount", f"${tot_amt:,.2f}")

st.divider()

# --- STEP 1: TAP DATES VISITED BY ACCOUNT ---
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

# Optional One-Off / Bulk Trash section
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
                st.rerun()

st.divider()

# --- STEP 2: REVIEW & SUBMIT ---
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
            if tech_copy_email.strip():
                st.success(
                    f"Sent! Completed {billing_month} PDF log (${tot_amt:,.2f} across {tot_visits} visits) "
                    f"emailed to Team and {tech_copy_email.strip()}."
                )
            else:
                st.success(
                    f"Sent! Completed {billing_month} PDF log (${tot_amt:,.2f} across {tot_visits} visits) "
                    f"emailed to Team."
                )
        except Exception as e:
            st.error(f"Could not send email — check Streamlit Secrets email settings. Details: {e}")

st.divider()

# --- STEP 3: OPTIONAL DMG PRO AUDIT CROSS-REFERENCE ---
with st.expander("🔍 3. Cross-Reference Log Against DMG Pro (Admin Audit)"):
    st.caption(
        "On DMG Pro's 'Invoices & payments' screen or inside any 'Job details' page, press Ctrl+A then Ctrl+C "
        "and paste below to verify store addresses, dates, and dollar totals against the logged visits above."
    )
    dmg_pasted = st.text_area(
        "Paste copied DMG Pro page text here:",
        height=140,
        placeholder="Paste Ctrl+A / Ctrl+C text from DMG Pro here...",
    )
    dmg_csv = st.file_uploader(
        "Or upload DMG Pro Early-Pay / Invoices CSV export (optional):",
        type=["csv"],
    )

    if dmg_pasted.strip():
        parsed_dmg = parse_dmg_pasted_text(dmg_pasted)
        if parsed_dmg.empty:
            st.warning("Could not detect any DMG Pro job numbers or invoice cards in the pasted text.")
        else:
            st.markdown("**Extracted DMG Pro Records (Mapped to Your Routing Addresses):**")
            st.dataframe(parsed_dmg, use_container_width=True, hide_index=True)

            # Compare by Store against active technician log
            tech_by_store = (
                summary_df[summary_df["Visits"] > 0]
                .groupby("Store", as_index=False)
                .agg({"Visits": "sum", "Amount": "sum", "Dates Visited": lambda s: ", ".join(x for x in s if x)})
            )
            dmg_by_store = (
                parsed_dmg.groupby("Store", as_index=False)
                .agg(
                    {
                        "Job Number": lambda s: ", ".join(s),
                        "DMG Check-In Days": lambda s: ", ".join(x for x in s if x),
                        "DMG Amount": "sum",
                    }
                )
            )
            audit_df = pd.merge(tech_by_store, dmg_by_store, on="Store", how="outer").fillna(
                {"Visits": 0, "Amount": 0.0, "Dates Visited": "-", "Job Number": "-", "DMG Check-In Days": "-", "DMG Amount": 0.0}
            )
            audit_df["Tech Visits"] = audit_df["Visits"].astype(int)
            audit_df["Tech Billed ($)"] = audit_df["Amount"].round(2)
            audit_df["DMG Portal ($)"] = audit_df["DMG Amount"].round(2)

            def audit_status(row):
                if row["Store"] == "Unmapped / Out-of-Route Store":
                    return "⚠️ Out-of-Route Store"
                if row["Tech Visits"] > 0 and row["DMG Portal ($)"] == 0:
                    return "❌ Missing in DMG Paste"
                if row["Tech Visits"] == 0 and row["DMG Portal ($)"] > 0:
                    return "📋 In DMG, Not in Log"
                return "✅ Found in Both"

            audit_df["Status"] = audit_df.apply(audit_status, axis=1)
            st.markdown("**Side-by-Side Reconciliation:**")
            st.dataframe(
                audit_df[
                    [
                        "Store",
                        "Status",
                        "Tech Visits",
                        "Dates Visited",
                        "DMG Check-In Days",
                        "Tech Billed ($)",
                        "DMG Portal ($)",
                        "Job Number",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    if dmg_csv is not None:
        csv_df = pd.read_csv(dmg_csv)
        st.markdown(f"**Uploaded DMG CSV ({len(csv_df)} jobs | Total: ${csv_df['Amount'].sum():,.2f}):**")
        st.dataframe(csv_df, use_container_width=True, hide_index=True)

    if not dmg_pasted.strip() and dmg_csv is None:
        st.info("Paste copied DMG Pro screen text or upload the DMG Pro CSV above to run the cross-reference.")
