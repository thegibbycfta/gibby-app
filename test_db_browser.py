#!/usr/bin/env python3
"""Tests for the read-only admin database browser helpers."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

import db_browser


class DatabaseBrowserTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE people (
                id INTEGER PRIMARY KEY, name TEXT, password_hash TEXT,
                access_token TEXT, document_b64 TEXT, notes TEXT
            );
            INSERT INTO people VALUES
                (1, 'Ada', 'hash-one', 'token-one', 'file-one', 'first'),
                (2, 'Grace', 'hash-two', 'token-two', 'file-two', 'second'),
                (3, 'Katherine', 'hash-three', 'token-three', 'file-three', 'third');
            CREATE TABLE "odd"" table" (id INTEGER PRIMARY KEY, value TEXT);
            INSERT INTO "odd"" table" VALUES (1, 'safe identifier');
            CREATE TABLE secrets_only (token_id INTEGER PRIMARY KEY, token TEXT, image_b64 TEXT) WITHOUT ROWID;
            INSERT INTO secrets_only VALUES (1, 'secret-token', 'encoded-image');
            CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
            INSERT INTO meta VALUES ('mail_bridge_key', 'private-key-value');
        """)

    def tearDown(self):
        self.conn.close()

    def test_table_summaries_omit_internal_sqlite_tables(self):
        names = {table["name"] for table in db_browser.table_summaries(self.conn)}
        self.assertIn("people", names)
        self.assertIn('odd" table', names)
        self.assertNotIn("sqlite_sequence", names)

    def test_sensitive_columns_are_redacted(self):
        result = db_browser.table_page(self.conn, "people")
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["rows"][0]["name"], "Ada")
        self.assertEqual(result["rows"][0]["password_hash"], db_browser.REDACTED)
        self.assertEqual(result["rows"][0]["access_token"], db_browser.REDACTED)
        self.assertEqual(result["rows"][0]["document_b64"], db_browser.REDACTED)

    def test_search_is_parameterized_and_pagination_is_bounded(self):
        self.conn.executemany(
            "INSERT INTO people(id,name) VALUES(?,?)",
            [(i, f"Person {i}") for i in range(4, 64)],
        )
        page = db_browser.table_page(self.conn, "people", page=2)
        self.assertEqual(page["page"], 2)
        self.assertEqual(page["total"], 63)
        injected = db_browser.table_page(self.conn, "people", search="%' OR 1=1 --")
        self.assertEqual(injected["total"], 0)
        with self.assertRaises(KeyError):
            db_browser.table_page(self.conn, 'people"; DROP TABLE people; --')
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM people").fetchone()[0], 63)

    def test_search_excludes_redacted_columns(self):
        result = db_browser.table_page(self.conn, "people", search="hash-one")
        self.assertEqual(result["total"], 0)

    def test_tables_with_only_redacted_columns_still_page(self):
        result = db_browser.table_page(self.conn, "secrets_only")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["rows"], [{
            "token_id": db_browser.REDACTED,
            "token": db_browser.REDACTED,
            "image_b64": db_browser.REDACTED,
        }])

    def test_generic_meta_values_are_redacted(self):
        result = db_browser.table_page(self.conn, "meta")
        self.assertEqual(result["rows"][0]["k"], "mail_bridge_key")
        self.assertEqual(result["rows"][0]["v"], db_browser.REDACTED)

    def test_values_are_truncated_and_binary_is_summarized(self):
        self.conn.execute("ALTER TABLE people ADD COLUMN attachment BLOB")
        self.conn.execute("UPDATE people SET attachment=? WHERE id=1", (b"12345",))
        self.conn.execute("UPDATE people SET notes=? WHERE id=1", ("x" * (db_browser.MAX_CELL_LENGTH + 10),))
        row = db_browser.table_page(self.conn, "people")["rows"][0]
        self.assertEqual(row["attachment"], "[binary: 5 bytes]")
        self.assertTrue(row["notes"].endswith("[truncated]"))

    def test_open_readonly_rejects_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "readonly.db"
            writable = sqlite3.connect(path)
            writable.execute("CREATE TABLE sample (id INTEGER)")
            writable.commit()
            writable.close()
            readonly = db_browser.open_readonly(path)
            try:
                with self.assertRaises(sqlite3.DatabaseError):
                    readonly.execute("DELETE FROM sample")
            finally:
                readonly.close()


if __name__ == "__main__":
    unittest.main()