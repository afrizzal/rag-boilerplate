"""
Seed instruksi sistem awal untuk RAG Chatbot.
Edit bagian INSTRUCTIONS di bawah sesuai dengan database MIS kamu.

Cara pakai:
    python seed_instructions.py              # tambah instruksi baru (skip yang sudah ada)
    python seed_instructions.py --replace    # timpa instruksi yang sudah ada
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine, Base
import app.models  # noqa
from app.models.instruction import SystemInstruction

# ═══════════════════════════════════════════════════════════════════════════════
# EDIT BAGIAN INI — sesuaikan dengan struktur database dan aturan bisnis kamu
# ═══════════════════════════════════════════════════════════════════════════════

INSTRUCTIONS = [

    # ── SCHEMA: pemetaan nama tabel & kolom ────────────────────────────────────
    {
        'name': 'schema_customer',
        'category': 'schema',
        'order': 1,
        'content': (
            'Tabel customer bernama mis_cust. '
            'Kolom utama: cust_id (ID unik), cust_name (nama), cust_phone (telepon), '
            'cust_dob (tanggal lahir), cust_gender (L/P), cust_created (tanggal daftar), '
            'branch_id (cabang).'
        ),
    },
    {
        'name': 'schema_visit',
        'category': 'schema',
        'order': 2,
        'content': (
            'Tabel kunjungan pasien bernama mis_visit. '
            'Kolom utama: visit_id, cust_id (FK ke mis_cust), visit_date (tanggal kunjungan), '
            'branch_id (cabang), therapist_id, treatment_id, visit_status (done/cancel/pending).'
        ),
    },
    {
        'name': 'schema_treatment',
        'category': 'schema',
        'order': 3,
        'content': (
            'Tabel treatment/layanan bernama mis_treatment. '
            'Kolom: treatment_id, treatment_name (nama layanan), treatment_category, price.'
        ),
    },
    {
        'name': 'schema_branch',
        'category': 'schema',
        'order': 4,
        'content': (
            'Tabel cabang bernama mis_branch. '
            'Kolom: branch_id, branch_name (nama cabang), branch_city, branch_status (active/inactive).'
        ),
    },
    {
        'name': 'schema_transaction',
        'category': 'schema',
        'order': 5,
        'content': (
            'Tabel transaksi bernama mis_transaction. '
            'Kolom: trx_id, visit_id (FK), cust_id (FK), trx_date, total_amount, '
            'payment_method (cash/transfer/card/voucher), trx_status (paid/refund/pending).'
        ),
    },

    # ── FORMULA: cara menghitung metrik bisnis ─────────────────────────────────
    {
        'name': 'formula_new_customer',
        'category': 'formula',
        'order': 1,
        'content': (
            'Customer baru (new customer) adalah customer yang melakukan kunjungan pertama kali '
            '(visit pertama dalam sejarah mis_visit). '
            'Cara menghitung: COUNT DISTINCT cust_id di mis_visit WHERE visit_date dalam periode tertentu '
            'AND cust_id tidak ada di mis_visit sebelum periode tersebut.'
        ),
    },
    {
        'name': 'formula_returning_customer',
        'category': 'formula',
        'order': 2,
        'content': (
            'Customer lama (returning customer) adalah customer yang sudah pernah berkunjung sebelumnya. '
            'Cara menghitung: total kunjungan dikurangi kunjungan customer baru dalam periode yang sama.'
        ),
    },
    {
        'name': 'formula_revenue',
        'category': 'formula',
        'order': 3,
        'content': (
            'Revenue/omzet dihitung dari SUM(total_amount) di mis_transaction '
            'WHERE trx_status = "paid" dalam periode tertentu.'
        ),
    },
    {
        'name': 'formula_visit_frequency',
        'category': 'formula',
        'order': 4,
        'content': (
            'Frekuensi kunjungan per customer = COUNT(visit_id) / COUNT(DISTINCT cust_id) '
            'dari mis_visit dalam periode tertentu dengan visit_status = "done".'
        ),
    },

    # ── RULE: aturan bisnis ────────────────────────────────────────────────────
    {
        'name': 'rule_active_customer',
        'category': 'rule',
        'order': 1,
        'content': (
            'Customer dianggap aktif jika memiliki minimal 1 kunjungan (visit_status = done) '
            'dalam 90 hari terakhir.'
        ),
    },
    {
        'name': 'rule_visit_status',
        'category': 'rule',
        'order': 2,
        'content': (
            'Kunjungan yang dihitung sebagai valid hanya yang memiliki visit_status = "done". '
            'Status "cancel" dan "pending" tidak dihitung dalam laporan.'
        ),
    },
    {
        'name': 'rule_branch_filter',
        'category': 'rule',
        'order': 3,
        'content': (
            'Jika pertanyaan tidak menyebut cabang tertentu, data diambil dari semua cabang '
            'dengan branch_status = "active".'
        ),
    },

    # ── CONTEXT: informasi umum bisnis ─────────────────────────────────────────
    {
        'name': 'context_business',
        'category': 'context',
        'order': 1,
        'content': (
            'Miracle Aesthetic Clinic adalah klinik kecantikan dan perawatan estetika '
            'dengan beberapa cabang. Sistem MIS (Miracle Management System) adalah ERP internal '
            'yang mengelola data customer, kunjungan, treatment, dan transaksi.'
        ),
    },
    {
        'name': 'context_fiscal_year',
        'category': 'context',
        'order': 2,
        'content': (
            'Tahun fiskal mengikuti tahun kalender (Januari - Desember). '
            'Laporan bulanan dihitung dari tanggal 1 sampai akhir bulan.'
        ),
    },
]

# ═══════════════════════════════════════════════════════════════════════════════


def seed(replace: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    added, updated, skipped = 0, 0, 0

    for data in INSTRUCTIONS:
        existing = db.query(SystemInstruction).filter(
            SystemInstruction.name == data['name']
        ).first()

        if existing:
            if replace:
                for key, val in data.items():
                    setattr(existing, key, val)
                updated += 1
            else:
                skipped += 1
            continue

        db.add(SystemInstruction(**data))
        added += 1

    db.commit()
    db.close()

    print(f"\nSelesai: {added} ditambahkan | {updated} diperbarui | {skipped} dilewati")
    print("Instruksi aktif akan otomatis disertakan di setiap prompt Gemini.\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed system instructions untuk RAG Chatbot.')
    parser.add_argument('--replace', action='store_true', help='Timpa instruksi yang sudah ada')
    args = parser.parse_args()
    seed(replace=args.replace)
