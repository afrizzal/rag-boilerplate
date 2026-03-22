"""
Ingest semua dokumen dari sebuah folder lokal ke database MySQL.

Cara pakai:
    python ingest.py ./my-docs
    python ingest.py C:/Users/saya/Documents/knowledge-base
    python ingest.py ./my-docs --clear   # hapus semua dokumen lama dulu
"""
import sys
import argparse
from pathlib import Path

# Pastikan app/ bisa di-import
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
import app.models  # noqa — register semua model
from app.models.document import Document
from app.services.document_processor import process_document

SUPPORTED = {'.pdf', '.txt', '.docx', '.doc'}


def scan_files(folder: Path) -> list[Path]:
    """Kumpulkan semua file yang didukung di dalam folder (termasuk subfolder)."""
    files = []
    for ext in SUPPORTED:
        files.extend(folder.rglob(f'*{ext}'))
    return sorted(files)


def ingest_folder(folder_path: str, clear: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    folder = Path(folder_path).resolve()
    if not folder.exists():
        print(f"[ERROR] Folder tidak ditemukan: {folder}")
        sys.exit(1)
    if not folder.is_dir():
        print(f"[ERROR] Path bukan folder: {folder}")
        sys.exit(1)

    files = scan_files(folder)
    if not files:
        print(f"[INFO] Tidak ada file yang didukung di: {folder}")
        print(f"       Format yang didukung: {', '.join(SUPPORTED)}")
        return

    # Hapus semua dokumen lama jika --clear
    if clear:
        count = db.query(Document).count()
        db.query(Document).delete()
        db.commit()
        print(f"[CLEAR] {count} dokumen lama dihapus.\n")

    print(f"[INFO] Ditemukan {len(files)} file di: {folder}")
    print("-" * 50)

    success, skipped, failed = 0, 0, 0

    for i, file_path in enumerate(files, 1):
        rel_path = file_path.relative_to(folder)
        print(f"[{i}/{len(files)}] {rel_path} ...", end=' ', flush=True)

        # Skip jika sudah ada di DB (berdasarkan nama file)
        existing = db.query(Document).filter(Document.title == str(rel_path)).first()
        if existing and not clear:
            print("SKIP (sudah ada)")
            skipped += 1
            continue

        try:
            file_bytes = file_path.read_bytes()
            ext = file_path.suffix.lstrip('.')

            document = Document(
                title=str(rel_path),
                file_type=ext,
                file_size=len(file_bytes),
            )
            db.add(document)
            db.flush()

            process_document(document, file_bytes, db)
            print(f"OK ({len(document.chunks)} chunks)")
            success += 1

        except Exception as e:
            db.rollback()
            print(f"GAGAL — {e}")
            failed += 1

    db.close()

    print("-" * 50)
    print(f"Selesai: {success} berhasil | {skipped} dilewati | {failed} gagal")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ingest dokumen dari folder lokal ke RAG database.')
    parser.add_argument('folder', help='Path ke folder berisi dokumen')
    parser.add_argument('--clear', action='store_true', help='Hapus semua dokumen lama sebelum ingest')
    args = parser.parse_args()

    ingest_folder(args.folder, clear=args.clear)
