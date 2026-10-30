
import unittest
from router import compile_request
from models import PatternStatus


class RouterHarnessTests(unittest.TestCase):
    def test_trivial_does_not_use_multi_agent(self):
        spec = compile_request("Explique em uma frase o que é cache.")
        self.assertEqual(spec.patterns["P07"].status, PatternStatus.REJECTED)

    def test_debug_mandatory(self):
        spec = compile_request("Esta função deveria retornar 10, mas está retornando 8. Descubra o erro.")
        self.assertEqual(spec.patterns["P03"].status, PatternStatus.MANDATORY)

    def test_refactor_regression_gate(self):
        spec = compile_request("Reorganize este módulo sem alterar seu comportamento público.")
        self.assertEqual(spec.patterns["P02"].status, PatternStatus.MANDATORY)
        self.assertIn("REGRESSION_GATE", {g.gate_id for g in spec.quality_gates})

    def test_perf_requires_baseline_gate(self):
        spec = compile_request("Esta consulta está lenta. Reduza a latência.")
        self.assertEqual(spec.patterns["P05"].status, PatternStatus.MANDATORY)
        self.assertIn("BASELINE_GATE", {g.gate_id for g in spec.quality_gates})

    def test_anti_overengineering(self):
        spec = compile_request("Crie uma função para converter Celsius em Fahrenheit usando vários agentes.")
        self.assertEqual(spec.patterns["P07"].status, PatternStatus.REJECTED)


if __name__ == "__main__":
    unittest.main()
