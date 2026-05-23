#!/usr/bin/env python3
"""Task runner for davisgroup.uk.

Usage:
    uv run make.py [task]

Default task: fmt
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
NPM_APPS = ["share-location", "chikorita", "freebee"]


def sh(*args, env=None, check=True):
    command = [str(arg) for arg in args]
    print("+", " ".join(command))
    env_vars = os.environ.copy()
    if env:
        env_vars.update(env)
    subprocess.run(command, cwd=ROOT, env=env_vars, check=check)


def build_npm() -> None:
    for project in NPM_APPS:
        destination = ROOT / "dist" / project
        destination.mkdir(parents=True, exist_ok=True)
        sh("bun", "i", "--cwd", str(ROOT / project))
        sh("bun", "run", "--cwd", str(ROOT / project), "build")

    sh(
        "rsync",
        "-rv",
        "--delete",
        str(ROOT / "freebee" / "api") + "/",
        str(ROOT / "dist" / "freebee" / "api") + "/",
    )


def compress() -> None:
    dist_root = ROOT / "dist"
    if not dist_root.exists():
        print("No dist directory found; nothing to compress.")
        return

    for path in dist_root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix in {".gz", ".zst"}:
            continue

        sh("gzip", "-fk", str(path))
        sh("zstd", "-fk", str(path))

        for suffix in [".gz", ".zst"]:
            compressed = pathlib.Path(str(path) + suffix)
            if compressed.exists() and path.stat().st_size <= compressed.stat().st_size:
                compressed.unlink()


def build_md() -> None:
    sh("bash", str(ROOT / "writeups" / "compile"))


def cp_static() -> None:
    sh("rsync", "-rv", str(ROOT / "static") + "/", str(ROOT / "dist") + "/")


def build() -> None:
    build_npm()
    build_md()
    cp_static()
    compress()


def deploy_test() -> None:
    env = {"ANSIBLE_CONFIG": str(ROOT / "ansible" / "ansible.cfg")}
    sh(
        "ansible-playbook",
        "-K",
        "--diff",
        "--check",
        "-vv",
        str(ROOT / "ansible" / "playbooks" / "deploy.json"),
        env=env,
    )


def deploy() -> None:
    env = {"ANSIBLE_CONFIG": str(ROOT / "ansible" / "ansible.cfg")}
    sh(
        "ansible-playbook",
        "-K",
        str(ROOT / "ansible" / "playbooks" / "deploy.json"),
        env=env,
    )
    sh("rsync", "-r", "--delete", "./dist/", "steve@davisgroup.uk:/var/www/html-predeploy")


def dev() -> None:
    sh("python3", "-m", "http.server", "-d", str(ROOT / "dist"), "50000")


def fmt() -> None:
    sh("uv", "run", "ruff", "check", "--fix", "--unsafe-fixes")
    sh("bun", "run", "biome", "format", "--write")


tasks = {
    "build_npm": build_npm,
    "compress": compress,
    "build_md": build_md,
    "cp_static": cp_static,
    "build": build,
    "deploy_test": deploy_test,
    "deploy": deploy,
    "dev": dev,
    "fmt": fmt,
}


def print_help() -> None:
    print("Usage: python make.py [task]\n")
    print("Available tasks:")
    for name in sorted(tasks):
        print(f"  {name}")
    print("\nDefault task: fmt")


def main() -> int:
    task_name = "fmt" if len(sys.argv) <= 1 else sys.argv[1]

    task = tasks.get(task_name)
    if task is None:
        print(f"Unknown task: {task_name}\n")
        print_help()
        return 1

    task()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
