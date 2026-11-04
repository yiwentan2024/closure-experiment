"""Run the three ZH retrospective audits locally and archive verdicts.

For each ZH scenario: build the case from the frozen owner-record ledger
(scenarios/owner_records), run the B2 closure auditor, and archive
case.json / result.json / B0 record review / B1 N-A record under
runs/zh_retro/<scenario>/.  ZH cases are adjudication records: B0 reviews the
recorded gate evidence, B1 is N/A per the batch specification (the original
system deployed no attestation tooling), B2 adjudicates. No injection step.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scenarios.build_case import build, SCENARIOS   # noqa: E402
from verifier.closure_audit import verify            # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs' / 'zh_retro'
R4_IDENTITY_NOTE = (
    'Signal SIG-FB-260820-010 is identity-pending: the workbook records it as a\n'
    'deployment on 2026-08-18 14:12 (local) while the R4 voucher records a change\n'
    'event for the same id on 2026-08-20 (EXCLUDED_AS_DUPLICATE_IDENTITY by the\n'
    'data producer). The ledger follows the producer\'s standing exclusion; the\n'
    'conflict is retained here as the ZH-R4 subject matter.')


def b0_review(sid, case):
    gates = case['gates']
    lines = [f'# B0 record review — {sid}', '',
             'Re-verification of the source system\'s recorded gate evidence',
             '(release %s, cutoff %s). No gates were re-executed; the records'
             % (case['release_id'], case['source_cutoff']),
             'are reviewed as recorded in the owner ledger.', '']
    if not gates:
        lines.append('No approval/deployment records found for this release -> no gate evidence.')
    for g in gates:
        lines.append(f"- gate {g['gate_id']}: {g['status']} at {g['evaluated_at']}")
    if sid == 'ZH-R4':
        lines += ['', '## Identity-pending signal', R4_IDENTITY_NOTE]
    return '\n'.join(lines) + '\n'


B1_NA = """# B1 record — N/A

The original system did not deploy artifact-attestation tooling; per the batch
specification, B1 reports N/A for ZH retrospective cases rather than claiming a
miss. The owner ledger carries no attestation artifacts.
"""


def main():
    results = {}
    for sid in sorted(SCENARIOS):
        if not SCENARIOS[sid]['source'].startswith('REAL_'):
            continue
        case = build(sid)
        result = verify(case)
        d = OUT / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / 'case.json').write_text(json.dumps(case, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                                     encoding='utf-8')
        (d / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                                       encoding='utf-8')
        (d / 'B0_record_review.md').write_text(b0_review(sid, case), encoding='utf-8')
        (d / 'B1_na.md').write_text(B1_NA, encoding='utf-8')
        results[sid] = result
        print(f"{sid}: {result['machine_decision']}/{result['evidence_status']} "
              f"codes={result['failure_codes']}")
    print(f"\narchived under {OUT}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
