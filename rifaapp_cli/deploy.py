from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path, env: dict) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def _resolve_paths(infra_dir: str | None) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parent.parent
    if infra_dir:
        infra_path = Path(infra_dir).expanduser().resolve()
    else:
        infra_path = (repo_root / ".." / "RifaApp-infra").resolve()
    return repo_root, infra_path


def _ensure_db_password(env: dict) -> None:
    if env.get("TF_VAR_db_password"):
        return
    if env.get("DB_PASSWORD"):
        env["TF_VAR_db_password"] = env["DB_PASSWORD"]
        return
    raise RuntimeError("TF_VAR_db_password or DB_PASSWORD is required for Terraform apply")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy RifaApp Lambda + infra using Terraform")
    parser.add_argument("--infra-dir", default=os.getenv("INFRA_DIR"))
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--lambda-only", action="store_true")
    args = parser.parse_args()

    repo_root, infra_path = _resolve_paths(args.infra_dir)
    if not infra_path.exists():
        raise RuntimeError(f"Infra repo not found: {infra_path}")

    env = os.environ.copy()
    env.setdefault("TF_IN_AUTOMATION", "true")
    env.setdefault("TF_INPUT", "false")

    if not args.skip_build:
        _run(["bash", str(repo_root / "scripts" / "build_lambda.sh")], cwd=repo_root, env=env)

    lambda_dist = repo_root / "lambda_dist"
    if not lambda_dist.exists():
        raise RuntimeError("lambda_dist not found. Run scripts/build_lambda.sh first.")

    env["TF_VAR_lambda_source_dir"] = str(lambda_dist)
    _ensure_db_password(env)

    _run(["terraform", "init", "-backend-config=backend.hcl.example", "-reconfigure"], cwd=infra_path, env=env)

    if args.plan_only:
        _run(["terraform", "plan"], cwd=infra_path, env=env)
        return 0

    apply_cmd = ["terraform", "apply", "-auto-approve"]
    if args.lambda_only:
        apply_cmd.extend(["-target=aws_lambda_function.api"])

    _run(apply_cmd, cwd=infra_path, env=env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
