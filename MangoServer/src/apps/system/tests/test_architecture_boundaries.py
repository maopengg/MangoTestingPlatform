import ast
import re
import symtable
from pathlib import Path

import builtins
import mangotools.contracts
from django.apps import apps
from django.conf import settings
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase

SRC_ROOT = Path(__file__).resolve().parents[3]
APPS_ROOT = SRC_ROOT / "apps"
REPOSITORY_ROOT = SRC_ROOT.parents[1]
ACTUATOR_SRC_ROOT = REPOSITORY_ROOT / "MangoActuator" / "src"
PROMPTS_ROOT = SRC_ROOT / "common" / "prompts"
PYDANTIC_BASES = {
    "BaseModel",
    "RootModel",
    "StrictSchema",
    "FrozenSchema",
    "OpenSchema",
    "OrmSchema",
    "TrimmedStrictSchema",
}

SERVICE_CAPABILITY_GROUPS = {
    'auto_api': 'api_case api_import api_info authentication callbacks configuration coverage execution execution_trace mock protocols resource_cleanup',
    'auto_pytest': 'assets execution reporting repository synchronization',
    'auto_ui': 'assets authentication cases elements execution live_stream page_steps pages reporting',
    'data_factory': 'assets cleanup datasource execution governance pool preview protocols recovery reporting schema sql',
    'evaluation': 'assets dataset execution grading model reporting targets workflow',
    'functional_test': 'cases execution integration requirements suites',
    'monitoring': 'diagnostics execution logging tasks',
    'perf': 'capacity compilation execution reporting scenario security',
    'system': 'actuator ai catalog configuration coordination initialization notice runtime_center runtime_kv socket_link',
    'task_center': 'execution scheduling selection workbench',
    'test_center': 'datasource diagnostics environment project reporting results storage',
    'user': 'account authentication authorization preferences audit',
}


def _python_files(root: Path):
    return (
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and "migrations" not in path.parts
    )


def _contains_python_sources(path: Path) -> bool:
    """Return whether a legacy namespace still contains importable source code."""
    return path.is_file() and path.suffix == ".py" or (
            path.is_dir()
            and any(
        source.is_file() and "__pycache__" not in source.parts
        for source in path.rglob("*.py")
    )
    )


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name


def _class_base_names(node: ast.ClassDef) -> set[str]:
    return {ast.unparse(base).split(".")[-1] for base in node.bases}


def _is_enum_definition(node: ast.ClassDef) -> bool:
    bases = _class_base_names(node)
    return node.name.endswith(("Enum", "Choices")) or bool(bases & {"Enum", "IntEnum", "BaseEnum"})


def _enum_members(node: ast.ClassDef) -> dict[str, str]:
    members = {}
    for statement in node.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        value = statement.value
        if value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                members[target.id] = ast.dump(value, include_attributes=False)
    return members


