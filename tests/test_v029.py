import unittest

from v029_runtime import classify_ambiguity, classify_solvability, merge_task_state, NormalizedTask, PolicyRouter
from v029_policies import detect_constraint_conflict, duplicate_evidence, ideation_pipeline, production_prompt_ready, rationale_mode
from semantic_replay import ReplaySemanticProvider
from semantic_interpreter import SemanticInterpreter
from compiler_runtime import CompilerRuntime
from diagnostics import classify_failure
from repair_plan import repair_scope

class V029Tests(unittest.TestCase):
    def test_task_delta_preserves_state(self):
        updated = merge_task_state({'city':'Tokyo','days':7}, {'budget':1000})
        self.assertEqual(updated['city'], 'Tokyo')
        self.assertEqual(updated['budget'], 1000)

    def test_explicit_none_removes_state(self):
        self.assertNotIn('tone', merge_task_state({'tone':'formal'}, {'tone':None}))

    def test_ambiguity_and_solvability(self):
        self.assertEqual(classify_ambiguity(True), 'CLARIFY')
        self.assertEqual(classify_ambiguity(True, resolvable_by_tool=True), 'RESOLVE_WITH_TOOL')
        self.assertEqual(classify_solvability(unsafe=True), 'UNSAFE_TO_PERSONALIZE')

    def test_constraint_conflict(self):
        self.assertTrue(detect_constraint_conflict(['be exhaustive','maximum 30 words']))

    def test_ideation_and_evidence_dedup(self):
        self.assertEqual(ideation_pipeline(['Consulting',' consulting ','Course']), ['Consulting','Course'])
        self.assertTrue(duplicate_evidence('abc',['abc']))

    def test_production_prompt_gate_and_rationale(self):
        self.assertFalse(production_prompt_ready(True,False,True))
        self.assertTrue(production_prompt_ready(True,True,True))
        self.assertEqual(rationale_mode(checkable_steps=True), 'CHECKABLE_STEPS')

    def test_normalized_task_and_policy_router(self):
        with self.assertRaises(ValueError):
            NormalizedTask('x','y','UNKNOWN')
        task = NormalizedTask('plan','make plan','PLAN')
        self.assertEqual(PolicyRouter().route(task).route, 'PLANNER')

    def test_replay_semantics(self):
        provider = ReplaySemanticProvider({'q':{'intent':'plan','objective':'make plan','task_mode':'PLAN'}})
        task = SemanticInterpreter(provider).interpret('q')
        self.assertEqual(task.task_mode, 'PLAN')

    def test_end_to_end_compile(self):
        provider = ReplaySemanticProvider({'q':{'intent':'research','objective':'verify','task_mode':'ASSESS','evidence_required':True}})
        spec = CompilerRuntime(provider).compile('q')
        self.assertEqual(spec.route, 'GROUNDED_EXECUTION')
        self.assertTrue(spec.require_grounding)

    def test_causal_taxonomy_semantics_precedes_policy(self):
        self.assertEqual(classify_failure(False,False,False,False), 'SEMANTIC')

    def test_reconstructed_mutation_taxonomy(self):
        cases = [
            ((False,True,True,True,None),'SEMANTIC'),
            ((True,False,True,True,None),'POLICY'),
            ((True,True,False,True,None),'EXECUTION'),
            ((True,True,True,False,None),'VALIDATION'),
            ((True,True,True,True,'TOOL'),'TOOL'),
            ((True,True,True,True,'PROVIDER'),'PROVIDER'),
            ((True,True,True,True,'DATA'),'DATA'),
            ((True,True,True,True,'RENDER'),'RENDER'),
            ((True,True,True,True,None),None),
        ]
        for args, expected in cases:
            self.assertEqual(classify_failure(*args[:4], stage_failure=args[4]), expected)

    def test_minimum_scope_repair(self):
        self.assertEqual(repair_scope('POLICY'),'REPAIR_POLICY_ROUTE')
        self.assertEqual(repair_scope('RENDER'),'REPAIR_RENDER_ONLY')

if __name__ == '__main__':
    unittest.main()
