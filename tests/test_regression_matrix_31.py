import unittest

from diagnostics import classify_failure
from repair_plan import repair_scope
from semantic_replay import ReplaySemanticProvider
from v029_runtime import NormalizedTask, PolicyRouter, TASK_MODES


class RegressionMatrix31Tests(unittest.TestCase):
    pass


def _task_mode_test(mode):
    def test(self):
        task = NormalizedTask('intent', 'objective', mode)
        self.assertEqual(task.task_mode, mode)
    return test


for _mode in TASK_MODES:
    setattr(RegressionMatrix31Tests, f'test_task_mode_{_mode.lower()}', _task_mode_test(_mode))


ROUTES = {
    'EXPLORE': 'DIVERGENT_PLANNER',
    'SELECT': 'DECISION_ROUTER',
    'PLAN': 'PLANNER',
    'EXECUTE': 'EXECUTOR',
    'VALIDATE': 'VALIDATOR',
    'REPAIR': 'REPAIR_ROUTER',
}


def _route_test(mode, expected):
    def test(self):
        task = NormalizedTask('intent', 'objective', mode)
        self.assertEqual(PolicyRouter().route(task).route, expected)
    return test


for _mode, _expected in ROUTES.items():
    setattr(RegressionMatrix31Tests, f'test_route_{_mode.lower()}', _route_test(_mode, _expected))


REPAIR_SCOPES = {
    'SEMANTIC': 'REINTERPRET_REQUEST',
    'POLICY': 'REPAIR_POLICY_ROUTE',
    'EXECUTION': 'REPAIR_EXECUTION_SPEC',
    'VALIDATION': 'REPAIR_OUTPUT',
    'TOOL': 'REPAIR_TOOL_STEP',
    'PROVIDER': 'REPAIR_PROVIDER_STEP',
    'DATA': 'REPAIR_DATA_INPUT',
    'RENDER': 'REPAIR_RENDER_ONLY',
}


def _repair_test(failure, expected):
    def test(self):
        self.assertEqual(repair_scope(failure), expected)
    return test


for _failure, _expected in REPAIR_SCOPES.items():
    setattr(RegressionMatrix31Tests, f'test_repair_{_failure.lower()}', _repair_test(_failure, _expected))


def test_provider_returns_defensive_copy(self):
    provider = ReplaySemanticProvider({'q': {'intent':'x','objective':'y','task_mode':'PLAN'}})
    first = provider.interpret('q')
    first['task_mode'] = 'REPAIR'
    self.assertEqual(provider.interpret('q')['task_mode'], 'PLAN')


def test_semantic_failure_precedes_all_downstream_failures(self):
    result = classify_failure(False, False, False, False, stage_failure='RENDER')
    self.assertEqual(result, 'SEMANTIC')


setattr(RegressionMatrix31Tests, 'test_provider_returns_defensive_copy', test_provider_returns_defensive_copy)
setattr(RegressionMatrix31Tests, 'test_semantic_failure_precedes_all_downstream_failures', test_semantic_failure_precedes_all_downstream_failures)


if __name__ == '__main__':
    unittest.main()
