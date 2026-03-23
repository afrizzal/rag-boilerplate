"""
Text-to-SQL Service

Alur:
1. Gemini baca pertanyaan + instruksi schema → generate SQL (atau None)
2. Validasi SQL: hanya SELECT, blok keyword berbahaya
3. Eksekusi ke MIS DB dengan batas baris & timeout
4. Format hasil jadi teks untuk dimasukkan ke prompt jawaban final
"""
import re
import json
import google.generativeai as genai
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db_mis import get_mis_engine

# ── Keyword yang diblok (keamanan) ────────────────────────────────────────────

BLOCKED_KEYWORDS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b',
    r'\bCREATE\b', r'\bALTER\b', r'\bTRUNCATE\b', r'\bREPLACE\b',
    r'\bGRANT\b', r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b',
    r'\bCALL\b', r'\bLOAD\b', r'\bOUTFILE\b', r'\bDUMPFILE\b',
    r'--', r'/\*',  # SQL comment injection
]


# ── SQL Generation ─────────────────────────────────────────────────────────────

def generate_sql(question: str, schema_instructions: str) -> str | None:
    """
    Minta Gemini generate SQL berdasarkan pertanyaan dan schema.
    Return SQL string, atau None jika pertanyaan tidak butuh data dari DB.
    """
    if not settings.gemini_api_key:
        return None

    prompt = f"""Kamu adalah ahli SQL untuk database MySQL.

Berikut adalah informasi schema database yang tersedia:
{schema_instructions}

Tugasmu:
- Jika pertanyaan berikut membutuhkan data dari database, tulis query MySQL SELECT yang tepat.
- Jika pertanyaan tidak membutuhkan query database (misalnya pertanyaan konseptual, prosedur, atau sudah bisa dijawab dari dokumen), kembalikan tepat kata: NO_QUERY

Aturan wajib:
1. Hanya boleh menggunakan SELECT — tidak boleh INSERT, UPDATE, DELETE, DROP, dll.
2. Selalu tambahkan LIMIT {settings.mis_query_max_rows} jika belum ada.
3. Gunakan alias kolom yang jelas dan mudah dibaca (contoh: COUNT(*) AS jumlah_kunjungan).
4. Jangan tambahkan penjelasan apapun — kembalikan HANYA query SQL atau NO_QUERY.

Pertanyaan: {question}

SQL atau NO_QUERY:"""

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt)
    result = response.text.strip()

    if result.upper() == 'NO_QUERY' or not result:
        return None

    # Bersihkan markdown code block jika ada
    result = re.sub(r'^```sql\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'^```\s*', '', result)
    result = re.sub(r'\s*```$', '', result)

    return result.strip()


# ── SQL Validation ─────────────────────────────────────────────────────────────

def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validasi SQL sebelum dieksekusi.
    Return (valid, pesan_error).
    """
    sql_upper = sql.upper().strip()

    # Harus dimulai dengan SELECT
    if not sql_upper.startswith('SELECT'):
        return False, "Query harus diawali dengan SELECT."

    # Blok keyword berbahaya
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, sql_upper):
            keyword = pattern.replace(r'\b', '').replace('\\b', '')
            return False, f"Keyword '{keyword}' tidak diizinkan."

    return True, ''


# ── SQL Execution ──────────────────────────────────────────────────────────────

def execute_sql(sql: str) -> tuple[list[dict], str | None]:
    """
    Eksekusi SQL ke MIS DB.
    Return (rows, error_message).
    rows adalah list of dict {kolom: nilai}.
    """
    engine = get_mis_engine()
    if engine is None:
        return [], "Koneksi MIS DB tidak aktif (MIS_DB_ENABLED=False)."

    is_valid, err = validate_sql(sql)
    if not is_valid:
        return [], f"SQL tidak valid: {err}"

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows, None
    except SQLAlchemyError as e:
        return [], f"Error eksekusi query: {str(e)}"


# ── Format Results ─────────────────────────────────────────────────────────────

def format_results(sql: str, rows: list[dict]) -> str:
    """Ubah hasil query menjadi teks yang mudah dibaca oleh Gemini."""
    if not rows:
        return "Query berhasil dieksekusi tetapi tidak mengembalikan data."

    # Jika hanya 1 baris dan 1 kolom → tampilkan sederhana
    if len(rows) == 1 and len(rows[0]) == 1:
        key, val = next(iter(rows[0].items()))
        return f"{key}: {val}"

    # Format tabel sederhana
    headers = list(rows[0].keys())
    lines = [' | '.join(headers)]
    lines.append('-' * len(lines[0]))
    for row in rows:
        lines.append(' | '.join(str(v) for v in row.values()))

    suffix = f"\n(Total: {len(rows)} baris)" if len(rows) > 1 else ''
    return '\n'.join(lines) + suffix


# ── Pipeline Utama ─────────────────────────────────────────────────────────────

def run_text_to_sql(question: str, schema_instructions: str) -> dict:
    """
    Pipeline lengkap Text-to-SQL.
    Return dict dengan sql, rows, formatted_result, dan error (jika ada).
    """
    result = {
        'sql': None,
        'rows': [],
        'formatted_result': None,
        'row_count': 0,
        'error': None,
    }

    # 1. Generate SQL
    sql = generate_sql(question, schema_instructions)
    if not sql:
        return result  # pertanyaan tidak butuh query DB

    result['sql'] = sql

    # 2. Eksekusi
    rows, error = execute_sql(sql)
    if error:
        result['error'] = error
        return result

    # 3. Format
    result['rows'] = rows
    result['row_count'] = len(rows)
    result['formatted_result'] = format_results(sql, rows)
    return result
