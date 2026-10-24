from django.db import migrations

OWNER_TABLE = "project_product_owners"
PROJECT_PRODUCT_TABLE = "project_product"
TEST_OBJECT_TABLE = "test_object"
USER_TABLE = "user"


def ensure_project_product_owners(apps, schema_editor):
    """Create and backfill the owner relation for databases upgraded in place.

    ``test_center`` took ownership of historical ``auto_system`` tables without
    recreating them. Its state-only baseline therefore leaves database work for
    newly introduced relations to an explicit repair migration.
    """
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    # The historical base tables must exist before this relation can be added.
    if PROJECT_PRODUCT_TABLE not in existing_tables or USER_TABLE not in existing_tables:
        return

    ProjectProduct = apps.get_model("test_center", "ProjectProduct")
    through_model = ProjectProduct._meta.get_field("owners").remote_field.through
    owner_table_exists = OWNER_TABLE in existing_tables
    if owner_table_exists:
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, OWNER_TABLE)
        has_relation_constraint = any(
            constraint["unique"]
            and constraint["columns"] == ["projectproduct_id", "user_id"]
            for constraint in constraints.values()
        )
        # A failed MySQL CREATE TABLE can leave the table committed before
        # Django runs its deferred indexes and unique constraint. Such a table
        # only contains rows produced by this idempotent backfill, so rebuild it
        # and let create_model finish the complete schema on the retry.
        if not has_relation_constraint and set(constraints) == {"PRIMARY"}:
            schema_editor.delete_model(through_model)
            owner_table_exists = False
        elif not has_relation_constraint:
            raise RuntimeError(
                f"{OWNER_TABLE} exists without its expected relation constraint; "
                "refusing to replace an unknown schema"
            )

    if not owner_table_exists:
        schema_editor.create_model(through_model)

    if TEST_OBJECT_TABLE not in existing_tables:
        return

    TestObject = apps.get_model("test_center", "TestObject")
    database = connection.alias
    legacy_relations = (
        TestObject.objects.using(database)
        .exclude(project_product_id__isnull=True)
        .exclude(executor_name_id__isnull=True)
        .order_by()
        .values_list("project_product_id", "executor_name_id")
        .distinct()
    )
    through_model.objects.using(database).bulk_create(
        [
            through_model(projectproduct_id=project_product_id, user_id=user_id)
            for project_product_id, user_id in legacy_relations
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    # MySQL cannot execute CREATE TABLE inside Django's migration transaction
    # because its DDL isn't rollback-safe. The operation is idempotent, so an
    # interrupted run can be resumed safely.
    atomic = False

    dependencies = [
        ("auto_system", "0049_delete_executortask_delete_filedata_and_more"),
    ]

    operations = [
        migrations.RunPython(
            ensure_project_product_owners,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
