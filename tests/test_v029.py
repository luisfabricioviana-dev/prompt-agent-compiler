import unittest

from v029_runtime import classify_ambiguity, classify_solvability, merge_task_state, NormalizedTask, PolicyRouter
from v029_policies import (
    detect_constraint_conflict,
    duplicate_evidence,
    ideation_pipeline,
    production_prompt_ready,
    rationale_mode,
)
from semantic_replay import ReplaySemanticProvider
from semantic_interpreter import SemanticInterpreter
from diagnostics import classify_failure
from repair_plan import repair_scope


class V029Tests(unittest.TestCase):
    def test_task_delta_preserves_state(self):
        current = {'city': 'Tokyo', 'days': 7, 'interest': 'culture+food'}
        updated = merge_task_state(current, {'budget': 1000, 'party_size': 2})
        self.assertEqual(updated['city'], 'Tokyo')
        self.assertEqual(updated['days'], 7)
        self.assertEqual(updated['party_size'], 2)

    def test_explicit_none_removes_state(self):
        self.assertNotIn('tone', merge_task_state({'tone': 'formal'}, {'tone': None}))

    def test_material_ambiguity_requires_clarification_when_unresolvable(self):
        self.assertEqual(classify_ambiguity(True), 'CLARIFY')

    def test_tool_resolvable_ambiguity_does_not_require_user(self):
        self.assertEqual(classify_ambiguity(True, resolvable_by_tool=True), 'RESOLVE_WITH_TOOL')

    def test_high_risk_personalization_gate(self):
        self.assertEqual(classify_solvability(unsafe=True), 'UNSAFE_TO_PERSONALIZE')

    def test_constraint_conflict(self):
        self.assertTrue(detect_constraint_conflict(['be exhaustive', 'maximum 30 words']))

    def test_ideation_deduplicates_semantically_identical_strings(self):
        self.assertEqual(ideation_pipeline(['Consulting', ' consulting ', 'Course']), ['Consulting', 'Course'])

    def test_production_prompt_requires_eval_fixtures_and_version(self):
        self.assertFalse(production_prompt_ready(True, False, True))
        self.assertTrue(production_prompt_ready(True, True, True))

    def test_duplicate_source_does_not_count_as_new_evidence(self):
        self.assertTrue(duplicate_evidence('abc', ['abc']))

    def test_verifiable_rationale_policy(self):
        self.assertEqual(rationale_mode(checkable_steps=True), 'CHECKABLE_STEPS')

    def test_normalized_task_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            NormalizedTask('x', 'y', 'UNKNOWN')

    def test_policy_router_uses_semantics(self):
        task = NormalizedTask('plan', 'make plan', 'PLAN')
        self.assertEqual(PolicyRouter().route(task).route, 'PLANNER')

    def test_replay_semantics(self):
        provider = ReplaySemanticProvider({'q': {'intent':'plan','objective':'make plan','task_mode':'PLAN'}})
        task = SemanticInterpreter(provider).interpret('q')
        self.assertEqual(task.task_mode, 'PLAN')

    def test_causal_taxonomy_prevents_policy_blame_when_semantics_wrong(self):
        self.assertEqual(classify_failure(False, False, False, False), 'SEMANTIC')

    def test_minimum_scope_repair(self):
        self.assertEqual(repair_scope('POLICY'), 'REPAIR_POLICY_ROUTE')


if __name__ == '__main__':
    unittest.main()
