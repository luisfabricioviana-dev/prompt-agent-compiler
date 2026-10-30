from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "compile-execution-spec",
    "review-execution-spec",
    "repair-failed-run",
    "evaluate-compiler",
    "governed-release",
}


def read_skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("skill_frontmatter_missing")
    data = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    raise AssertionError("skill_frontmatter_unterminated")


class SkillStructureTests(unittest.TestCase):
    def test_required_skills_exist(self):
        for name in SKILLS:
            self.assertTrue((ROOT / "skills" / name / "SKILL.md").is_file(), name)

    def test_each_skill_has_name_and_description_frontmatter(self):
        for name in SKILLS:
            meta = frontmatter(read_skill(name))
            self.assertEqual(meta.get("name"), name)
            self.assertTrue(meta.get("description"))

    def test_skills_do_not_contain_placeholders(self):
        for name in SKILLS:
            text = read_skill(name)
            self.assertIsNone(
                re.search(r"\b(TBD|TODO|implement later|fill in details)\b", text, re.I),
                name,
            )


class CompileExecutionSpecSkillTests(unittest.TestCase):
    def test_compile_skill_uses_runtime_contracts(self):
        text = read_skill("compile-execution-spec")
        self.assertIn("ExecutionSpecV2", text)
        self.assertIn("CapabilityRegistry", text)
        self.assertIn("NormalizedTask", text)
        self.assertIn("UNKNOWN_CAPABILITY", text)
        self.assertIn("do not silently", text.lower())


class ReviewExecutionSpecSkillTests(unittest.TestCase):
    def test_review_skill_requires_gate_and_artifact_evidence(self):
        text = read_skill("review-execution-spec")
        self.assertIn("quality gates", text.lower())
        self.assertIn("ArtifactContract", text)
        self.assertIn("PASS", text)
        self.assertIn("FAIL", text)
        self.assertIn("independent", text.lower())


class RepairFailedRunSkillTests(unittest.TestCase):
    def test_repair_skill_uses_causal_and_minimum_scope_repair(self):
        text = read_skill("repair-failed-run")
        self.assertIn("causal", text.lower())
        self.assertIn("minimum", text.lower())
        self.assertIn("local", text.lower())
        self.assertIn("targeted reverification", text.lower())


class EvaluateCompilerSkillTests(unittest.TestCase):
    def test_evaluate_skill_protects_holdout_and_case_identity(self):
        text = read_skill("evaluate-compiler")
        self.assertIn("case_id", text)
        self.assertIn("blind holdout", text.lower())
        self.assertIn("never", text.lower())
        self.assertIn("promotion gate", text.lower())
        self.assertIn("INTERPRETER", text)
        self.assertIn("POLICY", text)


class GovernedReleaseSkillTests(unittest.TestCase):
    def test_governed_release_is_opt_in_fail_closed(self):
        text = read_skill("governed-release")
        lowered = text.lower()
        self.assertIn("opt-in", lowered)
        self.assertIn("fail-closed", lowered)
        self.assertIn("CapabilityRegistry", text)
        self.assertIn("signed", lowered)
        self.assertIn("reconciliation", lowered)
        self.assertIn("dry-run", lowered)
        self.assertIn("never embed", lowered)


if __name__ == "__main__":
    unittest.main()
