"""Audit assertions for the selected owner release records (xlsx).

Tests 1-7 require the provider package (kept outside this repository) and
verify the frozen xlsx against it. The final class runs everywhere.
"""
import csv
import json
import re
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scenarios.owner_records_select import (        # noqa: E402
    parse_xlsx, select, sha256_file, RAW_DEFAULT, OUT_DEFAULT, XLSX_NAME,
    INCLUDED_RELEASES, OUTPUT_COLUMNS)
from scenarios.build_case import build, ZH_ANCHORS    # noqa: E402
from verifier.closure_audit import verify, sha       # noqa: E402

RAW = RAW_DEFAULT
SRC = RAW / XLSX_NAME
OUT = OUT_DEFAULT
XLSX = OUT / 'owner_release_records.xlsx'
ARCHIVE = Path(__file__).resolve().parents[1] / 'runs' / 'zh_retro'
CJK = re.compile(r'[\u4e00-\u9fff]')
ZH_IDS = tuple(sorted(ZH_ANCHORS))


def sheet_rows():
    _hdr, rows = parse_xlsx(XLSX)
    return rows


@unittest.skipUnless(SRC.is_file(), 'provider package present (kept outside this repository)')
class TestOwnerPackageAssertions(unittest.TestCase):

    def test_1_selected_rows_are_verbatim(self):
        _hdr, src_rows = parse_xlsx(SRC)
        src_by_op = {r['operation_id']: r for r in src_rows}
        for e in sheet_rows():
            src = src_by_op[e['operation_id']]
            for col in OUTPUT_COLUMNS:
                got = e[col]
                want = src[col]
                if col == 'role_at_time':
                    # declared vocabulary translation
                    from scenarios.owner_records_select import ROLE_EN
                    self.assertEqual(got, ROLE_EN[want], e['operation_id'])
                else:
                    self.assertEqual(got, want, f'{e["operation_id"]}.{col}')

    def test_2_selection_is_audited_releases_only(self):
        rows = sheet_rows()
        self.assertEqual(len(rows), 31)
        self.assertEqual({r['release_id'] for r in rows}, INCLUDED_RELEASES)

    def test_3_english_surface(self):
        for e in sheet_rows():
            for col in OUTPUT_COLUMNS:
                self.assertIsNone(CJK.search(e[col]), f'{e["signal_id"]}.{col}')

    def test_4_all_three_releases_present(self):
        rows = sheet_rows()
        from scenarios.owner_records_select import INCLUDED_RELEASES
        for rel in INCLUDED_RELEASES:
            self.assertTrue(any(r['release_id'] == rel for r in rows), rel)

    def test_5_case_closure_against_xlsx(self):
        rows = sheet_rows()
        for sid in ZH_IDS:
            case = build(sid)
            rel = ZH_ANCHORS[sid]['release']
            want = {r['signal_id'] for r in rows if r['release_id'] == rel}
            self.assertEqual({s['signal_id'] for s in case['raw_signals']}, want, sid)

    def test_6_replay_reproduces_xlsx(self):
        with tempfile.TemporaryDirectory() as td:
            select(RAW, Path(td))
            a = sha256_file(XLSX)
            b = sha256_file(Path(td) / 'owner_release_records.xlsx')
            self.assertEqual(a, b)

    def test_7_source_hash_matches_provider_manifest(self):
        import csv as _csv
        v23 = list(_csv.DictReader((RAW / 'received_manifests' / 'v23_source_manifest.csv')
                                   .read_text(encoding='utf-8-sig').splitlines()))[0]
        self.assertEqual(v23['file_sha256'], sha256_file(SRC))


class TestZhAdjudicationsReproducible(unittest.TestCase):
    """Runs in public clones (the xlsx ships with the repo)."""

    def test_verdicts_match_archived_results(self):
        for sid in ZH_IDS:
            result = verify(build(sid))
            self.assertEqual(result['input_sha256'], sha(build(sid)))
            archived = ARCHIVE / sid / 'result.json'
            if archived.is_file():
                want = json.loads(archived.read_text(encoding='utf-8'))
                self.assertEqual(result['machine_decision'], want['machine_decision'], sid)
                self.assertEqual(result['failure_codes'], want['failure_codes'], sid)
            else:
                self.assertIn(result['machine_decision'], ('OPEN', 'CLOSED'), sid)


if __name__ == '__main__':
    unittest.main()
