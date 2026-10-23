from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
import assistant
import database
import loader

app = FastAPI(title="Voice Data Analysis API")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "index.html")


class Question(BaseModel):
    question: str


class SQLQuery(BaseModel):
    sql: str


def run_pipeline(question):
    try:
        schema = database.get_schema()
    except ValueError as e:
        raise HTTPException(400, str(e))

    sql = assistant.generate_sql(question, schema)
    try:
        columns, rows = database.run_sql(sql)
    except Exception as first_error:
        # one retry: tell the LLM what went wrong
        sql = assistant.generate_sql(
            question, schema, error=f"Previous SQL: {sql}\nError: {first_error}"
        )
        try:
            columns, rows = database.run_sql(sql)
        except Exception as e:
            raise HTTPException(400, f"Could not run the generated SQL ({e}). SQL was: {sql}")

    explanation = assistant.explain_result(question, sql, columns, rows)
    return {
        "question": question,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "explanation": explanation,
    }


def transcribe_upload(file, language):
    text, lang = loader.transcribe_file(file.file.read(), file.filename or "audio.wav", language)
    if not text:
        raise HTTPException(400, "No speech found in the audio")
    return text, lang


@app.post("/dataset")
def upload_dataset(file: UploadFile = File(...)):
    try:
        return database.load_dataset(file.file.read(), file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/schema")
def schema():
    try:
        return {"schema": database.get_schema()}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/transcribe")
def transcribe(file: UploadFile = File(...), language: Optional[str] = None):
    text, lang = transcribe_upload(file, language)
    return {"text": text, "language": lang}


@app.post("/generate-sql")
def generate_sql(body: Question):
    try:
        schema = database.get_schema()
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"sql": assistant.generate_sql(body.question, schema)}


@app.post("/execute-sql")
def execute_sql(body: SQLQuery):
    try:
        columns, rows = database.run_sql(body.sql)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"columns": columns, "rows": rows}


@app.post("/ask-text")
def ask_text(body: Question):
    return run_pipeline(body.question)


@app.post("/ask-voice")
def ask_voice(file: UploadFile = File(...), language: Optional[str] = None):
    text, lang = transcribe_upload(file, language)
    return {"transcript": text, "language": lang, **run_pipeline(text)}