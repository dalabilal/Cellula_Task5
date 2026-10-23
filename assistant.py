import os
import re

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL = "openrouter/free"  # use the same model that works in your assistant.py

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found. Put it in a .env file next to app.py")

llm = ChatOpenAI(
    model=MODEL,
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)


def ask(system, user):
    return llm.invoke([("system", system), ("human", user)]).content


def clean_sql(text):
    """Removes ```sql fences and any text before the SELECT."""
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1)
    m = re.search(r"\bselect\b.*", text, re.DOTALL | re.IGNORECASE)
    return (m.group(0) if m else text).strip()


def generate_sql(question, schema, error=None):
    system = (
        "You are an expert in SQLite. Convert the user's question into ONE SQLite SELECT query.\n"
        "The question can be in Arabic or English. Understand it, then write SQL.\n"
        "Rules:\n"
        "- Use ONLY the table and column names from the schema below, exactly as written.\n"
        "- Text values from the data (even Arabic) must be written exactly as they appear in the data.\n"
        "- Use a single SELECT statement, no comments.\n"
        "- Return ONLY the SQL. No explanation, no markdown.\n\n"
        f"Database schema:\n{schema}"
    )
    user = question
    if error:
        user += f"\n\nYour previous attempt failed. Fix it.\n{error}"
    return clean_sql(ask(system, user))


def explain_result(question, sql, columns, rows):
    system = (
        "You are a data analyst. Explain the query result in 2 or 3 short, simple sentences. "
        "Answer in the SAME language as the user's question (Arabic if the question is Arabic)."
    )
    user = f"Question: {question}\nSQL: {sql}\nColumns: {columns}\nRows (up to 20): {rows[:20]}"
    return ask(system, user).strip()
