#!env/bin/python

import argparse
import json
import os
import re
import requests
from sys import stdin, stderr


class FixtureRunner():
    prefixes = {
        'local': 'https://khk-local.wss.daily.co:8080/',
        'staging': 'https://staging.daily.co/',
        'blue': 'https://qa-ks.pluot.blue/',
        'prod': 'https://api.daily.co/'
    }

    prefixes_raw = {
        'local': 'https://khk-local.wss.daily.co:8080/',
        'staging': 'https://staging.daily.co/',
        'blue': 'https://qa-ks.pluot.blue/',
        'prod': 'https://daily.co/'
    }

    api_paths = {
        'local': 'api/v1/',
        'staging': 'api/v1/',
        'blue': 'api/v1/',
        'prod': 'v1/'
    }

    envkeys = {
        'local': 'DAILY_API_KEY',
        'staging': 'DAILY_API_KEY',
        'blue': 'DAILY_API_KEY',
        'prod': 'DAILY_API_KEY_PROD'
    }

    envkeys_alt = {
        'local': 'DAILY_API_KEY_ALT',
        'staging': 'DAILY_API_KEY_ALT',
        'blue': 'DAILY_API_KEY_ALT',
        'prod': 'DAILY_API_KEY_PROD_ALT'
    }

    prefix = None
    fixture = None

    environment = None
    fixture_file = None
    output_file = None

    fixture_values = {}
    output = {}

    def __init__(self, environment, fixture_file, output_file, verbose):
        self.environment = environment
        self.fixture_file = fixture_file
        self.output_file = output_file
        self.verbose = verbose
        pass

    def start(self):
        self.prefix = self.prefixes[self.environment]
        self.prefix_raw = self.prefixes_raw[self.environment]
        self.api_path = self.api_paths[self.environment]
        self.api_key = os.environ[self.envkeys[self.environment]]
        self.api_key_alt = os.environ[self.envkeys_alt[self.environment]]

        if self.fixture_file:
            f = open(self.fixture_file)
            self.fixture = json.load(f)
        else:
            self.fixture = json.load(stdin)

    def set_properties(self):
        pass

    def parse_value_string(self, value):
        try:
            if type(value) == dict:
                new_dict = {}
                for key in value:
                    new_dict[key] = self.parse_value_string(value[key])
                return new_dict
            elif type(value) != str:
                return value

            matches = re.findall('\$\{(.*?)\}', value)
            for match in matches:
                fields = match.split(".")
                cur_obj = self.fixture_values
                for field in fields:
                    array = re.match('(.*)\[([0-9]+)\]', field)
                    if array:
                        cur_obj = cur_obj[array[1]][int(array[2])]
                    elif field in cur_obj:
                        cur_obj = cur_obj[field]
                    else:
                        self.log("%s not found in %s" %
                                 (field, json.dumps(cur_obj)[:20]))
                        break

                if isinstance(cur_obj, str) or isinstance(cur_obj, int):
                    value = re.sub('\$\{(.*?)\}', str(cur_obj), value, count=1)
                else:
                    self.log("%s does not resolve to a string or integer" % value)

            return value
        except Exception as e:
            print("An error occurred while parsing %s: %s" % (value, e))
            return value

    def check_required_field(self, field, fixture):
        if field not in fixture:
            self.log_error("Field '%s' not in fixture '%s'" %
                           (field, fixture['name']))
            exit(1)

    def check_fixtures(self, fixtures):
        seen_fixtures = set()
        for fixture in fixtures:
            print(fixture)
            if fixture['name'] in seen_fixtures:
                self.log_error(
                    "Duplicate name in fixture array: %s" % fixture['name'])
                exit(1)

            if 'assertion_eq' not in fixture:
                self.check_required_field('method', fixture)
                self.check_required_field('path', fixture)

                if fixture['method'] == 'post':
                    self.check_required_field('data', fixture)

            seen_fixtures.add(fixture['name'])

    def run_fixtures(self, fixtures):
        for fixture in fixtures:
            parsed_fixture = {}
            for (key, value) in fixture.items():
                parsed_fixture[key] = self.parse_value_string(value)

            fixture = parsed_fixture

            use_alt_token = 'alt' in fixture and fixture['alt']
            if use_alt_token:
                self.log('Using alt key for request %s' % fixture['name'])

            if 'assertion_eq' in fixture:
                self.log("Checking assertion: %s" % fixture['name'])
                items = [self.parse_value_string(i)
                         for i in fixture['assertion_eq']]
                if len(items) != 2:
                    self.log_error('2 items expected for assertion_eq: %s' %
                                   fixture['assertion_eq'])
                    exit(1)

                if items[0] != items[1]:
                    self.log_error('Failed assertion: %s not equal' % items)
                    exit(1)

                self.log("Passed: %s" % items)
                continue

            if 'raw' in fixture and fixture['raw']:
                url = self.prefix_raw + fixture['path']
            else:
                url = self.prefix + self.api_path + fixture['path']

            if 'token_type' in fixture:
                if fixture['token_type'] == 'login':
                    self.log('Using login token for request %s' %
                             fixture['name'])
                    if use_alt_token:
                        bearer_token = self.login_token_alt
                    else:
                        bearer_token = self.login_token
                elif fixture['token_type'] == 'none':
                    self.log('Using no token for request %s' % fixture['name'])
                    bearer_token = None
            elif 'override_token' in fixture:
                bearer_token = fixture['override_token']
            else:
                if use_alt_token:
                    bearer_token = self.api_key
                else:
                    bearer_token = self.api_key_alt

            if bearer_token:
                headers = {
                    'Authorization': 'Bearer %s' % bearer_token
                }
            else:
                headers = {}

            if 'query' in fixture:
                url += '?' + fixture['query']
            fixture['method'] = fixture['method'].lower()
            if fixture['method'] == 'get':
                self.log("get %s" % url)
                res = requests.get(url, headers=headers)
                self.add_result(res, fixture)
            elif fixture['method'] == 'post':
                self.log("post %s with data %s" %
                         (url, json.dumps(fixture['data'])))
                res = requests.post(url, headers=headers, json=fixture['data'])
                self.add_result(res, fixture)
            elif fixture['method'] == 'delete':
                self.log("delete %s" % url)
                res = requests.delete(url, headers=headers)
                self.add_result(res, fixture)
            else:
                self.log_error("Unknown method %s in fixture %s" %
                               (fixture['method'], fixture['name']))
                exit(1)


    def add_result(self, res, fixture):
        self.log("status: %d" % res.status_code)
        if (res.status_code != 200):
            self.log("Error: %s" % res.text)
            self.output[fixture['name']] = {
                'error': res.status_code,
                'text': res.text
            }
        else:
            try:
                self.fixture_values[fixture['name']] = res.json()
                if 'silent' not in fixture or not fixture['silent']:
                    self.output[fixture['name']] = res.json()
            except requests.exceptions.JSONDecodeError as err:
                self.fixture_values[fixture['name']] = {
                    'error': f"Unexpected {err=}, {type(err)=}"}

    def save_results(self):
        self.log("Saving results %s" % self.output_file)

        if self.output_file:
            f = open(self.output_file, 'w')
            json.dump(self.output, f, indent=2)
        else:
            print(json.dumps(self.output, indent=2))

    def log(self, s):
        if self.verbose:
            print(s)

    def log_error(self, e):
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        stderr.write("%sERROR: %s %s" % (FAIL, e, ENDC))

    def run(self):
        self.start()
        if ('properties' in self.fixture):
            self.set_properties(self.fixture['properties'])

        self.check_fixtures(self.fixture['fixtures'])
        self.run_fixtures(self.fixture['fixtures'])
        self.save_results()
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Daily fixtures library')
    parser.add_argument('environment', type=str,
                        help='The environment (local, staging or prod)')
    parser.add_argument('-v', '--verbose', type=bool,
                        help='Verbose mode', default=False)
    parser.add_argument('-f', '--file', type=str,
                        help='The fixture file. If not specified will read from STDIN')
    parser.add_argument('-o', '--output_file', type=str, default='',
                        help='The output file. If not specified will write to STDOUT')
    args = parser.parse_args()
    FixtureRunner(args.environment, args.file,
                  args.output_file, args.verbose).run()
