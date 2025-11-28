import pymysql

from src.tools import ProjectDir

ProjectDir()

pymysql.install_as_MySQLdb()
