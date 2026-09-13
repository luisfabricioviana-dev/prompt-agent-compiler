import unittest

from compiler_runtime import CompilerRuntime
from semantic_replay import ReplaySemanticProvider

CASES = [
    ('generate_direct', {'intent':'generate','objective':'draft text','task_mode':'GENERATE'}, 'DIRECT_EXECUTION', True, False),
    ('explore_divergent', {'intent':'explore','objective':'generate options','task_mode':'EXPLORE'}, 'DIVERGENT_PLANNER', True, False),
    ('explain_direct', {'intent':'explain','objective':'teach concept','task_mode':'EXPLAIN'}, 'DIRECT_EXECUTION', True, False),
    ('transform_direct', {'intent':'transform','objective':'rewrite content','task_mode':'TRANSFORM'}, 'DIRECT_EXECUTION', True, False),
    ('summarize_direct', {'intent':'summarize','objective':'compress source','task_mode':'SUMMARIZE'}, 'DIRECT_EXECUTION', True, False),
    ('classify_direct', {'intent':'classify','objective':'assign label','task_mode':'CLASSIFY'}, 'DIRECT_EXECUTION', True, False),
    ('extract_direct', {'intent':'extract','objective':'extract fields','task_mode':'EXTRACT'}, 'DIRECT_EXECUTION', True, False),
    ('compare_direct', {'intent':'compare','objective':'compare alternatives','task_mode':'COMPARE'}, 'DIRECT_EXECUTION', True, False),
    ('select_decision', {'intent':'select','objective':'choose candidate','task_mode':'SELECT'}, 'DECISION_ROUTER', True, False),
    ('plan_planner', {'intent':'plan','objective':'build plan','task_mode':'PLAN'}, 'PLANNER', True, False),
    ('assess_direct', {'intent':'assess','objective':'assess quality','task_mode':'ASSESS'}, 'DIRECT_EXECUTION', True, False),
    ('execute_executor', {'intent':'execute','objective':'perform action','task_mode':'EXECUTE'}, 'EXECUTOR', True, False),
    ('validate_validator', {'intent':'validate','objective':'validate result','task_mode':'VALIDATE'}, 'VALIDATOR', True, False),
    ('repair_router', {'intent':'repair','objective':'fix failure','task_mode':'REPAIR'}, 'REPAIR_ROUTER', True, False),
    ('research_grounded', {'intent':'research','objective':'verify claim','task_mode':'ASSESS','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('summarize_grounded', {'intent':'summarize','objective':'source faithful summary','task_mode':'SUMMARIZE','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('compare_grounded', {'intent':'compare','objective':'compare evidence','task_mode':'COMPARE','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('select_grounded', {'intent':'select','objective':'select from verified options','task_mode':'SELECT','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('plan_grounded', {'intent':'plan','objective':'plan from current facts','task_mode':'PLAN','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('execute_grounded', {'intent':'execute','objective':'execute evidence bound task','task_mode':'EXECUTE','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('validate_grounded', {'intent':'validate','objective':'validate against evidence','task_mode':'VALIDATE','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('clarify_generate', {'intent':'generate','objective':'draft unknown artifact','task_mode':'GENERATE','material_ambiguity':True}, 'CLARIFY', False, False),
    ('clarify_explore', {'intent':'explore','objective':'explore undefined space','task_mode':'EXPLORE','material_ambiguity':True}, 'CLARIFY', False, False),
    ('clarify_compare', {'intent':'compare','objective':'compare unspecified items','task_mode':'COMPARE','material_ambiguity':True}, 'CLARIFY', False, False),
    ('clarify_select', {'intent':'select','objective':'select with missing criterion','task_mode':'SELECT','material_ambiguity':True}, 'CLARIFY', False, False),
    ('clarify_plan', {'intent':'plan','objective':'plan with missing constraint','task_mode':'PLAN','material_ambiguity':True}, 'CLARIFY', False, False),
    ('clarify_execute', {'intent':'execute','objective':'execute ambiguous action','task_mode':'EXECUTE','material_ambiguity':True}, 'CLARIFY', False, False),
    ('ambiguity_precedes_grounding', {'intent':'research','objective':'verify underspecified claim','task_mode':'ASSESS','material_ambiguity':True,'evidence_required':True}, 'CLARIFY', False, False),
    ('repair_grounded', {'intent':'repair','objective':'repair evidence bound result','task_mode':'REPAIR','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('classify_grounded', {'intent':'classify','objective':'classify from source','task_mode':'CLASSIFY','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
    ('extract_grounded', {'intent':'extract','objective':'extract from authoritative source','task_mode':'EXTRACT','evidence_required':True}, 'GROUNDED_EXECUTION', True, True),
]

class EndToEnd31Tests(unittest.TestCase):
    pass


def _make_test(name, raw, expected_route, expected_eval, expected_grounding):
    def test(self):
        provider = ReplaySemanticProvider({name: raw})
        spec = CompilerRuntime(provider).compile(name)
        self.assertEqual(spec.route, expected_route)
        self.assertEqual(spec.require_eval, expected_eval)
        self.assertEqual(spec.require_grounding, expected_grounding)
        self.assertEqual(spec.task.task_mode, raw['task_mode'])
    return test


for _name, _raw, _route, _eval, _grounding in CASES:
    setattr(
        EndToEnd31Tests,
        f'test_e2e_{_name}',
        _make_test(_name, _raw, _route, _eval, _grounding),
    )


class EndToEndManifestTests(unittest.TestCase):
    def test_manifest_has_exactly_31_unique_scenarios(self):
        self.assertEqual(len(CASES), 31)
        self.assertEqual(len({case[0] for case in CASES}), 31)


if __name__ == '__main__':
    unittest.main()
