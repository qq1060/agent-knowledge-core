from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src" / "agent_knowledge_core" / "cli.py"


def run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(tmp_path), *args],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


class CliTest(unittest.TestCase):
    def test_new_validate_and_generate(self) -> None:
        with self.subTest("template lifecycle"):
            import tempfile

            with tempfile.TemporaryDirectory() as td:
                repo = Path(td) / "knowledge"
                subprocess.run([sys.executable, str(CLI), "new", str(repo)], cwd=str(ROOT), check=True)
                run_cli(repo, "init", "--profile", "example-mac")
                run_cli(repo, "validate")
                out = run_cli(repo, "generate").stdout

                self.assertIn("codex:", out)
                self.assertTrue((repo / "local" / "generated" / "example-mac.codex.AGENTS.md").exists())
                self.assertTrue((repo / "local" / "generated" / "example-mac.claude-code.CLAUDE.md").exists())

    def test_validate_rejects_missing_owned_skill(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "knowledge"
            subprocess.run([sys.executable, str(CLI), "new", str(repo)], cwd=str(ROOT), check=True)
            data = json.loads((repo / "manifests" / "skills.json").read_text())
            data["skills"][0]["path"] = "skills/owned/missing"
            (repo / "manifests" / "skills.json").write_text(json.dumps(data), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(CLI), "--repo-root", str(repo), "validate"],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("owned path missing SKILL.md", proc.stderr)

    def test_team_template_validate_and_generate(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "team-knowledge"
            subprocess.run([sys.executable, str(CLI), "new", "--template", "team", str(repo)], cwd=str(ROOT), check=True)

            run_cli(repo, "init", "--profile", "team-mac")
            run_cli(repo, "validate")
            out = run_cli(repo, "generate").stdout
            run_cli(repo, "privacy-scan")
            route = repo / "local" / "generated" / "team-mac.codex.AGENTS.md"
            route_text = route.read_text(encoding="utf-8")

            self.assertIn("codex:", out)
            self.assertTrue(route.exists())
            self.assertIn("team-runbook", route_text)
            self.assertIn("memory/team", route_text)
            self.assertIn("memory/projects", route_text)

    def test_privacy_scan_flags_private_ip(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "knowledge"
            subprocess.run([sys.executable, str(CLI), "new", str(repo)], cwd=str(ROOT), check=True)
            target = repo / "memory" / "common" / "leak.md"
            private_address = "10." + "1.2.3"
            target.write_text("private address: %s\n" % private_address, encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(CLI), "--repo-root", str(repo), "privacy-scan"],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("private ipv4-like address", proc.stdout)

    def test_privacy_scan_does_not_flag_three_part_version(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "knowledge"
            subprocess.run([sys.executable, str(CLI), "new", str(repo)], cwd=str(ROOT), check=True)
            target = repo / "memory" / "common" / "version.md"
            target.write_text("release version: 10.1.2\n", encoding="utf-8")

            run_cli(repo, "privacy-scan")

    def test_privacy_scan_flags_custom_term(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "knowledge"
            subprocess.run([sys.executable, str(CLI), "new", str(repo)], cwd=str(ROOT), check=True)
            target = repo / "memory" / "common" / "leak.md"
            term = "example-internal-name"
            target.write_text("private marker: %s\n" % term, encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(CLI), "--repo-root", str(repo), "privacy-scan", "--term", term],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("custom term", proc.stdout)


if __name__ == "__main__":
    unittest.main()
