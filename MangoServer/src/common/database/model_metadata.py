"""Normalize database-facing model metadata for schema migrations."""

from django.apps import apps


def apply_database_comments() -> None:
    """Use Django labels as native table and column comments.

    Django exposes ``verbose_name`` to application code and ``db_comment`` to
    the database. Keeping them aligned here gives every managed business table
    useful comments without duplicating the same Chinese label on every field.
    Explicit ``db_comment`` and ``db_table_comment`` values always win.
    """

    for model in apps.get_models():
        if not model.__module__.startswith("src.apps."):
            continue

        options = model._meta
        if not options.managed or options.proxy:
            continue

        if not options.db_table_comment:
            table_comment = str(options.verbose_name)
            options.db_table_comment = table_comment
            # ModelState reads Meta options from original_attrs.
            options.original_attrs["db_table_comment"] = table_comment

        for field in options.local_fields:
            if field.concrete and not field.db_comment:
                field.db_comment = str(field.verbose_name)
