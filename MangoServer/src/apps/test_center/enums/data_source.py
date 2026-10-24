from src.common.enums.base import BaseEnum


class DataSourceCategoryEnum(BaseEnum):
    """数据库能力分类。不同分类使用不同的执行适配器。"""
    DATABASE = 0
    CACHE = 1
    SEARCH = 2

    @classmethod
    def obj(cls):
        return {
            0: "关系型数据库",
            1: "缓存/键值存储",
            2: "搜索引擎",
        }


class DataSourceTypeEnum(BaseEnum):
    """具体数据库类型。保留历史数据库类型数值，避免破坏已有数据。"""
    MYSQL = 0
    POSTGRESQL = 1
    SQLITE = 2
    ORACLE = 3
    SQLSERVER = 4
    REDIS = 10
    ELASTICSEARCH = 20

    @classmethod
    def obj(cls):
        return {
            0: "MySQL",
            1: "PostgreSQL",
            2: "SQLite",
            3: "Oracle",
            4: "SQL Server",
            10: "Redis",
            20: "Elasticsearch",
        }

    @classmethod
    def category(cls, value: int) -> int | None:
        if value in {cls.MYSQL.value, cls.POSTGRESQL.value, cls.SQLITE.value, cls.ORACLE.value, cls.SQLSERVER.value}:
            return DataSourceCategoryEnum.DATABASE.value
        if value == cls.REDIS.value:
            return DataSourceCategoryEnum.CACHE.value
        if value == cls.ELASTICSEARCH.value:
            return DataSourceCategoryEnum.SEARCH.value
        return None
