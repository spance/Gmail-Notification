import sqlite3
import helper

__author__ = 'spance'


class Query(object):
    def __init__(self, db):
        self.log = helper.getLogger(__name__)
        self.conn = sqlite3.connect(db)
        self.opened = True
        self.log.debug('DB connected successfully.')

    def __del__(self):
        self.close()

    def close(self):
        try:
            if self.opened:
                self.conn.commit()
                self.conn.close()
                self.opened = False
                self.log.debug('DB closed.')
        except BaseException as e:
            self.log.error('Error in close db : %s' % e)

    def query(self, sql, *args):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, args)
            return cursor.fetchall()
        except:
            self.conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def update_auto(self, sql, *args):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, args)
            return cursor.rowcount
        except:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()
        finally:
            if cursor:
                cursor.close()

    def update_batch(self, sql, args):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.executemany(sql, args)
            return cursor.rowcount
        except:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()
        finally:
            if cursor:
                cursor.close()


class AppQuery(Query):
    def __init__(self):
        super(AppQuery, self).__init__('db/gnoti.db')