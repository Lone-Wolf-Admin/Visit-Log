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

# Mobile-first CSS for large thumb-friendly controls on Android
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 680px; }
    div[data-testid="stButton"] button {
        min-height: 3.1rem;
        font-size: 1.05rem;
        font-weight: 600;
        border-radius: 10px;
    }
    div[data-testid="stDownloadButton"] button {
        min-height: 3.2rem;
        font-size: 1.05rem;
        font-weight: 700;
        border-radius: 10px;
        width: 100%;
    }
    .stMultiSelect div[data-baseweb="select"] { min-height: 48px; }
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
if "extra_items" not in st.session_state:
    st.session_state.extra_items = []


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
    pdf.cell(98, 8, f"Total Invoice Amount: ${total_amount:,.2f}", border=1, align="R")

    # Table Header
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

    # Table Rows
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

    # Grand Total Row
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(col_w[0], 8, "TOTAL", border=1, fill=True, align="R")
    pdf.cell(col_w[1], 8, str(total_visits), border=1, fill=True, align="R")
    pdf.cell(col_w[2], 8, "", border=1, fill=True)
    pdf.cell(col_w[3], 8, f"${total_amount:,.2f}", border=1, fill=True, align="R")
    pdf.cell(col_w[4], 8, "Attach to Novo Invoice", border=1, fill=True)

    return bytes(pdf.output())


def send_completion_email(pdf_bytes: bytes, billing_month: str, invoice_num: str, total_visits: int, total_amount: float):
    smtp_host = st.secrets["email"]["smtp_host"]
    smtp_port = int(st.secrets["email"]["smtp_port"])
    sender = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["sender_password"]
    recipient = st.secrets["email"]["recipient_email"]

    msg = EmailMessage()
    msg["Subject"] = f"Backwoods Services Log Ready — {billing_month} (Inv #{invoice_num} | ${total_amount:,.2f})"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Hi Drew,\n\n"
        f"Backwoods Services has completed the monthly visit log for {billing_month}.\n\n"
        f"- Invoice #: {invoice_num}\n"
        f"- Total Verified Visits: {total_visits}\n"
        f"- Total Invoice Amount: ${total_amount:,.2f}\n\n"
        f"The clean PDF visit log is attached to this email for your records and photo audit.\n"
    )
    filename = f"Backwoods_Visit_Log_{billing_month.replace(' ', '_')}_Inv_{invoice_num}.pdf"
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.send_message(msg)


# --- APP HEADER ---
st.title("🧹 Backwoods Monthly Log")
st.caption("Tap each location below and pick the days you visited. Totals calculate automatically.")

col_m, col_i = st.columns([2, 1])
with col_m:
    default_month = datetime.now().strftime("%B %Y")
    billing_month = st.text_input("Billing Month", value=default_month)
with col_i:
    invoice_num = st.text_input("Invoice #", value="0026")

# --- LIVE SUMMARY BANNER ---
summary_df = build_summary_df()
tot_visits = int(summary_df["Visits"].sum())
tot_amt = float(summary_df["Amount"].sum())

k1, k2 = st.columns(2)
k1.metric("Total Visits Logged", f"{tot_visits}")
k2.metric("Total Invoice Amount", f"${tot_amt:,.2f}")

st.divider()

# --- STEP 1: TAP DAYS VISITED BY ACCOUNT ---
st.subheader("1. Select Days Visited")
days_options = list(range(1, 32))
accounts = ["King Soopers", "Lowe's", "Kohl's", "Best Buy", "Highlands Ranch / Safeway"]

for acct in accounts:
    acct_items = [x for x in RATE_CARD if x["account"] == acct]
    acct_visits = sum(len(st.session_state.visits[x["id"]]) for x in acct_items)
    acct_dollars = sum(len(st.session_state.visits[x["id"]]) * x["rate"] for x in acct_items)
    badge = f" — ✅ {acct_visits} visits (${acct_dollars:,.0f})" if acct_visits > 0 else ""

    with st.expander(f"{acct}{badge}", expanded=(acct == "Best Buy")):
        for item in acct_items:
            c_left, c_right = st.columns([3, 1])
            with c_left:
                st.markdown(f"**{item['location']} — {item['service']}** (${item['rate']:.0f}/visit)")
            with c_right:
                if st.button("Weekly (Fri)", key=f"wk_{item['id']}", help="Quick-fill Fridays (4, 11, 18, 25)"):
                    st.session_state.visits[item["id"]] = [4, 11, 18, 25]
                    st.rerun()

            selected = st.multiselect(
                f"Days visited ({item['location']} {item['service']})",
                options=days_options,
                default=st.session_state.visits[item["id"]],
                key=f"ms_{item['id']}",
                label_visibility="collapsed",
                placeholder="Tap to pick day numbers (1–31)...",
            )
            st.session_state.visits[item["id"]] = selected

# Optional One-Off / Bulk Trash section
with st.expander("➕ Add One-Off Job (e.g., Bulk Trash)"):
    ex_name = st.text_input("Job Description", placeholder="e.g., Arkansas Bulk Trash")
    ex_rate = st.number_input("Price per Visit ($)", min_value=0.0, value=500.0, step=25.0)
    ex_days = st.multiselect("Day(s) Completed", options=days_options, key="ex_days_picker")
    if st.button("Add One-Off Job to Log"):
        if ex_name and ex_days:
            st.session_state.extra_items.append({"name": ex_name, "rate": ex_rate, "days": ex_days})
            st.rerun()
        else:
            st.warning("Enter a job description and at least one day.")

st.divider()

# --- STEP 2: REVIEW & SUBMIT ---
st.subheader("2. Download PDF & Notify Drew")
active_preview = summary_df[summary_df["Visits"] > 0][["Line Item", "Visits", "Amount", "Dates Visited"]]

if active_preview.empty:
    st.info("No visits selected yet. Open any store group above and tap the days you visited.")
else:
    st.dataframe(active_preview, use_container_width=True, hide_index=True)

    pdf_bytes = generate_invoice_pdf(summary_df, billing_month, invoice_num)
    pdf_filename = f"Backwoods_Visit_Log_{billing_month.replace(' ', '_')}_Inv_{invoice_num}.pdf"

    st.download_button(
        label="📄 1. Download PDF to Attach in Novo",
        data=pdf_bytes,
        file_name=pdf_filename,
        mime="application/pdf",
        type="secondary",
    )

    if st.button("📧 2. Email Completed Log to Drew", type="primary", use_container_width=True):
        try:
            send_completion_email(pdf_bytes, billing_month, invoice_num, tot_visits, tot_amt)
            st.success(f"Sent! Drew received the {billing_month} PDF log (${tot_amt:,.2f} across {tot_visits} visits).")
        except Exception as e:
            st.error(f"Could not send email — check Streamlit Secrets email settings. Details: {e}")
