import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt

# -----------------------------
# Settings
# -----------------------------
st.set_page_config(page_title="HR Employee Dashboard", layout="wide")

CSV_FILE = "WA_Fn-UseC_-HR-Employee-Attrition.csv"
DB_FILE = "hr.db"
TABLE_NAME = "employees"

# -----------------------------
# Helper: connect to SQLite
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# -----------------------------
# Helper: initialize DB from CSV (only if table doesn't exist)
# -----------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Check if table exists
    cur.execute(f"""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='{TABLE_NAME}';
    """)
    exists = cur.fetchone() is not None

    if not exists:
        df = pd.read_csv(CSV_FILE)

        # Save to SQLite
        df.to_sql(TABLE_NAME, conn, index=False)
    conn.commit()
    conn.close()

# -----------------------------
# Helper: read data from DB
# -----------------------------
def load_data():
    conn = get_conn()
    df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()
    return df

# -----------------------------
# Start
# -----------------------------
st.title("HR Employee Dashboard")

init_db()
df = load_data()

# Preview
st.subheader("Dataset Preview")
st.dataframe(df.head(25), use_container_width=True)

# KPI
st.subheader("Total Employees")
st.write(f"Total Employees: {len(df)}")

# -----------------------------
# Filters (interactive)
# -----------------------------
st.sidebar.header("Filters")

dept_options = ["All"] + sorted(df["Department"].dropna().unique().tolist())
selected_dept = st.sidebar.selectbox("Department", dept_options)

attr_options = ["All"] + sorted(df["Attrition"].dropna().unique().tolist())
selected_attr = st.sidebar.selectbox("Attrition", attr_options)

gender_options = ["All"] + sorted(df["Gender"].dropna().unique().tolist())
selected_gender = st.sidebar.selectbox("Gender", gender_options)

filtered = df.copy()

if selected_dept != "All":
    filtered = filtered[filtered["Department"] == selected_dept]
if selected_attr != "All":
    filtered = filtered[filtered["Attrition"] == selected_attr]
if selected_gender != "All":
    filtered = filtered[filtered["Gender"] == selected_gender]

st.subheader("Filtered Data")
st.write(f"Rows after filtering: {len(filtered)}")
st.dataframe(filtered, use_container_width=True)

# -----------------------------
# Visual 1: Bar chart (employees by department)
# -----------------------------
st.subheader("Employees by Department (Bar Chart)")

dept_counts = filtered["Department"].value_counts()

fig1, ax1 = plt.subplots()
ax1.bar(dept_counts.index, dept_counts.values)
ax1.set_xlabel("Department")
ax1.set_ylabel("Employees")
ax1.set_title("Employees by Department")
plt.xticks(rotation=20, ha="right")
st.pyplot(fig1)

# -----------------------------
# Visual 2: Pie chart (Attrition Yes/No)
# -----------------------------
st.subheader("Attrition Distribution (Pie Chart)")

attr_counts = filtered["Attrition"].value_counts()

fig2, ax2 = plt.subplots()
ax2.pie(attr_counts.values, labels=attr_counts.index, autopct="%1.1f%%")
ax2.set_title("Attrition Distribution")
st.pyplot(fig2)

# -----------------------------
# Visual 3: Histogram (Monthly Income)
# -----------------------------
st.subheader("Monthly Income Distribution (Histogram)")

fig3, ax3 = plt.subplots()
ax3.hist(filtered["MonthlyIncome"].dropna(), bins=20)
ax3.set_xlabel("Monthly Income")
ax3.set_ylabel("Count")
ax3.set_title("Monthly Income Distribution")
st.pyplot(fig3)

# -----------------------------
# Add a new employee (FORM)
# -----------------------------
st.subheader("Add a New Employee")

with st.form("add_employee_form"):
    new_emp_num = st.number_input("EmployeeNumber (must be unique)", min_value=1, step=1)
    new_dept = st.selectbox("Department", sorted(df["Department"].dropna().unique()))
    new_role = st.selectbox("JobRole", sorted(df["JobRole"].dropna().unique()))
    new_income = st.number_input("MonthlyIncome", min_value=0, step=100)
    new_attrition = st.selectbox("Attrition", ["Yes", "No"])
    new_gender = st.selectbox("Gender", ["Male", "Female"])
    submitted = st.form_submit_button("Add Employee")

    if submitted:
        conn = get_conn()
        cur = conn.cursor()

        # Check if EmployeeNumber already exists
        cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE EmployeeNumber = ?", (new_emp_num,))
        exists = cur.fetchone()[0] > 0

        if exists:
            st.error("EmployeeNumber already exists. Please choose another one.")
        else:
            # Insert with only a few columns (others will be NULL)
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (EmployeeNumber, Department, JobRole, MonthlyIncome, Attrition, Gender)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (new_emp_num, new_dept, new_role, new_income, new_attrition, new_gender)
            )
            conn.commit()
            conn.close()
            st.success("Employee added! Refreshing data...")
            st.rerun()

# -----------------------------
# Update existing employee income
# -----------------------------
st.subheader("Update an Existing Employee's Income")

with st.form("update_income_form"):
    emp_to_update = st.number_input("EmployeeNumber to update", min_value=1, step=1)
    updated_income = st.number_input("New MonthlyIncome", min_value=0, step=100)
    update_btn = st.form_submit_button("Update Income")

    if update_btn:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE EmployeeNumber = ?", (emp_to_update,))
        exists = cur.fetchone()[0] > 0

        if not exists:
            st.error("EmployeeNumber not found.")
        else:
            cur.execute(
                f"UPDATE {TABLE_NAME} SET MonthlyIncome = ? WHERE EmployeeNumber = ?",
                (updated_income, emp_to_update)
            )
            conn.commit()
            conn.close()
            st.success("Monthly income updated! Refreshing data...")
            st.rerun()
