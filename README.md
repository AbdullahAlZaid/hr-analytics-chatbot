\# HR Analytics Chatbot



An AI-powered HR analytics dashboard that allows users to ask questions

about an HR dataset using natural language.



\## 🔍 Features

\- Chat-based interface built with Streamlit

\- Text-to-SQL pipeline for accurate analytics

\- Local AI model (1.5B) + Cloud AI model (7B)

\- Conversation memory for follow-up questions

\- SQL-backed answers using structured HR data



\## 🧠 How it works

1\. User asks a question in plain English

2\. The AI converts the question into SQL

3\. SQL is executed on the HR dataset

4\. Results are returned in natural language

5\. Chat memory preserves conversation context



\## 📊 Dataset

IBM HR Employee Attrition Dataset (CSV)



\## 🖼️ Demo

Below are screenshots and a GIF showing:

\- The dashboard UI

\- Example questions and answers

\- Chat memory in action



!\[Dashboard](assets/dashboard.png)

!\[Answered Question](assets/answered\_question.png)



!\[Chat Memory Demo](assets/chat\_memory.gif)



\## ⚙️ Setup Instructions



```bash

conda create -n hr\_analysis python=3.10

conda activate hr\_analysis

pip install -r requirements.txt

streamlit run app/app.py