class ArchitectureBoundaryTests(SimpleTestCase):
    def test_service_implementations_live_in_registered_capability_groups(self):
        violations = []
        service_apps = {app.name for app in APPS_ROOT.iterdir()
                        if (app / 'apps.py').is_file() and (app / 'services').is_dir()}
        self.assertEqual(service_apps, set(SERVICE_CAPABILITY_GROUPS))
        for app_name, groups in SERVICE_CAPABILITY_GROUPS.items():
            root = APPS_ROOT / app_name / 'services'
            allowed = set(groups.split())
            for source in _python_files(root):
                relative = source.relative_to(root)
                if source.name == '__init__.py':
                    continue
                if len(relative.parts) == 1 or relative.parts[0] not in allowed:
                    violations.append(str(source.relative_to(SRC_ROOT)))
            actual = {directory.name for directory in root.iterdir()
                      if directory.is_dir() and directory.name != '__pycache__'
                      and any(path.name != '__init__.py' for path in _python_files(directory))}
            self.assertEqual(allowed, actual, app_name)
        self.assertEqual([], violations, 'Service 按 AGENTS.md 的业务能力分组，禁止根级平铺或未登记分类')

    # Temporary ceilings capture the pre-cleanup architecture debt. Each focused
    # migration removes its ceiling and replaces it with a zero-tolerance guard.
    DRF_SERIALIZERS_OUTSIDE_HTTP_BASELINE = 0
    SERIALIZER_TO_VIEW_IMPORT_BASELINE = 0
    SERVICE_TO_LEGACY_DRF_SCHEMA_BASELINE = 0
    INLINE_RESPONSE_MESSAGE_BASELINE = 0
    RAW_EXCEPTION_RESPONSE_BASELINE = 0
    DIRECT_APP_BASE_MODEL_BASELINE = 0
    ACTUATOR_ENUM_OUTSIDE_ENUM_PACKAGE_BASELINE = 1
    APP_BIDIRECTIONAL_DEPENDENCY_BASELINE = 29
    UNNAMED_MODEL_INDEX_BASELINE = 62

    def test_system_package_keeps_its_persisted_migration_label(self):
        system_config = apps.get_app_config("auto_system")
        self.assertEqual("src.apps.system", system_config.name)
        self.assertEqual("auto_system", system_config.label)

    def test_test_center_has_a_complete_state_only_migration_baseline(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        baseline = ("test_center", "0002_execution_models_state")
        self.assertIn(baseline, loader.graph.nodes)

        state = loader.project_state([baseline])
        migrated_models = {
            model_name
            for app_label, model_name in state.models
            if app_label == "test_center"
        }
        runtime_models = {
            model._meta.model_name
            for model in apps.get_app_config("test_center").get_models()
        }
        self.assertEqual(runtime_models, migrated_models)
        self.assertIn("owners", state.models[("test_center", "projectproduct")].fields)

    def test_legacy_django_admin_and_session_stack_do_not_return(self):
        forbidden_apps = {
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.messages",
            "django.contrib.sessions",
        }
        forbidden_middleware = {
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        }
        violations = [
            f"INSTALLED_APPS:{app}"
            for app in settings.INSTALLED_APPS
            if app in forbidden_apps
        ]
        violations.extend(
            f"MIDDLEWARE:{middleware}"
            for middleware in settings.MIDDLEWARE
            if middleware in forbidden_middleware
        )
        violations.extend(
            str(path.relative_to(SRC_ROOT))
            for path in APPS_ROOT.glob("*/admin.py")
        )
        self.assertEqual([], violations)

    def test_drf_does_not_depend_on_django_anonymous_user(self):
        self.assertIsNone(settings.REST_FRAMEWORK.get("UNAUTHENTICATED_USER"))
        self.assertIsNone(settings.REST_FRAMEWORK.get("UNAUTHENTICATED_TOKEN"))

    def test_python_global_names_are_defined(self):
        ignored_names = {
            "__annotations__",
            "__cached__",
            "__doc__",
            "__file__",
            "__loader__",
            "__name__",
            "__package__",
            "__spec__",
        }
        violations = []
        for path in _python_files(SRC_ROOT):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            table = symtable.symtable(source, str(path), "exec")
            defined = set(dir(builtins)) | ignored_names

            def collect_module_definitions(node):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    return
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    defined.add(node.id)
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        defined.add(
                            alias.asname
                            or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name)
                        )
                for child in ast.iter_child_nodes(node):
                    collect_module_definitions(child)

            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined.add(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        if alias.name != "*":
                            defined.add(
                                alias.asname
                                or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name)
                            )
                else:
                    collect_module_definitions(node)

            referenced_globals = set()
            scopes = [table]
            while scopes:
                scope = scopes.pop()
                referenced_globals.update(
                    symbol.get_name()
                    for symbol in scope.get_symbols()
                    if symbol.is_referenced() and symbol.is_global()
                )
                scopes.extend(scope.get_children())
            for name in sorted(referenced_globals - defined):
                violations.append(f"{path.relative_to(SRC_ROOT)} -> {name}")
        self.assertEqual([], violations)

    def test_log_calls_have_a_module_definition(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            source = path.read_text(encoding="utf-8")
            table = symtable.symtable(source, str(path), "exec")
            try:
                module_log = table.lookup("log")
                module_log_defined = (
                        module_log.is_imported()
                        or module_log.is_assigned()
                        or module_log.is_parameter()
                )
            except KeyError:
                module_log_defined = False

            scopes = [table]
            while scopes:
                scope = scopes.pop()
                try:
                    symbol = scope.lookup("log")
                except KeyError:
                    symbol = None
                if symbol and symbol.is_referenced():
                    unresolved = (
                                         scope is table and not module_log_defined
                                 ) or (
                                         scope is not table
                                         and symbol.is_global()
                                         and not module_log_defined
                                 )
                    if unresolved:
                        violations.append(
                            f"{path.relative_to(SRC_ROOT)}:{scope.get_lineno()} {scope.get_name()}"
                        )
                scopes.extend(scope.get_children())
        self.assertEqual([], violations)

    def test_django_models_live_only_in_app_model_modules(self):
        violations = []
        for path in _python_files(APPS_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                bases = _class_base_names(node)
                if not (bases & {"Model", "AuditModel", "CreatedAtModel", "TimeStampedModel"}):
                    continue
                relative = path.relative_to(APPS_ROOT)
                if path.name != "models.py" and "models" not in relative.parts:
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_optional_model_fields_allow_blank_values(self):
        violations = []
        for path in _python_files(APPS_ROOT):
            relative = path.relative_to(APPS_ROOT)
            if path.name != "models.py" and "models" not in relative.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                value = node.value
                if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute):
                    continue
                field_type = value.func.attr
                if not field_type.endswith("Field"):
                    continue
                keywords = {keyword.arg: keyword.value for keyword in value.keywords if keyword.arg}
                blank = keywords.get("blank")
                blank_allowed = isinstance(blank, ast.Constant) and blank.value is True
                null = keywords.get("null")
                null_allowed = isinstance(null, ast.Constant) and null.value is True
                default = keywords.get("default")
                empty_json_default = (
                        field_type == "JSONField"
                        and isinstance(default, ast.Name)
                        and default.id in {"list", "dict"}
                )
                if (null_allowed or empty_json_default) and not blank_allowed:
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    field_name = targets[0].id if targets and isinstance(targets[0], ast.Name) else "?"
                    violations.append(
                        f"{path.relative_to(SRC_ROOT)}:{node.lineno} {field_name}"
                    )
        self.assertEqual([], violations)

    def test_managed_business_models_have_database_comments(self):
        missing_table_comments = []
        missing_field_comments = []
        for model in apps.get_models():
            if not model.__module__.startswith("src.apps."):
                continue
            if not model._meta.managed or model._meta.proxy:
                continue
            if not model._meta.db_table_comment:
                missing_table_comments.append(model._meta.label)
            for field in model._meta.local_fields:
                if field.concrete and not field.db_comment:
                    missing_field_comments.append(f"{model._meta.label}.{field.name}")

        self.assertEqual([], missing_table_comments)
        self.assertEqual([], missing_field_comments)

    def test_unnamed_model_indexes_do_not_grow(self):
        unnamed_indexes = []
        for path in _python_files(APPS_ROOT):
            relative = path.relative_to(APPS_ROOT)
            if path.name != "models.py" and "models" not in relative.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Attribute) or node.func.attr != "Index":
                    continue
                if any(keyword.arg == "name" for keyword in node.keywords):
                    continue
                unnamed_indexes.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")

        self.assertLessEqual(
            len(unnamed_indexes),
            self.UNNAMED_MODEL_INDEX_BASELINE,
            unnamed_indexes,
        )

    def test_pydantic_schemas_live_only_in_schema_packages(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or not (_class_base_names(node) & PYDANTIC_BASES):
                    continue
                relative = path.relative_to(SRC_ROOT)
                if relative.parts[:2] == ("common", "schemas"):
                    continue
                if len(relative.parts) >= 4 and relative.parts[0] == "apps" and relative.parts[2] == "schemas":
                    continue
                violations.append(f"{relative}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_drf_serializers_live_only_in_http_serializer_packages(self):
        violations = []
        for path in APPS_ROOT.glob("*/api/**/*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if not any(base.endswith("Serializer") for base in _class_base_names(node)):
                    continue
                if "serializers" not in path.relative_to(APPS_ROOT).parts:
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_drf_serializers_outside_http_packages_do_not_grow(self):
        violations = []
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            relative = path.relative_to(APPS_ROOT)
            in_http_package = len(relative.parts) >= 3 and relative.parts[1:3] == ("api", "serializers")
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if any(base.endswith("Serializer") for base in _class_base_names(node)) and not in_http_package:
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertLessEqual(len(violations), self.DRF_SERIALIZERS_OUTSIDE_HTTP_BASELINE, violations)

    def test_http_serializers_do_not_add_view_imports(self):
        violations = []
        for path in APPS_ROOT.glob("*/api/serializers/**/*.py"):
            for module in _imports(path):
                if ".api.views" in module:
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertLessEqual(len(violations), self.SERIALIZER_TO_VIEW_IMPORT_BASELINE, violations)

    def test_services_do_not_add_legacy_drf_schema_dependencies(self):
        violations = []
        for app in APPS_ROOT.iterdir():
            root = app / "services"
            if not root.exists():
                continue
            for path in _python_files(root):
                for module in _imports(path):
                    if ".schemas.mutation_serializers" in module or ".schemas.presentation_serializers" in module:
                        violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertLessEqual(len(violations), self.SERVICE_TO_LEGACY_DRF_SCHEMA_BASELINE, violations)

    def test_large_http_views_delegate_persistence_to_services(self):
        violations = []
        manager_writes = {"create", "bulk_create", "update", "bulk_update", "get_or_create", "update_or_create"}

        def uses_model_manager(node):
            return any(
                isinstance(item, ast.Attribute) and item.attr == "objects"
                for item in ast.walk(node)
            )

        for path in APPS_ROOT.glob("*/api/views/**/*.py"):
            source = path.read_text(encoding="utf-8")
            if len(source.splitlines()) < 600:
                continue
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                method = node.func.attr
                if method in manager_writes and uses_model_manager(node.func.value):
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {method}")
                elif method == "save":
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {method}")
                elif method == "delete":
                    owner = node.func.value
                    is_super_delete = isinstance(owner, ast.Call) and isinstance(owner.func,
                                                                                 ast.Name) and owner.func.id == "super"
                    if not is_super_delete:
                        violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} delete")
                elif method == "atomic":
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} transaction.atomic")
        self.assertEqual([], violations)

    def test_response_boundary_debt_does_not_grow(self):
        inline_messages = []
        raw_errors = []
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            inline_messages.extend(
                f"{path.relative_to(SRC_ROOT)}:{index}"
                for index, line in enumerate(source.splitlines(), start=1)
                if re.search(r"ResponseData\.(?:fail|error)\(\(\d+,\s*f?[\"']", line)
            )
            raw_errors.extend(
                f"{path.relative_to(SRC_ROOT)}:{index}"
                for index, line in enumerate(source.splitlines(), start=1)
                if "ResponseData." in line and re.search(r"str\((?:e|exc|error)\)", line)
            )
        self.assertLessEqual(len(inline_messages), self.INLINE_RESPONSE_MESSAGE_BASELINE, inline_messages)
        self.assertLessEqual(len(raw_errors), self.RAW_EXCEPTION_RESPONSE_BASELINE, raw_errors)

    def test_unclassified_pydantic_and_actuator_enum_debt_does_not_grow(self):
        direct_base_models = []
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and "BaseModel" in _class_base_names(node):
                    direct_base_models.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertLessEqual(len(direct_base_models), self.DIRECT_APP_BASE_MODEL_BASELINE, direct_base_models)

        actuator_enums = []
        for path in _python_files(ACTUATOR_SRC_ROOT):
            if "tests" in path.parts or "enums" in path.relative_to(ACTUATOR_SRC_ROOT).parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and _is_enum_definition(node):
                    actuator_enums.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno} {node.name}")
        self.assertLessEqual(
            len(actuator_enums),
            self.ACTUATOR_ENUM_OUTSIDE_ENUM_PACKAGE_BASELINE,
            actuator_enums,
        )

    def test_dataclasses_are_not_transport_contracts(self):
        violations = []
        # Process-local dataclasses are valid internal state. Public MCP payloads
        # must be Pydantic contracts so every caller receives the same validation.
        forbidden_roots = (SRC_ROOT / "interfaces",)
        for root in forbidden_roots:
            for path in _python_files(root):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in tree.body:
                    if not isinstance(node, ast.ClassDef):
                        continue
                    decorators = set()
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorators.add(decorator.id)
                        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                            decorators.add(decorator.func.id)
                    if "dataclass" in decorators and node.name.endswith(
                            ("Contract", "Request", "Response", "Command", "Event", "Payload")
                    ):
                        violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_removed_schema_model_namespaces_do_not_return(self):
        violations = []
        for app in APPS_ROOT.iterdir():
            legacy = app / "schemas" / "models"
            if legacy.exists() and any(_python_files(legacy)):
                violations.append(str(legacy.relative_to(SRC_ROOT)))
        forbidden_modules = [
            APPS_ROOT / "auto_api" / "schemas" / "runtime.py",
            APPS_ROOT / "auto_ui" / "schemas" / "runtime.py",
            APPS_ROOT / "auto_pytest" / "schemas" / "runtime.py",
            APPS_ROOT / "system" / "schemas" / "runtime.py",
        ]
        violations.extend(str(path.relative_to(SRC_ROOT)) for path in forbidden_modules if path.exists())
        self.assertEqual([], violations)

    def test_retired_ai_apps_and_workers_do_not_return(self):
        for path in (
            APPS_ROOT / "ai",
            APPS_ROOT / "case_generation",
            SRC_ROOT / "common" / "database" / "retired_ai",
            SRC_ROOT / "processes" / "ai_worker",
            SRC_ROOT / "processes" / "case_generation_worker",
            SRC_ROOT / "interfaces" / "mcp" / "tools" / "ai",
        ):
            with self.subTest(path=str(path)):
                self.assertFalse(path.exists())
        loader = MigrationLoader(None)
        self.assertFalse(any(label == "auto_ai" for label, _ in loader.graph.nodes))
        state = loader.project_state()
        for model in state.models.values():
            for field in model.fields.values():
                target = getattr(getattr(field, "remote_field", None), "model", None)
                self.assertFalse(isinstance(target, str) and target.startswith("auto_ai."))

    def test_removed_actuator_protocol_modules_do_not_return(self):
        forbidden = [
            ACTUATOR_SRC_ROOT / "models" / "api_model.py",
            ACTUATOR_SRC_ROOT / "models" / "pytest_model.py",
            ACTUATOR_SRC_ROOT / "models" / "ui_model.py",
        ]
        violations = [str(path.relative_to(REPOSITORY_ROOT)) for path in forbidden if path.exists()]
        self.assertEqual([], violations)

    def test_shared_contracts_do_not_import_application_code(self):
        contracts_root = Path(mangotools.contracts.__file__).resolve().parent
        violations = []
        for path in _python_files(contracts_root):
            for module in _imports(path):
                if module == "src" or module.startswith("src.") or module.startswith("mangoautomation"):
                    violations.append(f"{path.relative_to(contracts_root)} -> {module}")
        self.assertEqual([], violations)

    def test_app_bidirectional_dependencies_do_not_grow(self):
        dependencies = set()
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            source_app = path.relative_to(APPS_ROOT).parts[0]
            for module in _imports(path):
                parts = module.split(".")
                if len(parts) < 4 or parts[:2] != ["src", "apps"]:
                    continue
                target_app = parts[2]
                if target_app != source_app:
                    dependencies.add((source_app, target_app))

        bidirectional = {
            tuple(sorted((source, target)))
            for source, target in dependencies
            if (target, source) in dependencies
        }
        self.assertLessEqual(
            len(bidirectional),
            self.APP_BIDIRECTIONAL_DEPENDENCY_BASELINE,
            sorted(bidirectional),
        )
        removed_cycles = {
            ("auto_api", "user"),
            ("auto_pytest", "user"),
            ("auto_ui", "user"),
            ("perf", "task_center"),
        }
        self.assertEqual(set(), bidirectional & removed_cycles)

    def test_star_imports_are_forbidden(self):
        violations = []
        for root in (SRC_ROOT, ACTUATOR_SRC_ROOT):
            for path in _python_files(root):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                        violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
        self.assertEqual([], violations)

    def test_app_exceptions_use_packages_not_single_files(self):
        violations = []
        for app in APPS_ROOT.iterdir():
            if not app.is_dir():
                continue
            legacy = app / "exceptions.py"
            if legacy.exists():
                violations.append(str(legacy.relative_to(SRC_ROOT)))
            package = app / "exceptions"
            if package.exists() and not (package / "__init__.py").exists():
                violations.append(f"{package.relative_to(SRC_ROOT)} missing __init__.py")
        self.assertEqual([], violations)

    def test_business_error_definitions_live_in_exception_packages(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name) or "ERROR" not in target.id:
                    continue
                if not isinstance(node.value, ast.Call):
                    continue
                callable_name = ast.unparse(node.value.func).split(".")[-1]
                if callable_name != "ErrorDefinition":
                    continue
                relative = path.relative_to(SRC_ROOT)
                in_common = relative.parts[:2] == ("common", "exceptions")
                in_app = len(relative.parts) >= 3 and relative.parts[0] == "apps" and relative.parts[2] == "exceptions"
                in_interface = relative.parts[:3] == ("interfaces", "mcp", "exceptions")
                if not (in_common or in_app or in_interface):
                    violations.append(f"{relative}:{node.lineno} {target.id}")
        self.assertEqual([], violations)

    def test_expected_exception_classes_live_in_exception_packages(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if "MangoServerError" not in _class_base_names(node):
                    continue
                relative = path.relative_to(SRC_ROOT)
                if "exceptions" not in relative.parts:
                    violations.append(f"{relative}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_legacy_exception_catalogs_and_generic_classes_do_not_return(self):
        forbidden_paths = [
            SRC_ROOT / "common" / "exceptions" / "error_msg.py",
            SRC_ROOT / "common" / "exceptions" / "messages.py",
        ]
        forbidden_paths.extend(APPS_ROOT.glob("*/exceptions.py"))
        violations = [str(path.relative_to(SRC_ROOT)) for path in forbidden_paths if path.exists()]
        forbidden_names = {"ApiError", "UiError", "PytestError", "ToolsError", "SystemEError"}
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id in forbidden_names:
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.id}")
        self.assertEqual([], violations)

    def test_production_code_uses_named_error_definitions(self):
        error_classes = {
            "AiError",
            "AutoApiError",
            "AutoPytestError",
            "AutoUiError",
            "CommonError",
            "DataFactoryError",
            "FunctionalTestError",
            "GrayConfigError",
            "McpAuthError",
            "McpError",
            "MonitoringError",
            "PerfError",
            "SystemError",
            "TaskCenterError",
            "TestCenterError",
            "UserError",
        }
        violations = []
        for path in _python_files(SRC_ROOT):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                    continue
                if node.func.id not in error_classes or not node.args:
                    continue
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, int):
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.func.id}")
        self.assertEqual([], violations)

    def test_legacy_error_message_names_do_not_return(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith("ERROR_MSG_"):
                        if isinstance(node.value, ast.Call) and ast.unparse(node.value.func).endswith(
                                "ErrorDefinition"):
                            violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {target.id}")
        self.assertEqual([], violations)

    def test_error_definition_names_are_semantic(self):
        """Numbered catalog names hide intent and must not return."""
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                    continue
                if ast.unparse(node.value.func).split(".")[-1] != "ErrorDefinition":
                    continue
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id.startswith("ERROR_MSG_") or re.search(r"(?:ERROR|CODE)_\d{4}$", target.id):
                        violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {target.id}")
        self.assertEqual([], violations)

    def test_app_error_codes_are_unique(self):
        violations = []
        for app in APPS_ROOT.iterdir():
            package = app / "exceptions"
            if not package.exists():
                continue
            definitions = {}
            for path in _python_files(package):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in tree.body:
                    if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                        continue
                    if ast.unparse(node.value.func).split(".")[-1] != "ErrorDefinition":
                        continue
                    code = next(
                        (
                            keyword.value.value
                            for keyword in node.value.keywords
                            if keyword.arg == "code" and isinstance(keyword.value, ast.Constant)
                        ),
                        None,
                    )
                    name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else "?"
                    if code in definitions:
                        violations.append(
                            f"{app.name}:{code} {definitions[code]} != {path.relative_to(SRC_ROOT)}:{node.lineno} {name}"
                        )
                    definitions[code] = f"{path.relative_to(SRC_ROOT)}:{node.lineno} {name}"
        self.assertEqual([], violations)

    def test_expected_error_constructors_are_strict(self):
        error_classes = {
            "AiError", "AutoApiError", "AutoPytestError", "AutoUiError", "CommonError",
            "DataFactoryError", "FunctionalTestError", "GrayConfigError", "McpAuthError", "McpError",
            "MonitoringError", "PerfError", "SystemError", "TaskCenterError",
            "TestCenterError", "UserError",
        }
        violations = []
        for path in _python_files(SRC_ROOT):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                    continue
                if node.func.id not in error_classes:
                    continue
                if len(node.args) != 1 or isinstance(node.args[0], ast.Starred):
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.func.id}")
        self.assertEqual([], violations)

    def test_app_exception_classes_live_in_exception_packages(self):
        violations = []
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                if "Exception" not in _class_base_names(node):
                    continue
                if "exceptions" not in path.relative_to(SRC_ROOT).parts:
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_mcp_tools_do_not_catch_model_does_not_exist(self):
        violations = []
        for path in _python_files(SRC_ROOT / "interfaces" / "mcp" / "tools"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler) or node.type is None:
                    continue
                if "DoesNotExist" in ast.unparse(node.type):
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
        self.assertEqual([], violations)

    def test_unknown_exception_responses_do_not_expose_raw_errors(self):
        rest_source = (SRC_ROOT / "common" / "decorators" / "error_response.py").read_text(encoding="utf-8")
        mcp_source = (SRC_ROOT / "interfaces" / "mcp" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("data=str(error)", rest_source)
        self.assertNotIn('"error": str(exc)', mcp_source)

    def test_backend_enums_are_defined_only_in_enum_packages(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or not _is_enum_definition(node):
                    continue
                relative = path.relative_to(SRC_ROOT)
                if "enums" not in relative.parts:
                    violations.append(f"{relative}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_services_and_processes_do_not_define_business_pseudo_enums(self):
        suffixes = ("Type", "Status", "Role", "Source", "Command", "Mode", "Category", "Level", "Scope", "Scene",
                    "Kind")
        violations = []
        roots = [SRC_ROOT / "processes"] + [path / "services" for path in APPS_ROOT.iterdir()]
        for root in roots:
            if not root.exists():
                continue
            for path in _python_files(root):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in tree.body:
                    if not isinstance(node, ast.ClassDef) or not node.name.endswith(suffixes):
                        continue
                    if len(_enum_members(node)) >= 2:
                        violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_same_named_backend_enums_do_not_have_different_values(self):
        definitions = {}
        violations = []
        for path in _python_files(SRC_ROOT):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or not _is_enum_definition(node):
                    continue
                members = _enum_members(node)
                previous = definitions.get(node.name)
                current = (members, f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
                if previous and previous[0] != members:
                    violations.append(f"{node.name}: {previous[1]} != {current[1]}")
                definitions[node.name] = current
        self.assertEqual([], violations)

    def test_python_package_directories_have_init_modules(self):
        violations = []
        for directory in SRC_ROOT.rglob("*"):
            if not directory.is_dir() or "__pycache__" in directory.parts:
                continue
            if not any(directory.rglob("*.py")):
                continue
            if not (directory / "__init__.py").exists():
                violations.append(str(directory.relative_to(SRC_ROOT)))
        self.assertEqual([], violations)

    def test_common_production_code_does_not_import_business_apps(self):
        violations = []
        for path in _python_files(SRC_ROOT / "common"):
            if path.name.startswith("test") or path.name == "tests.py":
                continue
            for module in _imports(path):
                if module.startswith("src.apps."):
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_services_and_mcp_do_not_import_http_views(self):
        roots = [SRC_ROOT / "interfaces" / "mcp"]
        for app in APPS_ROOT.iterdir():
            roots.append(app / "services")
        violations = []
        for root in roots:
            if not root.exists():
                continue
            for path in _python_files(root):
                for module in _imports(path):
                    if ".api.views." in module or ".views." in module:
                        violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_services_do_not_import_http_serializers(self):
        violations = []
        for app in APPS_ROOT.iterdir():
            for root in (app / "services",):
                if not root.exists():
                    continue
                for path in _python_files(root):
                    if "tests" in path.parts:
                        continue
                    for module in _imports(path):
                        if ".api.serializers" in module:
                            violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_mcp_adapter_does_not_access_model_managers_directly(self):
        violations = []
        root = SRC_ROOT / "interfaces" / "mcp"
        for path in _python_files(root):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "objects":
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
        self.assertEqual([], violations)

    def test_mcp_adapter_does_not_import_http_layers(self):
        violations = []
        root = SRC_ROOT / "interfaces" / "mcp"
        for path in _python_files(root):
            if "tests" in path.parts:
                continue
            for module in _imports(path):
                if ".api.views" in module or ".api.serializers" in module:
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_runtime_adapters_do_not_access_model_managers_directly(self):
        violations = []
        root = SRC_ROOT / "processes"
        for path in _python_files(root):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "objects":
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
        self.assertEqual([], violations)

    def test_runtime_adapters_do_not_import_models_or_http_layers(self):
        violations = []
        root = SRC_ROOT / "processes"
        for path in _python_files(root):
            if "tests" in path.parts:
                continue
            for module in _imports(path):
                if (
                        (module.startswith("src.apps.") and module.endswith(".models"))
                        or ".api.views" in module
                        or ".api.serializers" in module
                ):
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_apps_do_not_cross_import_http_views(self):
        violations = []
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            owner = path.parts[path.parts.index("apps") + 1]
            for module in _imports(path):
                if not module.startswith("src.apps."):
                    continue
                parts = module.split(".")
                target = parts[2] if len(parts) > 2 else owner
                if target != owner and (".api.views." in module or ".views." in module):
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_apps_do_not_cross_import_http_serializers(self):
        violations = []
        for path in _python_files(APPS_ROOT):
            if "tests" in path.parts:
                continue
            owner = path.parts[path.parts.index("apps") + 1]
            for module in _imports(path):
                if not module.startswith("src.apps."):
                    continue
                parts = module.split(".")
                target = parts[2] if len(parts) > 2 else owner
                if target != owner and (
                        ".api.serializers." in module or module.endswith(".serializers")
                ):
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
        self.assertEqual([], violations)

    def test_http_serializers_are_not_declared_in_view_modules(self):
        violations = []
        for path in APPS_ROOT.glob("*/api/views/*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and "Serializer" in node.name:
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno} {node.name}")
        self.assertEqual([], violations)

    def test_legacy_view_and_system_task_directories_do_not_exist(self):
        violations = []
        for path in APPS_ROOT.glob("*/views"):
            if _contains_python_sources(path):
                violations.append(str(path.relative_to(SRC_ROOT)))
        legacy_system_tasks = APPS_ROOT / "system" / "services" / "tasks"
        if _contains_python_sources(legacy_system_tasks):
            violations.append(str(legacy_system_tasks.relative_to(SRC_ROOT)))
        self.assertEqual([], violations)

    def test_app_urlconfs_live_only_under_api_packages(self):
        violations = [
            str(path.relative_to(SRC_ROOT))
            for path in APPS_ROOT.glob("*/urls.py")
        ]
        self.assertEqual([], violations)

    def test_removed_compatibility_modules_do_not_return(self):
        forbidden = [
            APPS_ROOT / "auto_api" / "views.py",
            APPS_ROOT / "auto_api" / "api" / "serializers" / "api_case_detailed_parameter.py",
            APPS_ROOT / "auto_ui" / "api" / "serializers" / "ui_page.py",
            APPS_ROOT / "ai" / "api" / "serializers" / "mcp_server.py",
            APPS_ROOT / "functional_test" / "api" / "views" / "manual.py",
            APPS_ROOT / "ai" / "api" / "views" / "agent_tool_call.py",
            APPS_ROOT / "ai" / "api" / "views" / "agent_task_step.py",
            APPS_ROOT / "ai" / "api" / "views" / "ai.py",
            APPS_ROOT / "ai" / "services" / "mcp_session_manager.py",
            APPS_ROOT / "data_factory" / "serializers.py",
            APPS_ROOT / "system" / "enums" / "tools.py",
            APPS_ROOT / "functional_test" / "enums" / "manual_test.py",
            APPS_ROOT / "auto_api" / "services" / "execution_trace" / "enums.py",
            APPS_ROOT / "auto_ui" / "services" / "live_stream" / "protocol.py",
            APPS_ROOT / "ai" / "agent" / "roles.py",
            APPS_ROOT / "test_center" / "enums" / "execution.py",
            SRC_ROOT / "common" / "enums" / "status.py",
            SRC_ROOT / "common" / "utils" / "project_dir.py",
        ]
        violations = [str(path.relative_to(SRC_ROOT)) for path in forbidden if path.exists()]
        self.assertEqual([], violations)

    def test_removed_legacy_source_namespaces_do_not_return(self):
        forbidden = [
            SRC_ROOT / "services",
            SRC_ROOT / "runtime",
            SRC_ROOT / "interfaces" / "cli",
            SRC_ROOT / "common" / "tools",
            SRC_ROOT / "common" / "mcp",
            SRC_ROOT / "common" / "customization",
        ]
        forbidden.extend(APPS_ROOT.glob("*/service"))
        violations = [
            str(path.relative_to(SRC_ROOT))
            for path in forbidden
            if _contains_python_sources(path)
        ]
        self.assertEqual([], violations)

    def test_prompt_catalog_is_complete_and_valid(self):
        from src.common.prompts import validate_prompt_catalog
        from src.common.prompts.registry import PROMPT_FILES

        prompts = validate_prompt_catalog()
        self.assertEqual(len(PROMPT_FILES), len(prompts))
        self.assertEqual(set(PROMPT_FILES), {prompt.id for prompt in prompts})

    def test_prompt_bodies_do_not_return_to_business_modules(self):
        violations = []
        for path in _python_files(SRC_ROOT):
            if path.is_relative_to(PROMPTS_ROOT) or "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    value = node.value
                    if any(
                            isinstance(target, ast.Name)
                            and (target.id.endswith("_PROMPT") or target.id.endswith("_PROMPTS"))
                            for target in targets
                    ) and isinstance(value, (ast.Constant, ast.Dict, ast.List, ast.Tuple)):
                        violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
                if not isinstance(node, ast.Dict):
                    continue
                literal = {
                    key.value: value
                    for key, value in zip(node.keys, node.values)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                if (
                        isinstance(literal.get("role"), ast.Constant)
                        and literal["role"].value in {"system", "user"}
                        and isinstance(literal.get("content"), ast.Constant)
                        and isinstance(literal["content"].value, str)
                        and len(literal["content"].value.strip()) >= 40
                ):
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{node.lineno}")
        self.assertEqual([], violations)
