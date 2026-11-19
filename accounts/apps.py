import sys

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.db.backends.signals import connection_created

        def setup_sqlite(sender, connection, **kwargs):
            if connection.vendor != 'sqlite':
                return
            cursor = connection.cursor()
            cursor.execute('PRAGMA busy_timeout=8000;')
            if 'test' in sys.argv:
                return
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')

        connection_created.connect(setup_sqlite, dispatch_uid='instova_sqlite_pragmas')
