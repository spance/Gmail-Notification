#!/usr/bin/python
# coding=utf-8

import argparse
import inspect

import services
from helper import *
from config import AppConfig


__author__ = 'spance'
__version__ = '0.6.1'
__description__ = '''
    Gmail Notification.
    --------------------------------
    At first, You should be adjust the configuration in file "gnoti.conf".
    Use "-a/--add" option to add account and continue with the guide.
    You can get more help from "README".
'''

initLog('logs/gnoti.log')


def __list():
    accounts = services.CredentialManager.listAccounts()
    print('List All accounts:')
    if accounts:
        for account in accounts:
            print account
    else:
        print '<None>'


def __add_gmail(args):
    mail = args.add_gmail[0]
    if not reMail.match(mail):
        mail = tryInput('Please enter a Gmail address that you want to take notifications :', re=reMail)
    services.CredentialSetup(mail).interact()


def __remove_gmail(args):
    mail = args.remove_gmail[0]
    if not reMail.match(mail):
        mail = tryInput('Please enter a Gmail address that you want to take notifications :', re=reMail)
    services.CredentialManager.removeAccount(mail)


def __scheduled_task():
    services.CheckMailTask().run()


if __name__ == '__main__':
    argsParser = argparse.ArgumentParser(version=__version__,
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=__description__)
    argsGroup = argsParser.add_mutually_exclusive_group()
    argsGroup.add_argument('-a', '--add', dest='add_gmail', default=None, nargs=1,
                           help='setup account and authorization to take notification')
    argsGroup.add_argument('-l', '--list', action='store_true', default=None,
                           help='show the authorized accounts list')
    argsGroup.add_argument('-r', '--remove', dest='remove_gmail', default=None, nargs=1,
                           help='remove the authorized account')
    argsGroup.add_argument('--scheduled-task', action='store_true', default=None, help=argparse.SUPPRESS)

    args = argsParser.parse_args()

    if AppConfig.init_and_validate():
        this = globals()
        for k, v in dict(args.__dict__).iteritems():
            fun = this['__%s' % k]
            if v and fun and inspect.isfunction(fun):
                if fun.func_code.co_argcount:
                    fun(args)
                else:
                    fun()
                args = None
    else:
        sys.exit(-1)
    if args:
        print('Please use "--help" option to read help.')
