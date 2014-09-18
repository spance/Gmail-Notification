import ConfigParser
import copy
import json
import os
import urllib2

import helper


__author__ = 'spance'

log = helper.getLogger(__name__)

__configuration__ = None


def getConfiguration():
    """ get current configuration copy.

    :return: may be None if never call the "init_and_validate" at before.
    """
    return copy.deepcopy(__configuration__) if __configuration__ else None


class AppConfig(object):
    def __init__(self):
        self.sys = None
        self.methods = []


    @staticmethod
    def init_and_validate():
        """ init gnoti.conf to configuration object, and validate it.
        all exception will be logged.

        :return: if validate pass is True else is None
        """
        cp = ConfigParser.ConfigParser()
        try:
            cp.read('gnoti.conf')
        except:
            log.exception('Unable to read file gnoti.conf')
            return None
        _config = AppConfig()
        try:
            # may be throw KeyError if not found
            sysDefinition = SysDefinition(cp.get('sys', 'methods'),
                                          cp.get('sys', 'client_credential'),
                                          cp.get('sys', 'oauth_redirect_uri'))
            state = sysDefinition.validate()
            if not isinstance(state, bool) or not state:  # string or boolean
                raise RuntimeError(state)
            _config.sys = sysDefinition

            methods_literal = sysDefinition.methods
            for method in methods_literal.split():
                map = {'name': method}
                section = method + '_api'
                keys_section = cp.options(section)
                map['api'] = cp.get(section, 'url')
                map['method'] = cp.get(section, 'method')
                map['headers'] = cp.get(section, 'headers') if 'headers' in keys_section else None
                map['data'] = cp.get(section, 'data') if 'data' in keys_section else None
                map['basic_auth'] = cp.get(section, 'basic_auth') if 'basic_auth' in keys_section else None
                _config.methods.append(MethodDefinition(map))

            for method in _config.methods:
                msg = method.validate()
                if not isinstance(msg, bool):
                    raise RuntimeError(msg)
        except:
            log.exception('Error in gnoti.conf')
        else:
            global __configuration__
            __configuration__ = _config
            return True


def checkAppClientSecret(file):
    if not os.path.isfile(file):
        return 'Not found app_client_secret.json'
    else:
        try:
            with open(file, 'r') as f:
                json.loads(f.read())
            return True
        except:
            return 'Invalid app_client_secret file.'


def lines2map(data):
    _map = {}
    if data:
        for line in data.split('\n'):
            line = line.strip()
            if line:
                k, sp, v = line.partition('=')
                _map[k.strip()] = v.strip()
    return _map if _map else None


class SysDefinition(object):
    def __init__(self, methods, client_credential, oauth_redirect_uri):
        self.methods = methods
        self.client_credential = client_credential
        self.oauth_redirect_uri = oauth_redirect_uri

    def validate(self):
        if not self.methods:
            return 'sys.method is required'
        if not self.client_credential:
            return 'sys.client_credential is required'
        state = checkAppClientSecret(self.client_credential)
        if not isinstance(state, bool) or not state:  # string or boolean
            return state
        if not self.oauth_redirect_uri:
            return 'sys.oauth_redirect_uri is required.'
        return True


class MethodDefinition(object):
    def __init__(self, map):
        self.map = map
        self.__data = None
        self.__api_headers = None
        self.__basic_auth = None

    def validate(self):
        if not self.api or not helper.reUrl.match(self.api):
            return '%s.url is error.' % self.name
        if not self.method or not self.method.upper() in ["GET", "POST"]:
            return '%s.method should be one of ["GET","POST"]' % self.name
        _data = str(self.data)
        for var in ['msg', 'to']:
            if not _data or not '{%s}' % var in _data:
                return 'Not found "{%s}" symbols' % var
        return True

    @property
    def api(self):
        return self.map['api']

    @property
    def method(self):
        return self.map['method'].upper()

    @property
    def name(self):
        return self.map['name']

    @property
    def headers(self):
        if self.__api_headers:
            return self.__api_headers
        self.__api_headers = lines2map(self.map['headers'])
        return self.__api_headers

    @property
    def data(self):
        if self.__data:
            return self.__data
        self.__data = lines2map(self.map['data'])
        return self.__data

    @property
    def basic_auth(self):
        if self.__basic_auth:
            return self.__basic_auth
        basic_auth = self.map['basic_auth']
        if not basic_auth:
            return None
        user, passwd = basic_auth.split(':')
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.api, user, passwd)
        self.__basic_auth = urllib2.HTTPBasicAuthHandler(password_mgr)
        return self.__basic_auth
