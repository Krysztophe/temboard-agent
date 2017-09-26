from __future__ import unicode_literals
import os
from sys import stdout, stderr
from getpass import getpass
import re
import urllib2
import json

from .cli import cli
from .options import agentRegisterOptions
from .errors import (
    ConfigurationError,
    HTTPError,
)
from .types import T_PASSWORD, T_USERNAME
from .tools import validate_parameters
from .httpsclient import https_request
from .configuration import LazyConfiguration


def ask_password():
    try:
        raw_pass = os.environ['TEMBOARD_UI_PASSWORD']
    except KeyError:
        raw_pass = getpass(" Password: ")

    try:
        password = raw_pass
        validate_parameters({'password': password},
                            [('password', T_PASSWORD, False)])
    except HTTPError:
        stdout.write("Invalid password.\n")
        return ask_password()
    return password


def ask_username():
    try:
        raw_username = os.environ['TEMBOARD_UI_USER']
    except KeyError:
        raw_username = raw_input(" Username: ")

    try:
        username = raw_username
        validate_parameters({'username': username},
                            [('username', T_USERNAME, False)])
    except HTTPError:
        stdout.write("Invalid username.\n")
        return ask_username()
    return username


@cli
def main(argv, environ):
    optparser = agentRegisterOptions(
                    usage="usage: %prog [options] <https-temboard-ui-address>",
                    add_help_option=False,
                    description="Register a couple PostgreSQL instance/agent "
                                "to a Temboard UI.")
    (options, args) = optparser.parse_args()

    if options.help is True:
        print(optparser.format_help().strip())
        exit(0)
    if len(args) != 1:
        print("ERROR: One argument is required.\n")
        print(optparser.format_help().strip())
        exit(1)

    # Loading agent configuration file.
    config = LazyConfiguration(options.configfile)

    ui_address = args[0]
    # Load configuration from the configuration file.
    try:
        # Getting system/instance informations using agent's discovering API
        print("Getting system & PostgreSQL informations from the agent "
              "(https://%s:%s/discover) .." % (options.host, options.port))
        (code, content, cookies) = https_request(
                None,
                'GET',
                "https://%s:%s/discover" % (options.host, options.port),
                headers={
                    "Content-type": "application/json"
                })
        infos = json.loads(content)
        for k, v in infos.iteritems():
            print(" %s: %s" % (k, v))

        # Authentication done by the UI
        print("")
        print("Login at %s." % (ui_address))
        username = ask_username()
        password = ask_password()
        (code, content, cookies) = https_request(
                None,
                'POST',
                "%s/json/login" % (ui_address),
                headers={
                    "Content-type": "application/json"
                },
                data={'username': username, 'password': password})
        temboard_cookie = None
        for cookie in cookies.split("\n"):
            cookie_content = cookie.split(";")[0]
            if re.match(r'^temboard=.*$', cookie_content):
                temboard_cookie = cookie_content
                continue

        if options.groups:
            groups = [g for g in options.groups.split(',')]
        else:
            groups = None

        # POSTing new instance
        print("")
        print("Registering instance/agent to %s .." % (ui_address))
        (code, content, cookies) = https_request(
                None,
                'POST',
                "%s/json/register/instance" % (ui_address),
                headers={
                    "Content-type": "application/json",
                    "Cookie": temboard_cookie
                },
                data={
                    'hostname': infos['hostname'],
                    'agent_key': config.temboard['key'],
                    'agent_address': options.host,
                    'agent_port': config.temboard['port'],
                    'cpu': infos['cpu'],
                    'memory_size': infos['memory_size'],
                    'pg_port': infos['pg_port'],
                    'pg_data': infos['pg_data'],
                    'pg_version': infos['pg_version'],
                    'plugins': infos['plugins'],
                    'groups': groups
                })
        if code != 200:
            raise HTTPError(code, content)
        print("Done.")
    except (ConfigurationError, HTTPError, Exception) as e:
        if isinstance(e, urllib2.HTTPError):
            err = json.loads(e.read())
            stderr.write("FATAL: %s\n" % err['error'])
        else:
            stderr.write("FATAL: %s\n" % str(e))
        return 1

    return 0


if __name__ == '__main__':  # pragma: no cover
    main()