# Voice-Based Data Analysis System

Ask questions about your data by **voice** (Arabic or English) and get the answer as a table with an explanation.
Built with **FastAPI**, **Faster-Whisper**, an LLM from **OpenRouter** and **SQLite3**.

## Pipeline

```
Voice -> Faster-Whisper -> Text -> LLM -> SQL query -> SQLite3 -> Result + Explanation
```

1. The user uploads a CSV or Excel dataset. It is stored in a SQLite3 table.
2. The user speaks (or types) a question, in Arabic or English.
3. Faster-Whisper converts the speech to text.
4. The LLM reads the question and the dataset structure (table, columns, sample rows) and writes a SQL query.
5. The query is validated and executed with SQLite3.
6. The API returns the result rows and a short explanation, in the language of the question.

## Safety checks on the generated SQL

- Only a single `SELECT` statement is allowed.
- Words like `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER` are rejected.
- The query runs on a **read-only** database connection and is checked before it runs.
- If the SQL fails, the LLM gets the error and tries once more.

## Project structure

| File | Purpose |
|---|---|
| `app.py` | FastAPI app, API endpoints, serves the web page |
| `loader.py` | Audio loading and speech-to-text (Faster-Whisper) |
| `assistant.py` | LLM (OpenRouter): text to SQL and result explanation |
| `database.py` | SQLite3: load dataset, schema, SQL validation and execution |
| `index.html` | Simple web page: upload, ask, record |
| `sales.csv` | Small sample dataset for testing |

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/dataset` | Upload a CSV / Excel dataset |
| GET | `/schema` | Show tables and columns |
| POST | `/transcribe` | Audio to text |
| POST | `/generate-sql` | Question to SQL (does not run it) |
| POST | `/execute-sql` | Validate and run a SELECT query |
| POST | `/ask-text` | Text question to result and explanation |
| POST | `/ask-voice` | Full pipeline from an audio file |

The `language` option of `/ask-voice` and `/transcribe` is optional (`en` or `ar`). If empty, the language is detected automatically.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        
   ```
2. Install the packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file next to `app.py` with your [OpenRouter](https://openrouter.ai) key:
   ```
   OPENROUTER_API_KEY=your_key_here
   ```
4. Run the server:
   ```bash
   python -m uvicorn app:app --reload
   ```
5. Open **http://127.0.0.1:8000** for the web page.

## How to use

1. Upload `sales.csv` (or your own dataset) with the **Upload** button.
2. Type a question, upload a record, or press **Record**, speak, and press **Stop**.
3. Read the SQL, the result table and the explanation.

Example questions:

- Show me total sales by product category
- Which region has the highest sales?
- اعرض إجمالي المبيعات لكل فئة منتج
- ما هي المنطقة الأعلى مبيعاً؟
