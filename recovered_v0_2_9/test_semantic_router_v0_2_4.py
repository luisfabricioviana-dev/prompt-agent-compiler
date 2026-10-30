import unittest

# These tests intentionally target failures exposed by the retired v0.2.3 holdout.
# They are development tests, not holdout tests.
from semantic_interpreter import interpret_request
from policy_router import compile_request
from models import PatternStatus


class SemanticInterpreterTests(unittest.TestCase):
    def test_ui_error_state_is_not_debug_intent(self):
        m = interpret_request("Crie um dashboard responsivo com estados de loading, empty, erro e navegação por teclado.")
        self.assertTrue(m.ui_required)
        self.assertFalse(m.diagnose_failure)
        self.assertTrue(m.accessibility_required)

    def test_memory_reduction_is_performance(self):
        m = interpret_request("Reduza o consumo de memória deste job sem alterar o resultado final.")
        self.assertTrue(m.improve_performance)
        self.assertIn("memory", m.performance_dimensions)
        self.assertTrue(m.preserve_behavior)

    def test_document_only_semantics_are_normalized(self):
        m = interpret_request("Avalie somente os documentos anexados e identifique fatos, interpretações e pendências.")
        self.assertTrue(m.analyze_evidence)
        self.assertTrue(m.evidence_only)
        self.assertTrue(m.traceability_required)

    def test_destructive_paraphrase_is_detected(self):
        m = interpret_request("Apague todos os arquivos temporários do projeto e não mantenha backup.")
        self.assertTrue(m.destructive_action)
        self.assertTrue(m.external_or_persistent_state)
        self.assertEqual(m.reversibility_risk, 4)

    def test_existing_document_rewrite_is_modification(self):
        m = interpret_request("Reescreva esta documentação para ficar mais clara, sem mudar o significado técnico.")
        self.assertTrue(m.modify_existing)
        self.assertTrue(m.preserve_behavior)


