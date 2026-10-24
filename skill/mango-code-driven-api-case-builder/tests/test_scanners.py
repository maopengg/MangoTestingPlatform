#!/usr/bin/env python3
"""Regression tests for deterministic scanner boundaries."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scan_fastapi_ast  # noqa: E402
import scan_springboot_ast  # noqa: E402
from _common import ToolInputError, ensure_bounded_scan_root  # noqa: E402


class FastApiIndexTest(unittest.TestCase):
    def _scan(
        self,
        files: dict[str, str],
        *,
        allow_parse_errors: bool = False,
        allow_empty: bool = False,
        allow_unresolved_routes: bool = False,
    ):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative_path, source in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(source), encoding="utf-8")
        args = argparse.Namespace(
            root=[str(root)],
            paths=[],
            include=[],
            exclude=[],
            no_default_excludes=False,
            route_prefix=None,
            output="evidence.jsonl",
            output_dir=None,
            manifest_output="scan-manifest.json",
            inventory_output="endpoint-inventory.json",
            fail_on_parse_error=not allow_parse_errors,
            allow_empty=allow_empty,
            allow_unresolved_routes=allow_unresolved_routes,
        )
        return scan_fastapi_ast.run(args)

    def test_unbounded_roots_and_missing_scope_are_rejected(self) -> None:
        with self.assertRaises(ToolInputError):
            ensure_bounded_scan_root(Path(Path.home().anchor))
        with self.assertRaises(ToolInputError):
            ensure_bounded_scan_root(Path.home())
        args = scan_fastapi_ast.build_parser().parse_args([])
        with self.assertRaises(ToolInputError):
            scan_fastapi_ast.run(args)

    def test_route_and_parameters_are_indexed_without_body_logic(self) -> None:
        evidence, inventory, manifest, exit_code = self._scan(
            {
                "app.py": """
                    from fastapi import FastAPI, Query
                    app = FastAPI()

                    @app.get('/v3/items/{item_id}')
                    def get_item(item_id: int, q: str = Query(default='')):
                        if q:
                            service_call(q)
                        raise RuntimeError('business path')
                """
            }
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(manifest["analysis_ready"])
        self.assertEqual(inventory["summary"]["endpoint_count"], 1)
        self.assertEqual(
            {item["kind"] for item in evidence}, {"endpoint", "endpoint_parameter"}
        )
        self.assertFalse(
            any(
                token in item["kind"]
                for item in evidence
                for token in ("branch", "call", "return", "raise", "oracle")
            )
        )
        route = inventory["endpoints"][0]
        self.assertEqual((route["method"], route["path"]), ("GET", "/v3/items/{item_id}"))
        self.assertEqual({item["name"] for item in route["parameters"]}, {"item_id", "q"})

    def test_router_prefix_is_resolved_across_modules(self) -> None:
        _evidence, inventory, _manifest, exit_code = self._scan(
            {
                "routes.py": """
                    from fastapi import APIRouter
                    router = APIRouter(prefix='/items')

                    @router.post('/search')
                    def search(q: str):
                        return q
                """,
                "app.py": """
                    from fastapi import FastAPI
                    from routes import router
                    app = FastAPI()
                    app.include_router(router, prefix='/v3')
                """,
            }
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            {(item["method"], item["path"]) for item in inventory["endpoints"]},
            {("POST", "/v3/items/search")},
        )

    def test_parse_dynamic_and_duplicate_fail_closed(self) -> None:
        _evidence, _inventory, parse_manifest, parse_exit = self._scan(
            {"broken.py": "def broken(:\n"}
        )
        self.assertEqual(parse_exit, 2)
        self.assertIn(
            "PYTHON_PARSE_ERROR",
            {item["code"] for item in parse_manifest["blocking_reasons"]},
        )

        _evidence, _inventory, dynamic_manifest, dynamic_exit = self._scan(
            {
                "app.py": """
                    from fastapi import FastAPI
                    app = FastAPI()
                    PATH = '/v3/dynamic'

                    @app.get(PATH)
                    def dynamic():
                        return None
                """
            }
        )
        self.assertEqual(dynamic_exit, 2)
        self.assertFalse(dynamic_manifest["analysis_ready"])

        _evidence, _inventory, duplicate_manifest, duplicate_exit = self._scan(
            {
                "app.py": """
                    from fastapi import FastAPI
                    app = FastAPI()

                    @app.get('/v3/same')
                    def first():
                        return None

                    @app.get('/v3/same')
                    def second():
                        return None
                """
            },
            allow_unresolved_routes=True,
        )
        self.assertEqual(duplicate_exit, 2)
        self.assertIn(
            "DUPLICATE_ROUTE_REGISTRATION",
            {item["code"] for item in duplicate_manifest["blocking_reasons"]},
        )

    def test_exploratory_flags_never_mark_index_ready(self) -> None:
        _evidence, _inventory, manifest, exit_code = self._scan(
            {
                "app.py": """
                    from fastapi import FastAPI
                    app = FastAPI()

                    @app.get('/v3/ready')
                    def ready():
                        return True
                """
            },
            allow_parse_errors=True,
            allow_empty=True,
            allow_unresolved_routes=True,
        )
        self.assertEqual(exit_code, 0)
        self.assertFalse(manifest["analysis_ready"])
        self.assertEqual(manifest["status"], "incomplete")


@unittest.skipUnless(
    shutil.which("java") and shutil.which("javac"),
    "a JDK is required for Spring scanner regression tests",
)
class SpringIndexTest(unittest.TestCase):
    def _scan(self, files: dict[str, str], *extra_args: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for relative_path, source in files.items():
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(source), encoding="utf-8")
        output_dir = root / "output"
        args = scan_springboot_ast.build_parser().parse_args(
            ["--root", str(root), "--output-dir", str(output_dir), *extra_args]
        )
        exit_code = scan_springboot_ast.execute(args)
        inventory = json.loads(
            (output_dir / "endpoint-inventory.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (output_dir / "scan-manifest.json").read_text(encoding="utf-8")
        )
        evidence = [
            json.loads(line)
            for line in (output_dir / "evidence.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        return evidence, inventory, manifest, exit_code

    def test_routes_contracts_and_response_status_are_indexed(self) -> None:
        evidence, inventory, manifest, exit_code = self._scan(
            {
                "DemoController.java": """
                    import jakarta.validation.constraints.Min;
                    import jakarta.validation.constraints.NotBlank;
                    import org.springframework.http.HttpStatus;
                    import org.springframework.web.bind.annotation.*;

                    @RestController
                    @RequestMapping("/v3/items")
                    class DemoController {
                        @PostMapping("/{id}")
                        @ResponseStatus(HttpStatus.CREATED)
                        String update(@PathVariable @Min(1) long id,
                                      @RequestBody Body body,
                                      @RequestParam(required=false) Mode mode) {
                            if (mode == Mode.B) {
                                serviceCall(body);
                            }
                            throw new RuntimeException("business path");
                        }
                    }

                    class Body { @NotBlank String name; }
                    enum Mode { A, B }
                """
            }
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(manifest["analysis_ready"])
        self.assertEqual(
            {(item["method"], item["path"]) for item in inventory["endpoints"]},
            {("POST", "/v3/items/{id}")},
        )
        kinds = {item["kind"] for item in evidence}
        self.assertTrue({"route.mapping", "validation.bean", "validation.enum", "response.status"}.issubset(kinds))
        self.assertFalse(any(kind.startswith(("branch.", "call.", "exception.")) for kind in kinds))
        self.assertTrue(all(item["framework_adapter"] == "springboot-jdk-ast-index" for item in evidence))

    def test_valid_cascade_keeps_all_routes_and_records_interface_gaps(self) -> None:
        _evidence, inventory, manifest, exit_code = self._scan(
            {
                "PaymentPlanController.java": """
                    import jakarta.validation.Valid;
                    import org.springframework.web.bind.annotation.*;

                    @RestController
                    @RequestMapping("/contract/payment/plan")
                    class PaymentPlanController {
                        @PostMapping("/batchCreate") void batchCreate(
                                @Valid @RequestBody PlanBody body) {}
                        @PostMapping("/batchEdit") void batchEdit(
                                @Valid @RequestBody PlanBody body) {}
                        @GetMapping("/detail") void detail() {}
                        @GetMapping("/list") void list() {}
                        @PostMapping("/remove") void remove() {}
                        @PostMapping("/submit") void submit() {}
                        @PostMapping("/cancel") void cancel() {}
                        @PostMapping("/approve") void approve() {}
                        @PostMapping("/reject") void reject() {}
                    }

                    class PlanBody { String name; }
                """
            }
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(manifest["analysis_ready"])
        self.assertEqual(manifest["status"], "completed_with_gaps")
        self.assertEqual(inventory["summary"]["endpoint_count"], 9)
        self.assertEqual(manifest["summary"]["interface_analysis_gap_count"], 2)
        self.assertFalse(manifest["blocking_reasons"])
        endpoints = {
            (item["method"], item["path"]): item
            for item in inventory["endpoints"]
        }
        for path in (
            "/contract/payment/plan/batchCreate",
            "/contract/payment/plan/batchEdit",
        ):
            gaps = endpoints[("POST", path)]["analysis_gaps"]
            self.assertEqual(
                {gap["code"] for gap in gaps},
                {"SPRING_VALIDATION_CASCADE_SEMANTICS_UNRESOLVED"},
            )

    def test_route_prefix_ignores_validation_gaps_from_other_routes(self) -> None:
        _evidence, inventory, manifest, exit_code = self._scan(
            {
                "ScopedControllers.java": """
                    import jakarta.validation.Valid;
                    import org.springframework.web.bind.annotation.*;

                    @RestController
                    class PaymentController {
                        @GetMapping("/contract/payment/plan/list") void list() {}
                    }

                    @RestController
                    class OtherController {
                        @PostMapping("/outside/batch") void batch(
                                @Valid @RequestBody OtherBody body) {}
                    }

                    class OtherBody { String name; }
                """
            },
            "--route-prefix",
            "/contract/payment/plan",
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(manifest["analysis_ready"])
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(
            {(item["method"], item["path"]) for item in inventory["endpoints"]},
            {("GET", "/contract/payment/plan/list")},
        )
        self.assertFalse(manifest["interface_analysis_gaps"])
        self.assertNotIn(
            "SPRING_VALIDATION_CASCADE_SEMANTICS_UNRESOLVED",
            {warning["code"] for warning in manifest["warnings"]},
        )

    def test_dto_validation_gap_does_not_remove_linked_route(self) -> None:
        _evidence, inventory, manifest, exit_code = self._scan(
            {
                "DtoValidationController.java": """
                    import example.validation.NotBlank;
                    import org.springframework.web.bind.annotation.*;

                    @RestController
                    class DtoValidationController {
                        @PostMapping("/contract/payment/plan/create")
                        void create(@RequestBody PlanBody body) {}
                    }

                    class PlanBody { @NotBlank String name; }
                """
            }
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(manifest["analysis_ready"])
        self.assertEqual(manifest["status"], "completed_with_gaps")
        self.assertEqual(inventory["summary"]["endpoint_count"], 1)
        self.assertEqual(
            {
                gap["code"]
                for gap in inventory["endpoints"][0]["analysis_gaps"]
            },
            {"SPRING_VALIDATION_ANNOTATION_SOURCE_UNRESOLVED"},
        )

    def test_dynamic_and_duplicate_routes_fail_closed(self) -> None:
        _evidence, _inventory, dynamic_manifest, dynamic_exit = self._scan(
            {
                "DynamicController.java": """
                    import org.springframework.web.bind.annotation.*;
                    @RestController
                    class DynamicController {
                        static final String PATH = "/v3/dynamic";
                        @GetMapping(PATH)
                        void dynamic() {}
                    }
                """
            }
        )
        self.assertEqual(dynamic_exit, 2)
        self.assertFalse(dynamic_manifest["analysis_ready"])

        _evidence, _inventory, duplicate_manifest, duplicate_exit = self._scan(
            {
                "DuplicateController.java": """
                    import org.springframework.web.bind.annotation.*;
                    @RestController
                    class DuplicateController {
                        @GetMapping("/v3/same") void first() {}
                        @GetMapping("/v3/same") void second() {}
                    }
                """
            },
            "--allow-unresolved-routes",
        )
        self.assertEqual(duplicate_exit, 2)
        self.assertIn(
            "DUPLICATE_ROUTE_REGISTRATION",
            {item["code"] for item in duplicate_manifest["blocking_reasons"]},
        )

    def test_exploratory_flags_do_not_claim_analysis_ready(self) -> None:
        _evidence, _inventory, manifest, exit_code = self._scan(
            {
                "ReadyController.java": """
                    import org.springframework.web.bind.annotation.*;
                    @RestController
                    class ReadyController {
                        @GetMapping("/v3/ready") boolean ready() { return true; }
                    }
                """
            },
            "--allow-parse-errors",
            "--allow-empty",
            "--allow-unresolved-routes",
        )
        self.assertEqual(exit_code, 0)
        self.assertFalse(manifest["analysis_ready"])
        self.assertEqual(manifest["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
