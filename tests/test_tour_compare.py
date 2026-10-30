import copy
import io
import json
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import tour_compare as app


def intent(**changes):
    value = {"in_scope": True, "tour_ids": [], "criteria": [], "constraints": {}, "clear": [], "unsupported": []}
    value.update(changes)
    return value


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tours = app.load_catalogue()
        cls.by_id = {t["id"]: t for t in cls.tours}

    def test_budget_includes_mandatory_extras(self):
        violations, _ = app.check_constraints(self.by_id["T01"], {"max_price": 5500})
        self.assertIn("price", violations)

    def test_exact_budget_boundary_is_allowed(self):
        self.assertEqual(app.check_constraints(self.by_id["T01"], {"max_price": 5800}), ([], []))

    def test_unspecified_fee_does_not_become_zero(self):
        self.assertEqual(app.check_constraints(self.by_id["T03"], {"max_price": 5000}), ([], ["mandatory_fee"]))

    def test_base_price_alone_can_disqualify_unknown_total(self):
        self.assertEqual(app.check_constraints(self.by_id["T03"], {"max_price": 4000}), (["price"], []))

    def test_unknown_overnight_travel_is_not_confirmed_safe(self):
        self.assertEqual(app.check_constraints(self.by_id["T07"], {"avoid_overnight_bus": True}), ([], ["overnight_bus"]))

    def test_false_requirement_removes_restriction(self):
        self.assertEqual(app.check_constraints(self.by_id["T07"], {"avoid_overnight_bus": False}), ([], []))

    def test_explicit_selection_retains_excluded_option(self):
        state = app.update_state(app.new_state(), intent(tour_ids=["T01", "T02"], constraints={"avoid_overnight_bus": True}))
        rows = app.compare(self.tours, state)["rows"]
        self.assertEqual([(r["tour"]["id"], r["status"]) for r in rows], [("T02", "eligible"), ("T01", "excluded")])

    def test_search_hides_disqualified_options_and_limits_results(self):
        state = app.update_state(app.new_state(), intent(constraints={"destination": "Kapadokya", "avoid_overnight_bus": True}))
        rows = app.compare(self.tours, state)["rows"]
        self.assertEqual([r["tour"]["id"] for r in rows], ["T02", "T04"])

    def test_impossible_constraints_return_no_matches(self):
        state = app.update_state(app.new_state(), intent(constraints={"max_price": 1000, "min_nights": 5}))
        self.assertEqual(app.compare(self.tours, state)["rows"], [])

    def test_normalisation_supports_turkish_cities(self):
        self.assertEqual(app.check_constraints(self.by_id["T01"], {"departure": "istanbul", "destination": "KAPADOKYA"}), ([], []))

    def test_followup_retains_ids_budget_and_earlier_conditions(self):
        first = app.update_state(app.new_state(), intent(tour_ids=["T01", "T02"], constraints={"max_price": 8000}))
        second = app.update_state(first, intent(criteria=["breakfast"], constraints={"avoid_overnight_bus": True, "max_price": None}))
        self.assertEqual(second["tour_ids"], ["T01", "T02"])
        self.assertEqual(second["constraints"], {"max_price": 8000, "avoid_overnight_bus": True})
        self.assertNotIn("avoid_overnight_bus", first["constraints"])

    def test_explicit_constraint_removal(self):
        state = app.update_state(app.new_state(), intent(constraints={"max_price": 8000, "min_nights": 2}))
        state = app.update_state(state, intent(clear=["max_price"]))
        self.assertEqual(state["constraints"], {"min_nights": 2})

    def test_new_destination_clears_previous_selection(self):
        state = app.update_state(app.new_state(), intent(tour_ids=["T01", "T02"]))
        state = app.update_state(state, intent(constraints={"destination": "Ege"}))
        self.assertEqual(state["tour_ids"], [])

    def test_unrelated_question_preserves_state(self):
        state = app.update_state(app.new_state(), intent(tour_ids=["T01"], constraints={"max_price": 8000}))
        self.assertEqual(app.update_state(state, intent(in_scope=False, clear=["max_price"])), state)

    def test_order_of_input_options_does_not_change_comparison(self):
        a = app.compare(self.tours, app.update_state(app.new_state(), intent(tour_ids=["T01", "T02"])))
        b = app.compare(self.tours, app.update_state(app.new_state(), intent(tour_ids=["T02", "T01"])))
        self.assertEqual(a["rows"], b["rows"])

    def test_evidence_references_and_missing_information_are_visible(self):
        state = app.update_state(app.new_state(), intent(tour_ids=["T03"], criteria=["breakfast", "price"]))
        text = app.render(app.compare(self.tours, state), intent())
        self.assertIn("[T03:price]", text)
        self.assertIn("Belirtilmemiş", text)
        self.assertIn("Kesin toplam hesaplanamıyor", text)
        self.assertNotIn("[T03:breakfast]", text)

    def test_catalogue_rejects_evidence_not_found_in_description(self):
        data = json.loads((app.ROOT / "data/tours.json").read_text(encoding="utf-8"))
        data["tours"][0]["facts"]["price"]["evidence"] = "fabricated evidence"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(app.AppError):
                app.load_catalogue(path)

    def test_intent_rejects_invented_ids_and_bool_as_integer(self):
        for bad in (intent(tour_ids=["T99"]), intent(constraints={"max_price": True}), intent(tour_ids=[{}])):
            with self.subTest(bad=bad), self.assertRaises(app.AppError):
                app.validate_intent(bad, self.tours)

    def test_four_options_and_unknown_ids_are_rejected_before_model_call(self):
        for text in ("T01 T02 T03 T04", "T99 turunu anlat"):
            with self.subTest(text=text), patch("urllib.request.urlopen") as request, self.assertRaises(app.AppError):
                app.ollama_intent(text, app.new_state(), self.tours)
            request.assert_not_called()

    def test_network_error_is_explicit_and_does_not_use_baseline(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")), self.assertRaisesRegex(app.AppError, "Ollama"):
            app.ollama_intent("T01 T02", app.new_state(), self.tours)

    def test_malformed_or_truncated_model_output_is_rejected(self):
        for response in ({"message": {"content": "not json"}}, {"done_reason": "length", "message": {"content": "{}"}}):
            data = io.BytesIO(json.dumps(response).encode())
            with patch("urllib.request.urlopen", return_value=data), self.assertRaises(app.AppError):
                app.ollama_intent("T01 T02", app.new_state(), self.tours)

    def test_once_list_and_source_exit_without_model(self):
        for question, fragment in (("/liste", "T20"), ("/kaynak T01", self.by_id["T01"]["description"]), ("/sifirla", "temizlendi")):
            output = io.StringIO()
            with self.subTest(question=question), redirect_stdout(output), patch("urllib.request.urlopen") as request:
                self.assertEqual(app.main(["--once", question]), 0)
                self.assertIn(fragment, output.getvalue())
                request.assert_not_called()

    def test_rules_mode_is_explicit_and_works_without_network(self):
        output = io.StringIO()
        with redirect_stdout(output), patch("urllib.request.urlopen") as request:
            code = app.main(["--backend", "rules", "--once", "T01 ve T02 kahvaltı karşılaştır", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["metrics"]["backend"], "rules")
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
