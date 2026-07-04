"""
test_fk_integrity.py
Referential integrity within the dataset and back to the sibling
commission_formation work-programme table.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
import config

OUTPUT_DIR = config.OUTPUT_DIR


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        pytest.skip(f"{path.name} not found")
    return pd.read_csv(path)


def _out(name: str) -> pd.DataFrame:
    return load_csv(OUTPUT_DIR / name)


class TestForeignKeys:

    def test_refs_agenda_ids_valid(self):
        agenda = _out("agenda_items.csv")
        refs = _out("procedure_references.csv")
        invalid = set(refs["agenda_item_id"]) - set(agenda["agenda_item_id"])
        assert not invalid, f"procedure_references agenda_ids not in agenda_items: {invalid}"

    def test_status_ref_ids_valid(self):
        refs = _out("procedure_references.csv")
        status = _out("procedure_status.csv")
        invalid = set(status["procedure_ref_id"]) - set(refs["procedure_ref_id"])
        assert not invalid, f"procedure_status ref_ids not in procedure_references: {invalid}"

    def test_status_agenda_ids_valid(self):
        agenda = _out("agenda_items.csv")
        status = _out("procedure_status.csv")
        invalid = set(status["agenda_item_id"]) - set(agenda["agenda_item_id"])
        assert not invalid, f"procedure_status agenda_ids not in agenda_items: {invalid}"

    def test_evaluations_agenda_ids_valid(self):
        agenda = _out("agenda_items.csv")
        evals = _out("evaluations.csv")
        invalid = set(evals["agenda_item_id"]) - set(agenda["agenda_item_id"])
        assert not invalid, f"evaluations agenda_ids not in agenda_items: {invalid}"


class TestSiblingLink:
    """The agenda spine must link back to the commission_formation dataset."""

    def test_wp_item_ids_exist_in_sibling(self):
        if not config.WORK_PROGRAMME_CSV.exists():
            pytest.skip("Sibling work_programme_items.csv not found")
        wp = pd.read_csv(config.WORK_PROGRAMME_CSV)
        agenda = _out("agenda_items.csv")
        linked = agenda["wp_item_id"].dropna().astype(str)
        linked = linked[linked != ""]
        invalid = set(linked) - set(wp["item_id"].astype(str))
        assert not invalid, f"agenda wp_item_ids not in sibling work programme: {invalid}"
