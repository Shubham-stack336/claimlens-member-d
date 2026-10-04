import json

from eval.faults import build_probes, exact_match_grounding, run_benchmark
from eval.metrics import Count, case_verdict_agrees, recall_at_k
from eval.run import POLICY_PATH, load_cases, main


def test_count_reports_exact_numbers():
    c = Count()
    for ok in (True, True, False):
        c.add(ok)
    assert str(c) == "2 of 3"


def test_recall_at_k():
    assert recall_at_k(["6.1", "4.2", "5.1"], ["4.2"]) is True
    assert recall_at_k(["6.1", "5.1", "7.2", "4.2"], ["4.2"]) is False  # 4th place is outside top 3
    assert recall_at_k(["6.1"], []) is None  # no gold clause: not counted


def test_case_verdict_needs_every_reason_to_match():
    gold = [{"gold_verdict": "SUPPORTED"}, {"gold_verdict": "PARTIAL"}]
    assert case_verdict_agrees(["SUPPORTED", "PARTIAL"], gold)
    assert not case_verdict_agrees(["SUPPORTED", "SUPPORTED"], gold)
    assert not case_verdict_agrees(["SUPPORTED"], gold)


def test_dataset_meets_prd_rules():
    cases = load_cases()
    assert len(cases) >= 8
    assert all(c["synthetic"] for c in cases)
    supported = [c for c in cases if any(r["gold_verdict"] == "SUPPORTED" for r in c["reasons"])]
    assert len(supported) >= 3  # PRD: not biased toward "unsupported"


def test_probes_include_real_and_fake():
    probes = build_probes(POLICY_PATH.read_text(encoding="utf-8"))
    kinds = {p.kind for p in probes}
    assert {"real", "invented", "number_changed", "negated", "spliced"} <= kinds


def test_a_grounding_check_that_accepts_everything_catches_nothing():
    policy = POLICY_PATH.read_text(encoding="utf-8")
    result = run_benchmark(policy, grounding_fn=lambda quote, text: True)
    assert result["catch_rate"] == 0.0


def test_fallback_grounding_catches_all_fakes():
    policy = POLICY_PATH.read_text(encoding="utf-8")
    result = run_benchmark(policy, exact_match_grounding)
    assert result["catch_rate"] == 1.0
    assert result["false_alarms"] == 0


def test_full_run_with_predictions(tmp_path):
    predictions = {
        c["case_id"]: {"reasons": [
            {"retrieved_clause_ids": r["gold_clause_ids"], "verdict": r["gold_verdict"]}
            for r in c["reasons"]
        ]}
        for c in load_cases()
    }
    pred_file = tmp_path / "pred.json"
    pred_file.write_text(json.dumps(predictions))
    report = main(["--predictions", str(pred_file), "--out", str(tmp_path / "report.json")])
    assert report["pipeline"]["verdict_agreement_ratio"] == 1.0
    assert report["pipeline"]["recall_at_3_ratio"] == 1.0
    assert (tmp_path / "report.json").exists()
