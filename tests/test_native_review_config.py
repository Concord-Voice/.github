"""Offline contract tests for the direct PR review command. Run with Python 3 and jq."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1] / ".claude/skills/review-pr/SKILL.md"
TEXT = SKILL.read_text()
ARGUMENT = re.search(r"```regex\n(.+)\n```", TEXT)[1]
LOOKUP, POLICY, CONFIG, FILES = re.findall(r"```bash\n(.*?)\n```", TEXT, re.S)
REPO = "Concord-Voice/.github"
OID = "a" * 40
DEFAULT = {"base": ["security-reviewer", "code-reviewer", "docs-reviewer"], "patterns": []}

# A new shell for each block, as on the native host. Only the three expected gh
# operations exist; the command's own jq programs process the fixture responses.
MOCK_GH = """#!/bin/sh
set -eu
case "$1 $2" in
  "pr view")
    test "$3 $4 $5 $6 $7 $8" = "15 --repo github.com/$TARGET --json number,url,baseRefName --jq"
    jq -er "$9" "$FIXTURE/pr.json" ;;
  "api --hostname")
    if test "$4" = "repos/$TARGET/branches/main"; then
      test "$3 $5" = "github.com --jq"
      jq -er "$6" "$FIXTURE/main.json"
      exit
    fi
    test "$3 $4 $5 $6 $7 $8" = "github.com graphql -f base=$OID -f path=$OID:.claude/repo-config.json"
    test "$9" = "-f" && test "${11}" = "--jq"
    case "${10}" in *"repository(owner: \\"Concord-Voice\\", name: \\"${TARGET#*/}\\")"*) ;; *) exit 2 ;; esac
    jq -ce "${12}" "$FIXTURE/base.json" ;;
  "pr diff")
    test "$3 $4 $5 $6" = "15 --repo github.com/$TARGET --name-only"
    printf '%s\\n' docs/change.md ;;
  *) exit 2 ;;
