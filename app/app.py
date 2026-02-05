import sys
import os
import re
import streamlit as st
import pandas as pd
import duckdb

# Allow imports from project root
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from models.local_model import generate as local_generate
from models.cloud_model import generate as cloud_generate

st.markdown(
    """
    <style>
    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background-color: #4B007D;  /* Purple */
    }

    /* Sidebar labels */
    section[data-testid="stSidebar"] label {
        color: #FF2A2A !important;  /* Bright red */
        font-weight: 700;
    }

    /* Selectbox selected value text */
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: #FF2A2A !important;
        font-weight: 600;
    }

    /* Selectbox input background */
    section[data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: white !important;
        border-radius: 10px;
    }

    /* Clear Chat button text */
    section[data-testid="stSidebar"] button {
        color: #FF2A2A !important;
        font-weight: 700;
    }
    
    /* Sidebar title: Solutions by stc */
.stc-sidebar-title {
    color: #E10600;          /* STC Red */
    font-size: 22px;
    font-weight: 800;
    text-align: center;
    margin-bottom: 20px;
    letter-spacing: 0.5px;
    text-transform: lowercase;
}

.stc-sidebar-title::after {
content: "";
display: block;
width: 60%;
height: 2px;
background: #4B007D;
margin: 10px auto 0;
}
    </style>
    """,
    unsafe_allow_html=True
)

with st.sidebar:
    st.markdown(
        "<div class='stc-sidebar-title'>solutions by stc</div>",
        unsafe_allow_html=True
    )

# ===================== SESSION STATE =====================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ===================== CONFIG =====================
CSV_PATH = "data/WA_Fn-UseC_-HR-Employee-Attrition.csv"
TABLE_NAME = "employees"
MAX_SQL_RETRIES = 3


# ===================== SEMANTIC NORMALIZATION =====================
def normalize_department(question: str):
    q = question.lower()
    if "sales" in q:
        return "Sales"
    if "research" in q or "r&d" in q or "development" in q:
        return "Research & Development"
    if "human" in q or "hr" in q:
        return "Human Resources"
    return None


def normalize_attrition(question: str):
    q = question.lower()
    if "left" in q or "quit" in q or "resigned" in q or "attrition yes" in q:
        return "Yes"
    if "stayed" in q or "attrition no" in q or "did not leave" in q:
        return "No"
    return None


# ===================== SQL HELPERS =====================
def extract_sql(text: str) -> str:
    block = re.search(r"```sql\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if block:
        return block.group(1).strip()

    inline = re.search(r"(select\s+.*)", text, re.IGNORECASE | re.DOTALL)
    return inline.group(1).strip() if inline else ""


def is_select_only(sql: str) -> bool:
    if not sql:
        return False

    s = sql.strip().lower()
    if not s.startswith("select"):
        return False

    forbidden = [
        "insert", "update", "delete", "drop",
        "alter", "create", "attach", "detach", "pragma"
    ]
    return not any(re.search(rf"\b{kw}\b", s) for kw in forbidden)


# ===================== DATA =====================
@st.cache_resource
def load_db():
    df = pd.read_csv(CSV_PATH)
    con = duckdb.connect(database=":memory:")
    con.register(TABLE_NAME, df)
    return con, df, df.columns.tolist()


def summarize_result(df: pd.DataFrame) -> str:
    if df.empty:
        return "No results found."

    if df.shape == (1, 1):
        return f"{df.iloc[0, 0]}"

    return f"Returned {df.shape[0]} row(s). See table."


# ===================== UI =====================
st.set_page_config(page_title="HR Analytics Chatbot", layout="wide")
st.title("HR Analytics Chatbot")
st.caption("Chat-based HR analytics with enhanced reasoning")

model_choice = st.sidebar.selectbox(
    "Choose model",
    ["Local (1.5B)", "Cloud (7B)"]
)

if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages.clear()
    st.rerun()

con, df, cols = load_db()

# ===================== CHAT HISTORY =====================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===================== INPUT =====================
user_input = st.chat_input("Ask a question about the HR dataset...")

# ===================== MAIN LOGIC =====================
if user_input:
    # User message
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )

    # Memory context
    context = ""
    if st.session_state.chat_history:
        context = "Previous questions:\n"
        for q in st.session_state.chat_history[-3:]:
            context += f"- {q}\n"

    # Semantic grounding
    dept = normalize_department(user_input)
    attr = normalize_attrition(user_input)

    grounding_hint = ""
    if dept:
        grounding_hint += f"\nDepartment MUST be: '{dept}'"
    if attr:
        grounding_hint += f"\nAttrition MUST be: '{attr}'"

    cols_line = ", ".join(cols)

    base_prompt = f"""
You are an expert data analyst writing SQL for an HR database.

{grounding_hint}

CONTEXT:
{context if context else "None"}

DATA RULES:
- Table name: {TABLE_NAME}
- Attrition values: 'Yes' or 'No'
- Department values are case-sensitive
- If multiple conditions appear, COMBINE them using AND

SQL RULES:
- Output ONLY SQL
- SELECT statements ONLY
- Use WHERE for filters
- Percentages must use:
  (COUNT(condition) * 100.0 / COUNT(*))
- Use GROUP BY when needed
- Add LIMIT 200 when output may be large

COLUMNS:
{cols_line}

QUESTION:
{user_input}
""".strip()

    used_cloud = False
    sql = ""
    result = pd.DataFrame()

    with st.spinner("Thinking..."):
        for attempt in range(MAX_SQL_RETRIES):
            if model_choice == "Local (1.5B)":
                raw = local_generate(base_prompt)
                sql = extract_sql(raw)
                if not is_select_only(sql):
                    raw = cloud_generate(base_prompt)
                    sql = extract_sql(raw)
                    used_cloud = True
            else:
                raw = cloud_generate(base_prompt)
                sql = extract_sql(raw)
                used_cloud = True

            if not is_select_only(sql):
                continue

            try:
                result = con.sql(sql).df()
                if not result.empty:
                    break
            except Exception:
                continue

        if result.empty:
            with st.chat_message("assistant"):
                st.markdown("❌ I couldn’t generate a correct query for this question.")
            st.stop()

    # Update memory
    st.session_state.chat_history.append(user_input)
    if len(st.session_state.chat_history) > 5:
        st.session_state.chat_history = st.session_state.chat_history[-5:]

    # Build response
    answer_text = summarize_result(result)
    show_table = result.shape[0] > 1

    full_response = (
        f"**Answer**\n"
        f"{answer_text}\n\n"
        f"**Generated SQL**\n"
        f"```sql\n{sql}\n```"
    )

    if used_cloud:
        full_response += "\n\nℹ️ _Cloud model was used for accuracy._"

    with st.chat_message("assistant"):
        st.markdown(full_response)

        if show_table:
            st.dataframe(result, use_container_width=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response}
    )
