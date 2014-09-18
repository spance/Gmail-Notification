import json
import urllib
import urllib2

from oauth2client.client import Credentials
from crontab import CronTab

import config
from googleapis import *
from helper import *
from query import AppQuery


__author__ = 'spance'

log = getLogger(__name__)


class CredentialSetup:
    def __init__(self, mail):
        if not mail:
            raise Exception('mail is required.')
        self.mail = mail
        self.state = 'authorization'
        self.authorization_code = None

    def __acquireAuthorizationCode(self):
        self.authorization_code = tryInput('Please enter authorization_code: ')
        if self.authorization_code:
            return True

    def __acquireCredentials(self):
        try:
            id_and_credential = get_credentials(self.authorization_code, self.state)
            self.userId = id_and_credential[0]
            self.credential = id_and_credential[1]
            return True
        except BaseException as e:
            if isinstance(e, GetCredentialsException):
                raise AvailedException('Please check on the authorization_code and rerun this program.')
            else:
                log.exception('__acquireCredentials')
                raise e

    def __acquireTelephone(self):
        reTel = re.compile('^\+?\d+$')
        self.tel = tryInput('Please enter a telephone(eg. 123000 or +123000) :', re=reTel)
        if reTel.match(self.tel):
            return True

    def __saveCredential(self):
        credential_json = self.credential.to_json()
        CredentialManager.persistAccount(self.mail, self.tel, self.userId, credential_json)

    def interact(self):
        try:
            print 'Please copy the url into browser and give approval, then you can got the authorization code.'
            print '-' * 60
            print get_authorization_url(self.mail, self.state)
            print '-' * 60
            if not self.__acquireAuthorizationCode():
                return False
            if not self.__acquireCredentials():
                return False
            if not self.__acquireTelephone():
                return False
            self.__saveCredential()
            CronTask().create()
        except BaseException as e:
            if isinstance(e, AvailedException):
                print(e.message)
            else:
                log.exception('setup')


class CredentialManager:
    @staticmethod
    def listAccounts():
        """ query all accounts from database. within close connection.

        :return: resultSet tuple
        """
        sql = 'SELECT mail,create_time FROM authorization'
        query = AppQuery()
        results = []
        try:
            for row in query.query(sql):
                results.append('%-36s %s' % (row[0], row[1]))
        finally:
            query.close()
        return results

    @staticmethod
    def removeAccount(mail):
        """ remove account/credential from db. within close connection.

        :param mail:
        :return: affected count
        """
        sql = 'DELETE FROM authorization WHERE mail=?'
        query = AppQuery()
        try:
            affected = query.update_auto(sql, mail)
            sql = 'SELECT count(*) FROM authorization'
            count = query.query(sql)[0][0]
            if count == 0:
                CronTask().remove()
            return affected
        finally:
            query.close()

    @staticmethod
    def listCredentials():
        """ query all credentials from database. within close connection.

        :return: resultSet array
        """
        sql = 'SELECT mail,tel,credential FROM authorization'
        query = AppQuery()
        try:
            return query.query(sql)
        finally:
            query.close()

    @staticmethod
    def persistAccount(mail, tel, id, credential):
        """ save an account/credential to database. within close connection.

        :param mail:
        :param tel:
        :param id:
        :param credential: credential should be a string.
        """
        sql = 'INSERT INTO authorization (mail, user_id, tel, credential, create_time)' \
              ' VALUES (?, ?, ?, ?, ?)'
        query = AppQuery()
        try:
            query.update_auto(sql, mail, id, tel, credential, datetime.datetime.now())
        finally:
            query.close()

    @staticmethod
    def updateCredential(mail, credential):
        """ update credential of special account. within close connection.

        :param mail:
        :param credential: credential should be a string.
        """
        sql = "UPDATE authorization SET credential=?, refresh_time=datetime('now') WHERE mail=?"
        query = AppQuery()
        try:
            query.update_auto(sql, credential, mail)
        finally:
            query.close()

    @staticmethod
    def analyseAndPersistMessages(mail, messages):
        """ save messages from api to database.last_msg. within close connection.
        And take unread messages that not noticed over N-times during T-hours
        1. delete messages if old records after T-hours(expired).
        2. delete messages if old records not in this messages list(already read).
        3. insert this messages with current time(local timezone). So all records is current unread messages.
        4. total count of the records from sub query if records count <= N in a group by msg_id.

        :param mail:
        :param messages:
        :return:
        """
        args = []
        _N, _T = 2, 6
        for msg in messages:
            args.append((mail, '%s+%s' % (msg['id'], msg['threadId'])))
        query = AppQuery()
        try:
            sql = "DELETE FROM last_msg WHERE mail=? AND julianday(log_time)<julianday('now')-?"
            cleared = query.update_auto(sql, mail, _T / 24.0)
            log.debug('clear repeated expiry logs count=%d' % cleared)
            if args:
                sql = "delete from last_msg where mail=? and msg_id not in ('%s')" % "','".join(i[1] for i in args)
                cleared = query.update_auto(sql, mail)
                log.debug('clear read count=%d' % cleared)
                sql = "INSERT INTO last_msg (mail, msg_id, log_time) VALUES (?,?, datetime('now'))"
                inserted = query.update_batch(sql, args)
                log.debug('insert unread count=%d' % inserted)
                sql = 'SELECT count(*) FROM (' \
                      '  SELECT msg_id FROM last_msg ' \
                      '  WHERE mail=? ' \
                      '  GROUP BY msg_id ' \
                      '  HAVING count(*) <= ?' \
                      ' )'
                lastUnread = query.query(sql, mail, _N)[0][0]
                log.debug('lastUnread count=%d' % lastUnread)
                return lastUnread
            else:
                sql = "DELETE FROM last_msg WHERE mail=?"
                cleared = query.update_auto(sql, mail)
                log.debug('clear read COUNT=%d' % cleared)
                return 0
        finally:
            query.close()

    @staticmethod
    def prepareCredential(mail, credential_json):
        """  build credential object from json, and check expiry or refresh it.
        may be throw exceptions while dealing with google-apis.
        :param mail:
        :param credential_json:
        :return: credential obj
        """
        credential = Credentials.new_from_json(credential_json)
        if credential.access_token_expired:
            credential.refresh(httplib2.Http())
            CredentialManager.updateCredential(mail, credential.to_json())
            log.info('Credential refreshed and saved.')
        return credential