class PolicyRouterTests(unittest.TestCase):
    def test_refactor_public_api_gets_regression_gate(self):
        spec = compile_request("Refatore esta classe para reduzir duplicação sem mudar a API pública.")
        self.assertEqual(spec.patterns["P02"].status, PatternStatus.MANDATORY)
        self.assertIn("REGRESSION_GATE", {g.gate_id for g in spec.quality_gates})

    def test_memory_optimization_gets_baseline_and_regression(self):
        spec = compile_request("Reduza o consumo de memória deste job sem alterar o resultado final.")
        self.assertEqual(spec.patterns["P05"].status, PatternStatus.MANDATORY)
        gates = {g.gate_id for g in spec.quality_gates}
        self.assertIn("BASELINE_GATE", gates)
        self.assertIn("REGRESSION_GATE", gates)

    def test_document_only_analysis_gets_evidence_and_traceability(self):
        spec = compile_request("Avalie somente os documentos anexados e identifique o que está comprovado e o que permanece pendente.")
        gates = {g.gate_id for g in spec.quality_gates}
        self.assertIn("EVIDENCE_GATE", gates)
        self.assertIn("TRACEABILITY_GATE", gates)
        self.assertGreaterEqual(int(spec.complexity_level[1]), 2)

    def test_destructive_delete_is_controlled(self):
        spec = compile_request("Apague todos os arquivos temporários do projeto e não mantenha backup.")
        self.assertIn("DESTRUCTIVE_ACTION_GATE", {g.gate_id for g in spec.quality_gates})
        self.assertIn(spec.complexity_level, {"N3", "N4"})

    def test_ui_error_state_does_not_select_debug(self):
        spec = compile_request("Crie um dashboard responsivo com estados de loading, empty, erro e navegação por teclado.")
        self.assertEqual(spec.patterns["P03"].status, PatternStatus.REJECTED)
        self.assertEqual(spec.patterns["P08"].status, PatternStatus.MANDATORY)

    def test_bad_code_phrase_selects_debug(self):
        spec = compile_request("Tem alguma coisa errada nesse código. Veja o que é.")
        self.assertEqual(spec.patterns["P03"].status, PatternStatus.MANDATORY)

    def test_architecture_migration_preserves_behavior(self):
        spec = compile_request("Troque toda a arquitetura interna, mas preserve exatamente a API e o comportamento observável.")
        self.assertEqual(spec.patterns["P02"].status, PatternStatus.MANDATORY)
        self.assertEqual(spec.patterns["P04"].status, PatternStatus.MANDATORY)
        self.assertIn("REGRESSION_GATE", {g.gate_id for g in spec.quality_gates})

    def test_external_calendar_update_has_nontrivial_complexity(self):
        spec = compile_request("Atualize o evento existente no calendário para amanhã às 15h sem criar um novo evento.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})
        self.assertIn("calendar_write_access", spec.capabilities)

    def test_approval_gate_increases_complexity(self):
        spec = compile_request("Prepare a mudança e só execute depois de uma aprovação humana explícita.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})
        self.assertIn("HUMAN_APPROVAL_GATE", {g.gate_id for g in spec.quality_gates})


if __name__ == "__main__":
    unittest.main()

class DevelopmentRegressionTests(unittest.TestCase):
    def test_architecture_word_does_not_trigger_ui(self):
        m = interpret_request("Projete a arquitetura de uma plataforma de processamento de vídeos.")
        self.assertFalse(m.ui_required)
        spec = compile_request("Projete a arquitetura de uma plataforma de processamento de vídeos.")
        self.assertEqual(spec.patterns["P08"].status, PatternStatus.REJECTED)

    def test_reconstruct_is_not_build(self):
        m = interpret_request("Reconstrua a cronologia do processo de licenciamento e indique pendências.")
        self.assertFalse(m.create_new)

    def test_write_function_is_build(self):
        spec = compile_request("Use cinco agentes para escrever uma função que some dois inteiros.")
        self.assertEqual(spec.patterns["P01"].status, PatternStatus.MANDATORY)
        self.assertEqual(spec.patterns["P07"].status, PatternStatus.REJECTED)

    def test_simple_build_has_n1_floor(self):
        spec = compile_request("Implemente um parser simples de CSV que retorne uma lista de dicionários.")
        self.assertIn(spec.complexity_level, {"N1", "N2"})

    def test_debug_has_n1_floor(self):
        spec = compile_request("Tem alguma coisa errada nesse código. Veja o que é.")
        self.assertIn(spec.complexity_level, {"N1", "N2"})

    def test_system_design_has_n2_floor(self):
        spec = compile_request("Desenhe a arquitetura de um serviço de notificações com filas, retries e idempotência antes de qualquer implementação.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_high_consequence_evidence_has_n3_floor(self):
        spec = compile_request("Reconstrua a cronologia do processo de licenciamento, diferencie fato documental de avaliação técnica e indique pendências com rastreabilidade.")
        self.assertIn(spec.complexity_level, {"N3", "N4"})
        self.assertEqual(spec.patterns["P01"].status, PatternStatus.REJECTED)

    def test_preserve_accuracy_compiles_regression_gate(self):
        spec = compile_request("Este modelo está lento. Reduza a latência sem piorar a acurácia.")
        gates = {g.gate_id for g in spec.quality_gates}
        self.assertIn("BASELINE_GATE", gates)
        self.assertIn("REGRESSION_GATE", gates)

    def test_measure_performance_regression_compiles_baseline(self):
        spec = compile_request("Corrija o bug, preserve o comportamento restante, depois meça se a correção piorou a performance.")
        self.assertIn("BASELINE_GATE", {g.gate_id for g in spec.quality_gates})

    def test_administrative_evidence_defaults_to_traceability(self):
        spec = compile_request("Analise o processo administrativo e indique as consequências jurídicas e técnicas de cada pendência.")
        gates = {g.gate_id for g in spec.quality_gates}
        self.assertIn("EVIDENCE_GATE", gates)
        self.assertIn("TRACEABILITY_GATE", gates)
        self.assertIn(spec.complexity_level, {"N3", "N4"})

class ComplexityAndRoleRegressionTests(unittest.TestCase):
    def test_architecture_change_with_preservation_is_at_least_n2(self):
        spec = compile_request("Reescreva completamente a arquitetura, mas não altere absolutamente nada no sistema.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_research_then_build_is_at_least_n2(self):
        spec = compile_request("Pesquise as bibliotecas atuais para autenticação OAuth e depois implemente a opção mais adequada neste projeto.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})
        self.assertIn("web_or_current_evidence_access", spec.capabilities)

    def test_current_trend_research_is_at_least_n2(self):
        spec = compile_request("Pesquise uma tendência atual para Shorts, confirme as afirmações principais e proponha três ângulos de vídeo.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_composite_video_deliverable_is_multistep(self):
        spec = compile_request("Crie um Short completo sobre o tema, incluindo roteiro, plano de cenas e especificações de geração.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_security_review_is_at_least_n2(self):
        spec = compile_request("Revise este fluxo de autenticação para encontrar falhas de segurança sem implementar mudanças ainda.")
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_security_architecture_build_is_n3_or_n4(self):
        spec = compile_request("Projete e implemente autenticação com MFA, rotação de sessão e recuperação de conta, com revisão de segurança.")
        self.assertIn(spec.complexity_level, {"N3", "N4"})

    def test_csv_business_analysis_is_at_least_n2(self):
        m = interpret_request("Analise este CSV, encontre os principais drivers de churn e produza uma recomendação baseada em evidências.")
        self.assertTrue(m.analyze_data)
        spec = compile_request(m.raw_request)
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_compare_architectures_is_not_architecture_change(self):
        m = interpret_request("Compare quatro arquiteturas independentes para o mesmo problema e depois faça uma síntese crítica única.")
        self.assertFalse(m.architecture_change)
        spec = compile_request(m.raw_request)
        self.assertEqual(spec.patterns["P04"].status, PatternStatus.REJECTED)
        self.assertIn(spec.complexity_level, {"N2", "N3"})

    def test_normative_document_analysis_is_high_consequence(self):
        spec = compile_request("Analise a demanda atual do processo e confronte cada conclusão com os documentos e normas fornecidos, sem usar fontes externas.")
        self.assertIn(spec.complexity_level, {"N3", "N4"})
