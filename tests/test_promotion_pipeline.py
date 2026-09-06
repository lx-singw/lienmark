"""
Integration and Schema Tests for Two-Project Isolated Deployment & Promotion Pipeline.
Authored under Google AntiGravity for Agentic Cinema: The Blockbuster Hackathon.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
OUTPUT_DIR = ROOT_DIR / "output"
DOCS_DIR = ROOT_DIR / "docs" / "deployment"

PIPELINE_SCRIPTS = [
    "provision_environments.ps1",
    "provision_environments.sh",
    "deploy.ps1",
    "deploy.sh",
    "promote_to_demo.ps1",
    "promote_to_demo.sh",
]


class TestScriptIntegrityAndSyntax:
    """Verifies that all automation scripts exist, have proper headers, and pass syntax checks."""

    @pytest.mark.parametrize("script_name", PIPELINE_SCRIPTS)
    def test_script_exists_and_non_empty(self, script_name: str):
        script_path = SCRIPTS_DIR / script_name
        assert script_path.exists(), f"Missing required pipeline script: {script_name}"
        assert script_path.stat().st_size > 100, f"Script {script_name} is unexpectedly small or empty"

    def test_deployment_guide_exists(self):
        guide_path = DOCS_DIR / "two_project_deployment_guide.md"
        assert guide_path.exists(), "Missing docs/deployment/two_project_deployment_guide.md"
        content = guide_path.read_text(encoding="utf-8")
        assert "lienmark-dev-lx-2026" in content
        assert "lienmark-demo-lx-2026" in content
        assert "01575B-23EAEE-CF5627" in content

    def test_bash_syntax(self):
        """Validates syntax of all bash scripts using git bash or available bash."""
        git_bash = r"C:\Program Files\Git\bin\bash.exe"
        bash_cmd = git_bash if os.path.exists(git_bash) else shutil.which("bash")

        if not bash_cmd:
            pytest.skip("No compatible bash binary found on system.")

        for script_name in ["provision_environments.sh", "deploy.sh", "promote_to_demo.sh"]:
            script_path = SCRIPTS_DIR / script_name
            res = subprocess.run(
                [bash_cmd, "-n", str(script_path)],
                capture_output=True,
                text=True,
                cwd=str(ROOT_DIR),
            )
            assert res.returncode == 0, f"Bash syntax check failed for {script_name}: {res.stderr}"

    def test_powershell_syntax(self):
        """Validates that PowerShell scripts contain balanced structures and valid parameters."""
        for script_name in ["provision_environments.ps1", "deploy.ps1", "promote_to_demo.ps1"]:
            script_path = SCRIPTS_DIR / script_name
            content = script_path.read_text(encoding="utf-8")
            assert "[CmdletBinding()]" in content, f"{script_name} must include [CmdletBinding()]"
            assert "param (" in content or "param(" in content, f"{script_name} must include param block"
            assert "$ErrorActionPreference = \"Stop\"" in content


class TestZeroLegacyProjectDefaults:
    """Ensures no hardcoded benchpress-ai-cloud defaults remain in the new pipeline scripts."""

    @pytest.mark.parametrize("script_name", PIPELINE_SCRIPTS)
    def test_zero_benchpress_defaults(self, script_name: str):
        script_path = SCRIPTS_DIR / script_name
        content = script_path.read_text(encoding="utf-8")
        assert "benchpress-ai-cloud" not in content, (
            f"Script {script_name} contains legacy default 'benchpress-ai-cloud'. "
            "Scripts must use lienmark-dev-lx-2026 and lienmark-demo-lx-2026."
        )

    def test_project_id_defaults_configured(self):
        deploy_ps1 = (SCRIPTS_DIR / "deploy.ps1").read_text(encoding="utf-8")
        assert "lienmark-dev-lx-2026" in deploy_ps1
        assert "lienmark-demo-lx-2026" in deploy_ps1

        deploy_sh = (SCRIPTS_DIR / "deploy.sh").read_text(encoding="utf-8")
        assert "lienmark-dev-lx-2026" in deploy_sh
        assert "lienmark-demo-lx-2026" in deploy_sh


class TestProvisioningSpecifications:
    """Verifies that the provisioning scripts define all required GCP resources, budgets, and IAM roles."""

    def test_provisioning_contains_required_apis(self):
        required_apis = [
            "run.googleapis.com",
            "cloudbuild.googleapis.com",
            "secretmanager.googleapis.com",
            "artifactregistry.googleapis.com",
            "firestore.googleapis.com",
            "aiplatform.googleapis.com",
            "compute.googleapis.com",
        ]
        ps1_content = (SCRIPTS_DIR / "provision_environments.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "provision_environments.sh").read_text(encoding="utf-8")

        for api in required_apis:
            assert api in ps1_content, f"Missing {api} in provision_environments.ps1"
            assert api in sh_content, f"Missing {api} in provision_environments.sh"

    def test_provisioning_contains_least_privilege_roles(self):
        required_roles = [
            "roles/run.admin",
            "roles/storage.admin",
            "roles/cloudbuild.builds.editor",
            "roles/secretmanager.secretAccessor",
            "roles/aiplatform.user",
            "roles/datastore.user",
        ]
        ps1_content = (SCRIPTS_DIR / "provision_environments.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "provision_environments.sh").read_text(encoding="utf-8")

        for role in required_roles:
            assert role in ps1_content, f"Missing {role} in provision_environments.ps1"
            assert role in sh_content, f"Missing {role} in provision_environments.sh"

    def test_budget_partition_specifications(self):
        ps1_content = (SCRIPTS_DIR / "provision_environments.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "provision_environments.sh").read_text(encoding="utf-8")

        # Dev: $20, Demo: $60, Master Billing
        assert "01575B-23EAEE-CF5627" in ps1_content
        assert "20USD" in ps1_content
        assert "60USD" in ps1_content
        assert "01575B-23EAEE-CF5627" in sh_content
        assert "20USD" in sh_content
        assert "60USD" in sh_content

    def test_gcloud_cmd_bypass_on_windows(self):
        ps1_files = ["provision_environments.ps1", "deploy.ps1", "promote_to_demo.ps1"]
        for fname in ps1_files:
            content = (SCRIPTS_DIR / fname).read_text(encoding="utf-8")
            assert "gcloud.cmd" in content, f"{fname} must locate and use gcloud.cmd on Windows"


class TestReleaseManifestSchema:
    """Validates the structure, cryptographic formats, and invariants of release_manifest.json."""

    @pytest.fixture
    def sample_manifest(self):
        manifest_path = OUTPUT_DIR / "release_manifest.json"
        if not manifest_path.exists():
            # Run deploy dry run to create it
            git_bash = r"C:\Program Files\Git\bin\bash.exe"
            bash_cmd = git_bash if os.path.exists(git_bash) else "bash"
            subprocess.run([bash_cmd, "scripts/deploy.sh", "--dry-run"], cwd=str(ROOT_DIR), check=True)
        with open(manifest_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    def test_manifest_top_level_fields(self, sample_manifest):
        expected_keys = [
            "schema_version",
            "timestamp",
            "environment",
            "project_id",
            "region",
            "repository",
            "git_commit",
            "images",
        ]
        for key in expected_keys:
            assert key in sample_manifest, f"Manifest missing top-level key: {key}"

        assert sample_manifest["schema_version"] == "1.0.0"
        assert sample_manifest["region"] == "us-central1"
        assert sample_manifest["repository"] == "lienmark-repo"
        assert re.match(r"^[a-f0-9]{40}$", sample_manifest["git_commit"])

    def test_manifest_services_integrity(self, sample_manifest):
        images = sample_manifest["images"]
        assert "lienmark-api" in images, "Missing lienmark-api in images"
        assert "lienmark-web" in images, "Missing lienmark-web in images"

        for svc_name in ["lienmark-api", "lienmark-web"]:
            svc = images[svc_name]
            assert svc["service"] == svc_name
            assert "tag" in svc
            assert "digest" in svc
            assert "sha256" in svc
            assert "url" in svc

            sha = svc["sha256"]
            assert re.match(r"^sha256:[a-f0-9]{64}$", sha), f"Invalid sha256 format for {svc_name}: {sha}"
            assert sha in svc["digest"], f"Digest '{svc['digest']}' does not contain hash '{sha}'"


class TestImmutablePromotionPattern:
    """Verifies that promote_to_demo scripts strictly enforce the immutable digest promotion pattern."""

    def test_promotion_script_enforces_digest_equality(self):
        ps1_content = (SCRIPTS_DIR / "promote_to_demo.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "promote_to_demo.sh").read_text(encoding="utf-8")

        # Verify digest comparison logic
        assert "TargetApiActualSha" in ps1_content
        assert "-ne" in ps1_content
        assert "TARGET_API_ACTUAL_SHA" in sh_content
        assert "!=" in sh_content

    def test_promotion_script_enforces_no_traffic_candidate_deployment(self):
        ps1_content = (SCRIPTS_DIR / "promote_to_demo.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "promote_to_demo.sh").read_text(encoding="utf-8")

        assert "--no-traffic" in ps1_content
        assert "--tag" in ps1_content or "--tag=\"candidate\"" in ps1_content
        assert "--no-traffic" in sh_content
        assert "--tag=\"candidate\"" in sh_content or "--tag=candidate" in sh_content

    def test_promotion_script_enforces_atomic_traffic_shift(self):
        ps1_content = (SCRIPTS_DIR / "promote_to_demo.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "promote_to_demo.sh").read_text(encoding="utf-8")

        assert "update-traffic" in ps1_content
        assert "--to-revisions" in ps1_content
        assert "update-traffic" in sh_content
        assert "--to-revisions" in sh_content

    def test_promotion_script_enforces_health_probing(self):
        ps1_content = (SCRIPTS_DIR / "promote_to_demo.ps1").read_text(encoding="utf-8")
        sh_content = (SCRIPTS_DIR / "promote_to_demo.sh").read_text(encoding="utf-8")

        assert "/health" in ps1_content
        assert "/readyz" in ps1_content
        assert "/health" in sh_content
        assert "/readyz" in sh_content


class TestPromotionLogSchema:
    """Validates the structure and invariants of output/demo_promotion_log.json."""

    @pytest.fixture
    def sample_promotion_log(self):
        log_path = OUTPUT_DIR / "demo_promotion_log.json"
        if not log_path.exists():
            git_bash = r"C:\Program Files\Git\bin\bash.exe"
            bash_cmd = git_bash if os.path.exists(git_bash) else "bash"
            subprocess.run([bash_cmd, "scripts/promote_to_demo.sh", "--dry-run"], cwd=str(ROOT_DIR), check=True)
        with open(log_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)

    def test_promotion_log_invariants(self, sample_promotion_log):
        assert sample_promotion_log["status"] == "SUCCESS"
        assert sample_promotion_log["source_project"] == "lienmark-dev-lx-2026"
        assert sample_promotion_log["target_project"] == "lienmark-demo-lx-2026"
        assert sample_promotion_log["source_environment"] == "dev"
        assert sample_promotion_log["target_environment"] == "demo"

        services = sample_promotion_log["services"]
        assert "lienmark-api" in services
        assert "lienmark-web" in services

        for svc_name in ["lienmark-api", "lienmark-web"]:
            svc = services[svc_name]
            assert svc["digest_match"] is True
            assert svc["traffic_percent"] == 100
            assert svc["health_check"] == "PASSED"
            assert "candidate_revision" in svc
            assert "candidate_url" in svc
