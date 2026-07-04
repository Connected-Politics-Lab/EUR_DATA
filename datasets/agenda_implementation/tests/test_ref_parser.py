"""
test_ref_parser.py
Unit tests for the procedure-reference parser on real interleaved CWP prose.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.refs import extract_refs, to_process_id, canonical_ref


class TestToProcessId:
    @pytest.mark.parametrize("ref,expected", [
        ("2011/0314(CNS)", "2011-0314"),
        ("2018/0063B(COD)", "2018-0063B"),
        ("2024/0094(NLE)", "2024-0094"),
    ])
    def test_conversion(self, ref, expected):
        assert to_process_id(ref) == expected


class TestCanonicalRef:
    def test_zero_pads_number(self):
        assert canonical_ref("2012", "336", "APP") == "2012/0336(APP)"

    def test_preserves_letter_variant(self):
        assert canonical_ref("2018", "63B", "COD") == "2018/0063B(COD)"


class TestExtractRefs:
    def test_interleaved_annex_iv_row(self):
        # Real-shape WP073 prose: COM ref and procedure number split by title text.
        text = ("COM(2011)714 final Proposal for a COUNCIL DIRECTIVE on a common "
                "system of taxation 2011/0314 (CNS) applicable to interest and "
                "royalty payments")
        refs = extract_refs(text)
        assert len(refs) == 1
        r = refs[0]
        assert r["interinstitutional_ref"] == "2011/0314(CNS)"
        assert r["process_id_ep"] == "2011-0314"
        assert r["procedure_type"] == "CNS"
        assert r["com_reference"] == "COM(2011)714"

    def test_letter_variant_row(self):
        text = "COM(2018)135 final ... 2018/0063B (COD) THE COUNCIL on credit servicers"
        refs = extract_refs(text)
        assert refs[0]["interinstitutional_ref"] == "2018/0063B(COD)"
        assert refs[0]["process_id_ep"] == "2018-0063B"

    def test_join_proposal(self):
        text = "JOIN(2015)36 final Joint Proposal ... 2015/0302 (NLE) European Union"
        refs = extract_refs(text)
        assert refs[0]["com_reference"] == "JOIN(2015)36"
        assert refs[0]["procedure_type"] == "NLE"

    def test_no_reference(self):
        assert extract_refs("Competitiveness and Decarbonisation") == []

    def test_dedup_repeated_ref(self):
        text = "2023/0133(COD) ... and again 2023/0133 (COD)"
        assert len(extract_refs(text)) == 1
