import hashlib
from pathlib import Path
from unittest import TestCase


ACTUATOR_ROOT = Path(__file__).resolve().parents[1]


class ServerDependencyManifestTests(TestCase):
    @staticmethod
    def linux_local_dependencies() -> list[str]:
        return [
            line.strip().removeprefix("./")
            for line in (ACTUATOR_ROOT / "requirements" / "linux-local.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def test_linux_server_local_dependencies_exclude_desktop_ui(self):
        requirements = (
            ACTUATOR_ROOT / "requirements" / "linux-local.txt"
        ).read_text(encoding="utf-8").lower()

        self.assertIn("mangotools", requirements)
        self.assertIn("mangoautomation", requirements)
        self.assertNotIn("mangoui", requirements)
        self.assertNotIn("pyside", requirements)

    def test_docker_stages_use_linux_server_local_dependencies(self):
        dockerfile = (ACTUATOR_ROOT / "deploy" / "docker" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn(
            "FROM mcr.microsoft.com/playwright/python:v1.62.0-noble AS core_runtime",
            dockerfile,
        )
        self.assertNotIn("docker.io/playwright", dockerfile)
        self.assertEqual(dockerfile.count("-r requirements/linux-local.txt"), 1)
        self.assertNotIn("--force-reinstall", dockerfile)
        self.assertNotIn("FROM grafana/k6", dockerfile)
        self.assertIn("deploy/packages/k6/k6-v${K6_VERSION}-linux-${TARGETARCH}.tar.gz", dockerfile)
        self.assertIn("install -m 0755 /tmp/k6/k6 /usr/local/bin/k6", dockerfile)
        self.assertIn("FROM core_runtime AS standard", dockerfile)
        self.assertIn("FROM standard AS android", dockerfile)
        self.assertIn("ARG ACTUATOR_PROFILE=standard", dockerfile)
        self.assertNotIn("-r requirements/desktop-local.txt", dockerfile)
        self.assertNotIn("COPY local_packages ./local_packages", dockerfile)

    def test_linux_local_dependency_wheels_exist_and_are_copied_by_every_stage(self):
        dockerfile = (ACTUATOR_ROOT / "deploy" / "docker" / "Dockerfile").read_text(encoding="utf-8")

        for dependency_path in self.linux_local_dependencies():
            self.assertTrue(
                (ACTUATOR_ROOT / dependency_path).is_file(),
                f"本地依赖不存在：{dependency_path}",
            )
            self.assertEqual(dockerfile.count(dependency_path), 1)

    def test_local_internal_packages_only_keep_declared_wheels(self):
        local_package_root = ACTUATOR_ROOT / "local_packages"
        declared_wheels = {
            Path(dependency).name
            for dependency in self.linux_local_dependencies()
            if dependency.endswith(".whl")
        }
        actual_wheels = {package.name for package in local_package_root.glob("*.whl")}

        self.assertEqual(actual_wheels, declared_wheels)

    def test_k6_linux_archives_are_local_and_checksum_verified(self):
        expected = {
            "k6-v2.2.0-linux-amd64.tar.gz": "b5a8003c86f35f5cd5ceef1490312c48e587696c94d998cefc6d7b3b4cb1597d",
            "k6-v2.2.0-linux-arm64.tar.gz": "4ecd64cadcc792402d16293836115480419c4447c032858f564852d98f1bf54c",
        }
        package_root = ACTUATOR_ROOT / "deploy" / "packages" / "k6"

        for filename, checksum in expected.items():
            package = package_root / filename
            self.assertTrue(package.is_file(), f"缺少 k6 本地安装包：{filename}")
            digest = hashlib.sha256()
            with package.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            self.assertEqual(digest.hexdigest(), checksum)
