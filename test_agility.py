"""Standard-library regressions and finite-population oracle checks.

All scenarios are synthetic. They verify the declared bookkeeping model, not
empirical migration performance or independent ground truth about a blockchain.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from dataclasses import FrozenInstanceError
from fractions import Fraction

# -I omits the script directory. The release audit must separately verify that
# this explicitly added directory contains only the five allowlisted files.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agility import (Assessment, MechanismSupport, ObjectContinuity, Outcome,
                     TransitionAuthority, authority_effect, continuity_effect,
                     independent_success_effect)


def assessment(**changes):
    fields = dict(system="synthetic", scope="fixed 100-record population; deadline 2026-10-20",
                  evaluated_at="2026-10-20", mechanism=MechanismSupport.ACTIVATED,
                  continuity=ObjectContinuity.PRESERVED,
                  authority=TransitionAuthority.INCUMBENT_ONLY, population_known=100)
    fields.update(changes)
    return Assessment(**fields)


class IdentityTests(unittest.TestCase):
    def test_lost_controller_does_not_follow_from_continuity(self):
        for continuity in ObjectContinuity:
            with self.subTest(continuity=continuity):
                self.assertEqual(assessment(continuity=continuity).residual_count(), 100)

    def test_incumbent_success(self):
        self.assertEqual(assessment(r_incumbent=.2).residual_count(), 80)

    def test_full_incumbent_success(self):
        self.assertEqual(assessment(r_incumbent=1).residual_fraction(), 0)

    def test_partial_independent_success(self):
        a = assessment(authority=TransitionAuthority.INDEPENDENT_PATH,
                       r_incumbent=.5, q_independent=.5)
        self.assertEqual(a.residual_fraction(), Fraction(1, 4))
        self.assertEqual(a.residual_count(), 25)

    def test_independent_availability_does_not_supply_success(self):
        a = assessment(authority=TransitionAuthority.INDEPENDENT_PATH, r_incumbent=.2)
        self.assertEqual(a.residual_count(), 80)

    def test_complete_independent_success(self):
        a = assessment(authority=TransitionAuthority.INDEPENDENT_PATH, q_independent=1)
        self.assertEqual(a.residual_count(), 0)

    def test_no_path_no_success(self):
        self.assertEqual(assessment(authority=TransitionAuthority.NOBODY).residual_count(), 100)

    def test_missing_mechanism_without_successes(self):
        for mechanism in (MechanismSupport.NONE, MechanismSupport.PROPOSED,
                          MechanismSupport.IMPLEMENTED):
            with self.subTest(mechanism=mechanism):
                self.assertEqual(assessment(mechanism=mechanism).residual_count(), 100)

    def test_finite_population_oracle(self):
        # Independently enumerate disjoint success sets, including heterogeneous
        # weights and zero-weight members; compare their explicit complement.
        weights = [0, 2, 1, 7, 3, 1, 9, 4]
        total = sum(weights)
        for split in range(len(weights) + 1):
            for independent_end in range(split, len(weights) + 1):
                incumbent = set(range(split))
                independent = set(range(split, independent_end))
                remainder = set(range(len(weights))) - incumbent
                r = Fraction(sum(weights[i] for i in incumbent), total)
                remainder_weight = sum(weights[i] for i in remainder)
                q = (Fraction(sum(weights[i] for i in independent), remainder_weight)
                     if remainder_weight else Fraction(0))
                expected = sum(weights[i] for i in range(len(weights))
                               if i not in incumbent | independent)
                with self.subTest(split=split, end=independent_end):
                    a = assessment(population_known=len(weights), weighting="value",
                                   weight_known=total, weight_unit="synthetic units",
                                   authority=TransitionAuthority.INDEPENDENT_PATH,
                                   r_incumbent=r, q_independent=q)
                    self.assertEqual(a.residual_amount(), expected)

    def test_equal_weight_population_oracle(self):
        objects = set(range(12))
        for incumbent_count in range(13):
            for independent_count in range(13 - incumbent_count):
                incumbent = set(range(incumbent_count))
                remainder = objects - incumbent
                independent = set(sorted(remainder)[:independent_count])
                q = Fraction(independent_count, len(remainder)) if remainder else 0
                with self.subTest(incumbent=incumbent_count, independent=independent_count):
                    a = assessment(population_known=12,
                                   authority=TransitionAuthority.INDEPENDENT_PATH,
                                   r_incumbent=Fraction(incumbent_count, 12), q_independent=q)
                    self.assertEqual(a.residual_count(), len(objects - incumbent - independent))

    def test_monotonicity_for_fixed_assumptions(self):
        for r in (Fraction(i, 10) for i in range(10)):
            values = [assessment(authority=TransitionAuthority.INDEPENDENT_PATH,
                                 r_incumbent=r, q_independent=Fraction(i, 10)).residual_fraction()
                      for i in range(11)]
            self.assertEqual(values, sorted(values, reverse=True))
        values = [assessment(r_incumbent=Fraction(i, 10)).residual_fraction() for i in range(11)]
        self.assertEqual(values, sorted(values, reverse=True))


class PrecisionAndUnitsTests(unittest.TestCase):
    def test_billion_object_tail_does_not_round_to_zero(self):
        a = assessment(population_known=10**9, r_incumbent=.9999999)
        self.assertEqual(a.residual_fraction(), Fraction(1, 10**7))
        self.assertEqual(a.residual_count(), 100)

    def test_arbitrarily_small_exact_tail(self):
        a = assessment(population_known=10**500, r_incumbent=1-Fraction(1, 10**500))
        self.assertEqual(a.residual_count(), 1)

    def test_float_decimal_interpretation(self):
        self.assertEqual(assessment(r_incumbent=.1).r_incumbent, Fraction(1, 10))

    def test_fractional_equivalents_never_round_to_count(self):
        a = assessment(population_known=1, r_incumbent=.75)
        self.assertEqual(a.residual_amount(), Fraction(1, 4))
        with self.assertRaises(ValueError):
            a.residual_count()
        self.assertIsNone(a.report()["integral_object_equivalents"])

    def test_value_weight_never_becomes_object_count(self):
        a = assessment(weighting="value", weight_known=10000, weight_unit="USD", r_incumbent=.5)
        self.assertEqual(a.residual_amount(), 5000)
        self.assertEqual(a.report()["amount_unit"], "USD")
        self.assertIsNone(a.report()["integral_object_equivalents"])
        with self.assertRaises(ValueError):
            a.residual_count()

    def test_authority_path_weight(self):
        a = assessment(weighting="authority_paths", weight_known=300,
                       weight_unit="paths", r_incumbent=Fraction(1, 3))
        self.assertEqual(a.residual_amount(), 200)


class ValidationTests(unittest.TestCase):
    def test_invalid_fractions(self):
        for field in ("r_incumbent", "q_independent", "disabled_fraction"):
            for value in (-.1, 1.1, float("nan"), float("inf"), -float("inf"), True,
                          "0.5", None, complex(.5)):
                if field == "disabled_fraction" and value is None:
                    continue
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    assessment(**{field: value})

    def test_invalid_population_counts(self):
        for field in ("population_known", "population_believed_total"):
            for value in (-1, .5, True, "100", float("nan"), float("inf")):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    assessment(**{field: value})

    def test_total_below_known(self):
        with self.assertRaises(ValueError):
            assessment(population_believed_total=99)

    def test_no_authority_rejects_success(self):
        for field in ("r_incumbent", "q_independent"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                assessment(authority=TransitionAuthority.NOBODY, **{field: .1})

    def test_no_mechanism_rejects_success_not_overrides_it(self):
        for mechanism in (MechanismSupport.NONE, MechanismSupport.PROPOSED,
                          MechanismSupport.IMPLEMENTED):
            for field in ("r_incumbent", "q_independent"):
                with self.subTest(mechanism=mechanism, field=field), self.assertRaises(ValueError):
                    assessment(mechanism=mechanism, authority=TransitionAuthority.INDEPENDENT_PATH,
                               **{field: .5})

    def test_independent_success_needs_path(self):
        with self.assertRaises(ValueError):
            assessment(q_independent=.1)

    def test_empty_remainder_q_is_canonical_zero(self):
        with self.assertRaises(ValueError):
            assessment(authority=TransitionAuthority.INDEPENDENT_PATH, r_incumbent=1,
                       q_independent=.1)

    def test_invalid_enums_rejected_early(self):
        for field, value in (("mechanism", "ACTIVATED"), ("continuity", None),
                             ("authority", "INDEPENDENT_PATH")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                assessment(**{field: value})

    def test_metadata(self):
        for fields in ({"scope": " "}, {"system": None}, {"weighting": "money"},
                       {"evaluated_at": "2026-02-30"}, {"evaluated_at": "20261020"},
                       {"assumptions": "text"}, {"assumptions": [""]}, {"note": None}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                assessment(**fields)

    def test_non_object_weight_validation(self):
        for fields in ({}, {"weight_known": 100}, {"weight_unit": "USD"},
                       {"weight_known": -1, "weight_unit": "USD"},
                       {"weight_known": 0, "weight_unit": "USD"},
                       {"weight_known": float("inf"), "weight_unit": "USD"},
                       {"weight_known": True, "weight_unit": "USD"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                assessment(weighting="value", **fields)

    def test_object_weight_cannot_override_count(self):
        for fields in ({"weight_known": 100}, {"weight_unit": "USD"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                assessment(**fields)

    def test_empty_population(self):
        a = assessment(population_known=0, population_believed_total=0)
        self.assertIsNone(a.residual_fraction())
        self.assertEqual(a.residual_count(), 0)
        self.assertIsNone(a.coverage()["record_coverage_fraction"])
        self.assertEqual(set(a.outcome_fractions().values()), {None})
        for fields in ({"r_incumbent": .1}, {"disabled_fraction": .1},
                       {"weighting": "value", "weight_known": 1, "weight_unit": "USD"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                assessment(population_known=0, **fields)
        self.assertEqual(assessment(population_known=0, weighting="value", weight_known=0,
                                    weight_unit="USD").residual_amount(), 0)

    def test_frozen_and_assumptions_copied(self):
        notes = ["synthetic"]
        a = assessment(assumptions=notes)
        notes.append("later")
        self.assertEqual(a.assumptions, ("synthetic",))
        with self.assertRaises(FrozenInstanceError):
            a.r_incumbent = .5


class OutcomeAndCoverageTests(unittest.TestCase):
    def test_three_outcomes_partition_population(self):
        a = assessment(r_incumbent=.5, disabled_fraction=.25)
        self.assertEqual(a.outcome_fractions(),
                         {"TRANSITIONED": Fraction(1, 2), "DISABLED": Fraction(1, 4),
                          "UNRESOLVED": Fraction(1, 4)})
        self.assertEqual(sum(a.outcome_fractions().values()), 1)
        self.assertEqual(a.residual_fraction(), Fraction(1, 2))

    def test_disabled_is_not_successfully_transitioned(self):
        a = assessment(disabled_fraction=1)
        self.assertEqual(a.residual_count(), 100)
        self.assertEqual(a.outcome_fractions()["UNRESOLVED"], 0)

    def test_unknown_outcome_split_remains_unknown(self):
        outcomes = assessment(r_incumbent=.5).outcome_fractions()
        self.assertIsNone(outcomes["DISABLED"])
        self.assertIsNone(outcomes["UNRESOLVED"])

    def test_zero_residual_has_zero_other_outcomes(self):
        self.assertEqual(assessment(r_incumbent=1).outcome_fractions(),
                         {"TRANSITIONED": 1, "DISABLED": 0, "UNRESOLVED": 0})

    def test_disabled_over_residual_rejected(self):
        with self.assertRaises(ValueError):
            assessment(r_incumbent=.75, disabled_fraction=.5)

    def test_unknown_coverage_and_declared_coverage(self):
        self.assertIsNone(assessment().coverage()["record_coverage_fraction"])
        a = assessment(population_known=80, population_believed_total=100)
        self.assertEqual(a.coverage()["record_coverage_fraction"], "4/5")
        self.assertIn("not a reachability", a.coverage()["statement"])
        self.assertEqual(assessment(population_known=80, population_believed_total=1000,
                                    r_incumbent=.5).residual_count(), 40)

    def test_continuity_does_not_predict_dependent_breakage(self):
        for continuity in ObjectContinuity:
            with self.subTest(continuity=continuity):
                d = assessment(continuity=continuity).dependent_breakage()
                self.assertIsNone(d["breaks_external_references"])
                self.assertIsNone(d["creates_other_objects"])

    def test_report_is_json_safe_and_exact(self):
        a = assessment(r_incumbent=Fraction(1, 3))
        report = a.report()
        self.assertEqual(json.loads(json.dumps(report, allow_nan=False)), report)
        self.assertEqual(report["not_transitioned_fraction"], "2/3")
        self.assertEqual(report["residual_amount"], "200/3")
        self.assertEqual({o.value for o in Outcome}, {"TRANSITIONED", "DISABLED", "UNRESOLVED"})


class ComparisonTests(unittest.TestCase):
    def test_authority_contrast_fixes_both_success_fractions(self):
        rows = authority_effect()["rows"]
        self.assertEqual(len({row["authority"] for row in rows}), 2)
        self.assertEqual({row["r"] for row in rows}, {Fraction(4, 5)})
        self.assertEqual({row["q"] for row in rows}, {0})
        self.assertEqual({row["residual_fraction"] for row in rows}, {Fraction(1, 5)})

    def test_success_sensitivity_keeps_authority_fixed_and_exports_assumptions(self):
        rows = independent_success_effect()["rows"]
        self.assertEqual(len({row["authority"] for row in rows}), 1)
        self.assertEqual(len({row["r"] for row in rows}), 1)
        self.assertEqual([row["q"] for row in rows], [0, Fraction(1, 2), 1])
        self.assertEqual([row["residual_fraction"] for row in rows],
                         [Fraction(1, 5), Fraction(1, 10), 0])
        self.assertTrue(all(row["assumptions"] for row in rows))
        with self.assertRaises(ValueError):
            independent_success_effect(r=1)

    def test_continuity_comparison_is_conditional_identity(self):
        rows = continuity_effect()["rows"]
        self.assertEqual(len({row["continuity"] for row in rows}), 2)
        self.assertEqual(len({row["r"] for row in rows}), 1)
        self.assertEqual(len({row["q"] for row in rows}), 1)
        self.assertEqual(len({row["residual_fraction"] for row in rows}), 1)
        self.assertTrue(all(row["dependent_breakage"]["breaks_external_references"] is None
                            for row in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