class CronTask:
    def __init__(self, interval=5):
        self.cron = '*/%d * * * *' % interval
        self.cmd_file = 'gnoti.py'
        self.cmd_args = '--scheduled-task'
        self.cmd = 'python %s/%s %s &' % (appPath(), self.cmd_file, self.cmd_args)

    def create(self):
        cron = CronTab(user=True)
        jobs = cron.find_command(self.cmd_args)
        changed, jobExisted = 0, False
        if jobs:
            for job in jobs:
                if not job.is_enabled() or not job.is_valid():
                    log.info('remove the invalid cron task[%s]' % job)
                    changed += cron.remove(job)
                else:
                    jobExisted = True
        if not jobExisted:
            job = cron.new(self.cmd)
            job.setall(self.cron)
            changed += 1
            log.info('create a new cron task[%s]' % job)
        if changed > 0:
            try:
                cron.write()
            except:
                log.exception('An Error when writing cron configuration')
        else:
            log.info('the cron task is already exists. No changes.')


    def remove(self):
        cron = CronTab(user=True)
        jobs = cron.find_command(self.cmd_args)
        changed = 0
        for job in jobs:
            changed += cron.remove(job)
            log.info('remove task[%s]' % job)
        if changed > 0:
            try:
                cron.write()
            except:
                log.exception('An Error when writing cron configuration')
        else:
            log.info('the cron task is already exists. No changes.')


def maskedAccount(account):
    """ to ensure account privacy, make account to a masked text.

    :param account:
    :return:
    """
    suffix = None
    if '@' in account:
        name, _, suffix = account.partition('@')
    else:
        name = account
    _len = len(name)
    if _len <= 3:
        return account
    plen = 2 if _len > 3 else 1
    name = '%s%s%s' % (name[:plen], '*' * (_len - 2 * plen), name[_len - plen:])
    return '%s@%s' % (name, suffix) if suffix else name


class CheckMailTask(object):
    def __sendNotifications(self, mail, tel, count):
        url, api_code, api_result = None, None, None
        conf = config.getConfiguration()
        assert conf is not None
        for method in conf.methods:
            try:
                template = {
                    'msg': 'Your account %s have %d unread messages.' % (maskedAccount(mail), count),
                    'to': tel
                }
                url, data = method.api, {}

                # apply variables( {msg} {to} ) to http parameters.
                if method.data:
                    for (k, v) in method.data.items():
                        k = k.format(**template) if '{' in k else k
                        v = v.format(**template) if '{' in v else v
                        data[k] = v
                    data = urllib.urlencode(data)
                    if method.method == 'GET':  # else POST : retain data.
                        # todo parse url, append to query_part
                        url = '%s?%s' % (url, data)  # GET : append parameters to url and remove data.
                        data = None

                # apply basic auth
                if method.basic_auth:
                    urllib2.install_opener(urllib2.build_opener(method.basic_auth))

                # headers=None is not allowed.
                headers = method.headers if method.headers else {}

                req = urllib2.Request(url, data=data, headers=headers)
                log.info('Call %s_api HTTP/%s ==> %s' % (method.name, method.method, url))
                if data:
                    log.debug('Post-data = %s', json.dumps(data))
                if headers:
                    log.debug('Header = %s', json.dumps(headers))
                # if 1 == 1: return
                httpCall = urllib2.urlopen(req, timeout=5)
                api_code = httpCall.getcode()
                api_result = httpCall.read()
                log.info('Responded %s_api ==> [Code=%d] %s' % (method.name, api_code, api_result))
            except:
                log.exception('Error call %s_api [Code=%d] %s' % (method.name, api_code, api_result))

    def __check(self, info):
        mail, tel, credential = info  # tuple
        log.info('Working for account[%s]' % mail)
        if not tel:
            log.error('Unable send notifications to the account [%s] without tel.' % mail)
            return
        credential = CredentialManager.prepareCredential(mail, credential)
        unreadMails = findUnreadMails(mail, credential)
        log.info('Found unread&inbox COUNT=%d' % len(unreadMails))
        lastUnread = CredentialManager.analyseAndPersistMessages(mail, unreadMails)
        log.info('Checked account[%s] last-unread&inbox COUNT=%d' % (mail, lastUnread))
        if lastUnread > 0:
            # todo should be consider sending on an available time frame
            self.__sendNotifications(mail, tel, lastUnread)

    def run(self):
        try:
            allList = CredentialManager.listCredentials()
            log.info('Checking Task is running. ACCOUNTS-TOTAL = %d', len(allList))
            for info in allList:
                self.__check(info)
            log.info('Task is complete.')
        except:
            log.exception('Error when running the task!')