esac
"""


class ReviewConfig(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.cwd = self.root
        self.env = {**os.environ, "PATH": str(self.root) + os.pathsep + os.environ["PATH"],
                    "FIXTURE": str(self.root), "TARGET": REPO, "OID": OID, "GH_REPO": "example/fork"}
        self.env.pop("PR_NUMBER", None)
        (self.root / "gh").write_text(MOCK_GH)
        (self.root / "gh").chmod(0o755)
        self.pr = {"number": 15, "url": f"https://github.com/{REPO}/pull/15", "baseRefName": "main"}
        self.branch = {"name": "main", "protected": True, "commit": {"sha": OID}}
        self.repository = {"defaultBranchRef": {"name": "main"}, "base": {"__typename": "Commit"}, "config": None}

    def invoke(self, argument):
        match = re.fullmatch(ARGUMENT, argument)
        if not match:
            raise ValueError("invalid PR argument")
        number = next(group for group in match.groups() if group is not None)
        assert re.fullmatch(r"[1-9][0-9]*", number)
        (self.root / "pr.json").write_text(json.dumps(self.pr))
        (self.root / "main.json").write_text(json.dumps(self.branch))
        (self.root / "base.json").write_text(json.dumps({"data": {"repository": self.repository}}))
        def run(command):
            return subprocess.run(["bash", "-c", command], cwd=self.cwd, env=self.env,
                                  text=True, capture_output=True, check=True).stdout.strip()
        self.target = run(LOOKUP.replace("NUMBER", number))
        oid = run(POLICY)
        self.assertRegex(oid, r"^[0-9a-f]{40}$")
        config = json.loads(run(CONFIG.replace("POLICY_OID", oid)))
        self.assertEqual(run(FILES.replace("NUMBER", number)), "docs/change.md")
        return config

    def blob(self, text):
        self.repository["config"] = {"__typename": "Blob", "text": text,
                                     "isTruncated": False, "isBinary": False}

    def test_number_and_url_with_and_without_checkout(self):
        checkout = self.root / "fork"
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin",
                        "https://github.com/example/fork.git"], check=True)
        (checkout / ".claude").mkdir()
        (checkout / ".claude/repo-config.json").write_text('{"review_agents":{"base":["local-decoy"]}}')
        for self.cwd in (self.root, checkout):
            for argument in ("15", self.pr["url"], self.pr["url"] + "/"):
                with self.subTest(cwd=self.cwd, argument=argument):
                    self.assertEqual(self.invoke(argument), DEFAULT)

    def test_feature_target_uses_protected_default_policy(self):
        self.pr["baseRefName"] = "feature/preview"
        self.pr["baseRefOid"] = "b" * 40
        policy = {"base": ["scope-reviewer"], "patterns": []}
        self.blob(json.dumps({"review_agents": policy}))
        self.assertEqual(self.invoke("15"), policy)
        self.assertEqual(self.target, "other")
        self.pr["baseRefName"] = "main"
        self.assertEqual(self.invoke("15"), policy)
        self.assertEqual(self.target, "main")

    def test_policy_requires_protection_and_default_branch_identity(self):
        for name, protected, default in (("feature", True, "main"), ("main", False, "main"),
                                        ("main", True, "different")):
            with self.subTest(name=name, protected=protected, default=default):
                self.branch.update(name=name, protected=protected)
                self.repository["defaultBranchRef"]["name"] = default
                with self.assertRaises(subprocess.CalledProcessError):
                    self.invoke("15")

    def test_only_supported_coverage_roles_can_be_selected(self):
        eligible = ["code-reviewer", "docs-reviewer", "frontend-reviewer", "migration-reviewer",
                    "scope-reviewer", "security-reviewer"]
        self.blob(json.dumps({"review_agents": {"base": eligible}}))
        self.assertEqual(self.invoke("15")["base"], eligible)
        for role in ("developer", "docs-writer", "test-writer", "unknown-reviewer", []):
            for policy in ({"base": [role]}, {"patterns": [{"glob": "docs/**", "agent": role}]}):
                with self.subTest(policy=policy), self.assertRaises(subprocess.CalledProcessError):
                    self.blob(json.dumps({"review_agents": policy}))
                    self.invoke("15")

    def test_configured_and_intentionally_empty_lists(self):
        for policy in ({"base": [], "patterns": []},
                       {"base": ["docs-reviewer"], "patterns": [{"glob": "docs/**", "agent": "docs-reviewer"}]}):
            self.blob(json.dumps({"review_agents": policy}))
            self.assertEqual(self.invoke("15"), policy)

    def test_malformed_present_config_stops(self):
        for value in ("not JSON", "null", "[]", '{"review_agents":null}',
                      '{"review_agents":{"base":null}}', '{"review_agents":{"base":[12]}}',
                      '{"review_agents":{"base":[""]}}', '{"review_agents":{"patterns":false}}',
                      '{"review_agents":{"patterns":[{"glob":"docs/**"}]}}',
                      '{"review_agents":{"patterns":[{"agent":"docs-reviewer","glob":7}]}}'):
            with self.subTest(value=value), self.assertRaises(subprocess.CalledProcessError):
                self.blob(value)
                self.invoke("15")

    def test_unknown_base_unreadable_blob_and_wrong_target_stop(self):
        self.repository["base"] = None
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke("15")
        self.repository["base"] = {"__typename": "Commit"}
        self.blob("{}")
        self.repository["config"]["isTruncated"] = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke("15")
        self.repository["config"] = None
        self.pr = {"number": 16, "url": f"https://github.com/{REPO}/pull/16", "baseRefName": "main"}
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke("15")
        self.pr = {"number": 15, "url": "https://github.com/example/fork/pull/15", "baseRefName": "main"}
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke("15")
        for value in (self.pr["url"], "15 16", "zero", "0", "15/"):
            with self.assertRaises(ValueError):
                self.invoke(value)


if __name__ == "__main__":
    unittest.main()
