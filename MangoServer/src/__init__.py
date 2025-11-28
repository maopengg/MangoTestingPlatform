import pymysql

from tools import ProjectDir

project_dir = ProjectDir()

pymysql.install_as_MySQLdb()
