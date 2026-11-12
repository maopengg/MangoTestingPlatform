from copy import copy

from django.db.backends.mysql.schema import DatabaseSchemaEditor as DjangoMySQLSchemaEditor


class DatabaseSchemaEditor(DjangoMySQLSchemaEditor):
    def _iter_column_sql(self, column_db_type, params, model, field, field_db_params, include_default):
        if not (field.generated and field.db_comment and self.connection.features.supports_comments_inline):
            yield from super()._iter_column_sql(
                column_db_type, params, model, field, field_db_params, include_default,
            )
            return

        # MySQL 生成列要求 AS (...) STORED/VIRTUAL 在 COMMENT 前。
        # 只复制字段实例，不更改 Model 或 Migration State 中的注释和表达式。
        column_field = copy(field)
        column_field.db_comment = None
        yield from super()._iter_column_sql(
            column_db_type, params, model, column_field, field_db_params, include_default,
        )
        yield self._comment_sql(field.db_comment)
