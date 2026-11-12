"""用生产模型的字段和约束构建隔离表，验证 MySQL 兼容的唯一性语义。"""

from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from django.db import IntegrityError, connections, models
from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteWrapper
from django.db.migrations.state import ModelState, StateApps

from src.apps.auto_api.models import ApiCaseRelease, ApiInfoRelease
from src.apps.functional_test.models import FunctionalTestDefectCase
from src.apps.perf.models import PerfBaseline
from src.apps.perf.services.reporting.baseline import PerfBaselineService
from src.common.database.mysql.base import DatabaseWrapper as MySQLWrapper


class MySQLUniqueConstraintTests(unittest.TestCase):
    alias = "mysql_unique_constraints_test"

    def setUp(self):
        config = {
            "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "OPTIONS": {},
            "TIME_ZONE": None, "CONN_MAX_AGE": 0, "CONN_HEALTH_CHECKS": False,
            "AUTOCOMMIT": True, "ATOMIC_REQUESTS": False,
        }
        self.db = SQLiteWrapper(config, alias=self.alias)
        connections[self.alias] = self.db
        self.addCleanup(self._close)

    def _close(self):
        self.db.close()
        del connections[self.alias]

    @staticmethod
    def _constraint_model(source, flag=None):
        names = {name for constraint in source._meta.constraints for name in getattr(constraint, "fields", ())}
        if flag:
            names.add(flag)
        else:
            names.update(("defect", "case", "plan_case"))
        fields = [("id", models.AutoField(primary_key=True))]
        for name in sorted(names):
            original = source._meta.get_field(name)
            field = (
                models.BigIntegerField(null=original.null, blank=original.blank, db_column=original.column)
                if original.is_relation else original.clone()
            )
            fields.append((name, field))
        state = ModelState(
            source._meta.app_label, source.__name__, fields,
            options={"db_table": source._meta.db_table, "constraints": deepcopy(source._meta.constraints)},
        )
        return state.render(StateApps([], {}))

    def _create(self, source, flag=None):
        model = self._constraint_model(source, flag)
        with self.db.schema_editor() as editor:
            editor.create_model(model)
        return model.objects.using(self.alias)

    def test_case_release_current_is_unique_and_history_is_unlimited(self):
        self._check_releases(ApiCaseRelease, "api_case")

    def test_info_release_current_is_unique_and_history_is_unlimited(self):
        self._check_releases(ApiInfoRelease, "api_info")

    def _check_releases(self, source, owner):
        rows = self._create(source, "is_current")
        current = rows.create(**{owner: 1}, version_no=1, is_current=True)
        for number in (2, 3):
            rows.create(**{owner: 1}, version_no=number, is_current=False)
        with self.assertRaises(IntegrityError):
            rows.create(**{owner: 1}, version_no=4, is_current=True)
        with self.assertRaises(IntegrityError):
            rows.filter(version_no=2).update(is_current=True)
        with self.assertRaises(IntegrityError):
            rows.bulk_create([rows.model(**{owner: 1}, version_no=5, is_current=True)])
        rows.filter(pk=current.pk).update(is_current=False)
        rows.filter(version_no=2).update(is_current=True)
        self.assertEqual(rows.filter(is_current=True).count(), 1)
        self.assertEqual(rows.filter(is_current=False).count(), 2)
        rows.create(**{owner: 2}, version_no=1, is_current=True)
        self.assertEqual(rows.get(**{owner: 1}, version_no=2).current_unique_marker, 1)
        self.assertIsNone(rows.get(pk=current.pk).current_unique_marker)

    def test_baseline_unique_scope_switch_and_bulk_insert(self):
        rows = self._create(PerfBaseline, "active")
        scope = {"scenario": 1, "environment_key": "test", "engine": "k6"}
        current = rows.create(**scope, active=True)
        rows.create(**scope, active=False)
        rows.create(**scope, active=False)
        with self.assertRaises(IntegrityError):
            rows.bulk_create([rows.model(**scope, active=True)])
        with self.assertRaises(IntegrityError):
            rows.filter(active=False).update(active=True)
        rows.filter(pk=current.pk).update(active=False)
        rows.create(**scope, active=True)
        for dimension, value in (("scenario", 2), ("environment_key", "dev"), ("engine", "other")):
            rows.create(**{**scope, dimension: value}, active=True)
        self.assertEqual(rows.filter(**scope, active=True).count(), 1)
        self.assertEqual(rows.filter(**scope, active=False).count(), 3)

    def test_defect_targets_unique_and_nullable_alternative_allowed(self):
        rows = self._create(FunctionalTestDefectCase)
        rows.create(defect=1, case=10)
        rows.create(defect=1, case=11)
        rows.create(defect=1, plan_case=20)
        rows.create(defect=1, plan_case=21)
        rows.create(defect=2, case=10)
        for target in ({"case": 10}, {"plan_case": 20}, {}, {"case": 12, "plan_case": 22}):
            with self.subTest(target=target), self.assertRaises(IntegrityError):
                rows.create(defect=1, **target)
        self.assertEqual(rows.count(), 5)

    def test_mysql_generates_real_unique_indexes_without_where(self):
        config = dict(self.db.settings_dict, ENGINE="src.common.database.mysql", NAME="unused")
        db = MySQLWrapper(config, alias="mysql_sql_preview")
        db.mysql_server_data = {
            "version": "8.0.36", "sql_mode": "STRICT_TRANS_TABLES", "default_storage_engine": "InnoDB",
            "sql_auto_is_null": False, "lower_case_table_names": False, "has_zoneinfo_database": True,
        }
        with patch.object(db, "ensure_connection", side_effect=AssertionError("禁止连接环境数据库")):
            for source, flag in ((ApiCaseRelease, "is_current"), (ApiInfoRelease, "is_current"),
                                 (PerfBaseline, "active"), (FunctionalTestDefectCase, None)):
                model = self._constraint_model(source, flag)
                editor = db.schema_editor(collect_sql=True, atomic=False)
                editor.deferred_sql = []
                # MySQL 的字面量转义默认要求连接；这里只离线编译固定整数和注释。
                def quote_literal(value):
                    if value is None:
                        return "NULL"
                    if isinstance(value, (int, bool)):
                        return str(int(value))
                    return "'" + str(value).replace("'", "''") + "'"
                with patch.object(editor, "quote_value", side_effect=quote_literal):
                    sql, _ = editor.table_sql(model)
                sql += "\n" + "\n".join(str(item) for item in editor.deferred_sql)
                self.assertIn("UNIQUE", sql)
                self.assertNotIn(" WHERE ", sql)
                for constraint in model._meta.constraints:
                    if isinstance(constraint, models.UniqueConstraint):
                        self.assertIn(constraint.name, sql)
                self.assertTrue(all(c.condition is None for c in model._meta.constraints
                                    if isinstance(c, models.UniqueConstraint)))
                if flag:
                    self.assertIn("GENERATED ALWAYS AS", sql)
                    self.assertIn("STORED", sql)
                    marker = "current_unique_marker" if flag == "is_current" else "active_unique_marker"
                    with patch.object(editor, "quote_value", side_effect=quote_literal):
                        definition, _ = editor.column_sql(model, model._meta.get_field(marker), include_default=True)
                        editor.collected_sql = []
                        editor.add_field(model, model._meta.get_field(marker))
                    self.assertLess(definition.index("GENERATED ALWAYS AS"), definition.index("COMMENT"))
                    self.assertLess(definition.index("STORED"), definition.index("COMMENT"))
                    add_sql = editor.collected_sql[0]
                    self.assertIn("ADD COLUMN", add_sql)
                    self.assertLess(add_sql.index("STORED"), add_sql.index("COMMENT"))
                    self.assertTrue(model._meta.get_field(marker).db_comment)
                warnings = model._check_constraints(databases=[self.alias])
                self.assertFalse([w for w in warnings if w.id == "models.W036"])

    def test_baseline_switch_locks_parent_inside_atomic_transaction(self):
        path = "src.apps.perf.services.reporting.baseline"
        run = SimpleNamespace(scenario_id=1, test_env=5, engine="k6", name="run", snapshot_hash="hash")
        with patch(f"{path}.transaction.get_connection", return_value=self.db), \
                patch(f"{path}.PerfScenario") as scenarios, patch(f"{path}.PerfBaseline") as baselines:
            scenario = scenarios.objects.select_for_update.return_value.filter.return_value.first.return_value
            def assert_atomic(**kwargs):
                self.assertTrue(self.db.in_atomic_block)
                return SimpleNamespace(id=1)
            baselines.objects.create.side_effect = assert_atomic
            PerfBaselineService.set_baseline(run, name="baseline", created_by=None)
            self.assertFalse(self.db.in_atomic_block)
            scenarios.objects.select_for_update.assert_called_once_with()
            baselines.objects.filter.assert_called_once_with(
                scenario_id=scenario.pk, environment_key="5", engine="k6", active=True,
            )
            baselines.objects.filter.return_value.update.assert_called_once_with(active=False)
            baselines.objects.create.assert_called_once()

    def test_baseline_create_failure_rolls_back_previous_deactivation(self):
        rows = self._create(PerfBaseline, "active")
        old = rows.create(scenario=1, environment_key="5", engine="k6", active=True)
        run = SimpleNamespace(scenario_id=1, test_env=5, engine="k6", name="run", snapshot_hash="hash")
        path = "src.apps.perf.services.reporting.baseline"
        with patch(f"{path}.transaction.get_connection", return_value=self.db), \
                patch(f"{path}.PerfScenario") as scenarios, patch(f"{path}.PerfBaseline") as baselines:
            scenarios.objects.select_for_update.return_value.filter.return_value.first.return_value = SimpleNamespace(pk=1)
            baselines.objects.filter.return_value.update.side_effect = lambda **kw: rows.filter(pk=old.pk).update(**kw)
            baselines.objects.create.side_effect = IntegrityError("simulated insert failure")
            with self.assertRaises(IntegrityError):
                PerfBaselineService.set_baseline(run)
        self.assertTrue(rows.get(pk=old.pk).active)
