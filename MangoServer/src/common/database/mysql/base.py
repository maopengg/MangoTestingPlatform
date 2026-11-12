from django.db.backends.mysql.base import DatabaseWrapper as DjangoMySQLWrapper

from src.common.database.mysql.schema import DatabaseSchemaEditor


class DatabaseWrapper(DjangoMySQLWrapper):
    SchemaEditorClass = DatabaseSchemaEditor
