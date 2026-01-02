import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import bcrypt

# ================= CONFIG =================
st.set_page_config("Expense Tracker", "💰", layout="wide")
CURRENT_MONTH = date.today().strftime("%Y-%m")

# ================= DATABASE =================
conn = sqlite3.connect("finance.db", check_same_thread=False)
cur = conn.cursor()

# ================= TABLES =================
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    month TEXT,
    date TEXT,
    category TEXT,
    amount REAL,
    note TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS salary (
    username TEXT PRIMARY KEY,
    salary REAL
)
""")

conn.commit()

# ================= CSS (UI + ANIMATION) =================
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #020617, #0f172a);
}
[data-testid="stSidebar"] {
    background-color: #020617;
}
.card {
    background: linear-gradient(135deg, #1e293b, #020617);
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    animation: fadeUp 0.6s ease-in-out;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 15px 40px rgba(0,0,0,0.6);
}
@keyframes fadeUp {
    from {opacity:0; transform:translateY(12px);}
    to {opacity:1; transform:translateY(0);}
}
.hr {
    height:1px;
    background:#334155;
    margin:25px 0;
}
</style>
""", unsafe_allow_html=True)

# ================= AUTH HELPERS =================
def hash_password(p): 
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def check_password(p, h): 
    return bcrypt.checkpw(p.encode(), h.encode())

# ================= SESSION =================
if "logged" not in st.session_state:
    st.session_state.logged = False

# ================= AUTH UI =================
if not st.session_state.logged:
    st.title("🔐 Expense Tracker")

    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            cur.execute("SELECT password_hash FROM users WHERE username=?", (u,))
            row = cur.fetchone()
            if row and check_password(p, row[0]):
                st.session_state.logged = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        su = st.text_input("New Username")
        sp = st.text_input("New Password", type="password")
        if st.button("Signup"):
            cur.execute("SELECT * FROM users WHERE username=?", (su,))
            if cur.fetchone():
                st.error("Username already exists")
            else:
                cur.execute(
                    "INSERT INTO users VALUES (?,?)",
                    (su, hash_password(sp))
                )
                conn.commit()
                st.success("Account created! Login now.")
    st.stop()

# ================= LOGOUT =================
st.sidebar.success(f"Logged in as {st.session_state.user}")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

user = st.session_state.user
categories = ["Food","Rent","Travel","Shopping","Bills","Others"]

# ================= SALARY =================
cur.execute("SELECT salary FROM salary WHERE username=?", (user,))
row = cur.fetchone()

if "salary" not in st.session_state:
    st.session_state.salary = row[0] if row else 0.0

salary_input = st.sidebar.number_input(
    "💼 Monthly Salary (₹)",
    min_value=0.0,
    value=float(st.session_state.salary),
    step=1000.0
)

if salary_input != st.session_state.salary:
    cur.execute(
        "INSERT INTO salary (username, salary) VALUES (?, ?) \
         ON CONFLICT(username) DO UPDATE SET salary=excluded.salary",
        (user, salary_input)
    )
    conn.commit()
    st.session_state.salary = salary_input

# ================= ADD EXPENSE =================
st.sidebar.subheader("➕ Add Daily Expense")
d = st.sidebar.date_input("Date", date.today())
cat = st.sidebar.selectbox("Category", categories)
amt = st.sidebar.number_input("Amount (₹)", min_value=0.0, step=100.0)
note = st.sidebar.text_input("Note")

if st.sidebar.button("Add Expense"):
    cur.execute(
        "INSERT INTO expenses (username,month,date,category,amount,note) VALUES (?,?,?,?,?,?)",
        (user, CURRENT_MONTH, d.isoformat(), cat, amt, note)
    )
    conn.commit()
    st.sidebar.success("Expense added")
    st.rerun()

# ================= LOAD DATA (CURRENT MONTH) =================
df = pd.read_sql(
    "SELECT date, category, amount, note FROM expenses WHERE username=? AND month=?",
    conn,
    params=(user, CURRENT_MONTH)
)

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])

# ================= DASHBOARD =================
st.title(f"💰 Finance Dashboard — {CURRENT_MONTH}")

total_expense = df["amount"].sum() if not df.empty else 0
savings = salary_input - total_expense
savings_pct = (savings / salary_input * 100) if salary_input > 0 else 0

col1, col2, col3 = st.columns(3)
col1.markdown(f"<div class='card'><h3>Salary</h3><h2>₹ {salary_input:,.0f}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='card'><h3>Expenses</h3><h2>₹ {total_expense:,.0f}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='card'><h3>Savings</h3><h2>₹ {savings:,.0f}</h2></div>", unsafe_allow_html=True)

# ================= SAVINGS PLANNER =================
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.subheader("📈 Savings Planner")

ideal_savings = salary_input * 0.3
daily_limit = (salary_input - ideal_savings) / 30 if salary_input else 0

st.info(
    f"""
    **Ideal Monthly Savings (30%)**: ₹ {ideal_savings:,.0f}  
    **Daily Safe Spending Limit**: ₹ {daily_limit:,.0f}  
    **Savings Percentage**: {savings_pct:.1f}%
    """
)

if savings >= ideal_savings:
    st.success("✅ You are on track with your savings!")
elif savings > 0:
    st.warning("⚠️ Savings below ideal. Try reducing expenses.")
else:
    st.error("❌ No savings left this month!")

# ================= TABLE =================
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.subheader("📋 Expense Records")
st.dataframe(df, use_container_width=True)

# ================= CHARTS =================
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.subheader("📊 Visual Reports")

if not df.empty:
    col1, col2 = st.columns(2)

    # -------- PIE CHART --------
    with col1:
        st.markdown("**Category-wise Spending**")
        fig1, ax1 = plt.subplots()
        df.groupby("category")["amount"].sum().plot(
            kind="pie", autopct="%1.1f%%", ax=ax1
        )
        ax1.set_ylabel("")
        st.pyplot(fig1)

    # -------- BAR CHART --------
    with col2:
        st.markdown("**Daily Expense Trend**")
        fig2, ax2 = plt.subplots()
        df.groupby("date")["amount"].sum().plot(
            kind="bar", ax=ax2
        )
        ax2.set_ylabel("₹ Amount")
        ax2.set_xlabel("Date")
        plt.xticks(rotation=45)
        st.pyplot(fig2)
else:
    st.info("No expenses added yet for this month.")
