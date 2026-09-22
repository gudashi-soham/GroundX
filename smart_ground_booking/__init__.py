import pymysql
from django.db.backends.base.base import BaseDatabaseWrapper

# Enable PyMySQL as MySQLdb driver
pymysql.install_as_MySQLdb()

# Allow MySQL 5.7+ compatibility
BaseDatabaseWrapper.check_database_version_supported = lambda self: None
