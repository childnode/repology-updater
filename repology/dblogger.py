# Copyright (C) 2016-2018 Dmitry Marakasov <amdmi3@amdmi3.ru>
#
# This file is part of repology
#
# repology is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# repology is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with repology.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import traceback

from repology.logger import Logger


def _severity_to_sql(severity):
    if severity == Logger.NOTICE:
        return 'notice'
    elif severity == Logger.WARNING:
        return 'warning'
    elif severity == Logger.ERROR:
        return 'error'
    else:
        raise RuntimeError('Unknown severity ' + str(severity))


class RealtimeDatabaseLogger(Logger):
    def __init__(self, db, run_id):
        self.db = db
        self.run_id = run_id
        self.lineno = 1

    def log(self, message, severity=Logger.NOTICE):
        self.db.add_log_line(
            self.run_id,
            self.lineno,
            None,
            _severity_to_sql(severity),
            message
        )
        self.lineno += 1


class PostponedDatabaseLogger(Logger):
    def __init__(self):
        self.lines = []

    def log(self, message, severity=Logger.NOTICE):
        self.lines.append((
            datetime.datetime.now(),
            severity,
            message
        ))

    def flush(self, db, run_id):
        for lineno, (timestamp, severity, message) in enumerate(self.lines, 1):
            self.db.add_log_line(
                run_id,
                lineno,
                timestamp,
                _severity_to_sql(severity),
                message
            )


class LogRunManager:
    def __init__(self, env, reponame, run_type):
        self.env = env
        self.reponame = reponame
        self.run_type = run_type

    def __enter__(self):
        database = self.env.get_logging_database_connection()

        self.run_id = database.start_run(self.reponame, self.run_type)
        self.logger = RealtimeDatabaseLogger(database, self.run_id)

        database.update_repository_run_id(self.reponame, self.run_id, 'current')

        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        database = self.env.get_logging_database_connection()
        success = not exc_tb

        if exc_tb:
            self.logger.log('run failed, exception follows:', severity=Logger.ERROR)

            for item in traceback.format_exception(exc_type, exc_val, exc_tb):
                for line in item.split('\n'):
                    if line:
                        self.logger.log(line, severity=Logger.ERROR)

        database.finish_run(self.run_id, success)
        database.update_repository_run_id(self.reponame, None, 'current')
        database.update_repository_run_id(self.reponame, self.run_id, self.run_type, success)
