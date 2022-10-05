#!env/bin/python

import argparse
import json
import os
import re
import requests
from sys import stdin, stderr


class FixtureRunner():
    prefixes = {
        'local': 'https://khk-local.wss.daily.co:8080/api/',
        'staging': 'https://staging.daily.co/api/',
        'prod': 'https://api.daily.co/'
    }

    envkeys = {
        'local': 'DAILY_API_KEY',
        'staging': 'DAILY_API_KEY',
        'prod': 'DAILY_API_KEY_PROD'
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
        self.api_key = os.environ[self.envkeys[self.environment]]

        if self.fixture_file:
            f = open(self.fixture_file)
            self.fixture = json.load(f)
        else:
            self.fixture = json.load(stdin)

    def set_properties(self):
        pass

    def parse_value_string(self, value):
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
                    self.log("%s not found in %s" % (field, cur_obj))
                    break

            if isinstance(cur_obj, str) or isinstance(cur_obj, int):
                value = re.sub('\$\{(.*?)\}', str(cur_obj), value, count=1)
            else:
                self.log("%s does not resolve to a string or integer" % value)

        return value

    def check_required_field(self, field, fixture):
        if field not in fixture:
            self.log_error("Field '%s' not in fixture '%s'" %
                           (field, fixture['name']))
            exit(1)

    def check_fixtures(self, fixtures):
        seen_fixtures = set()
        for fixture in fixtures:
            if fixture['name'] in seen_fixtures:
                self.log_error(
                    "Duplicate name in fixture array: %s" % fixture['name'])
                exit(1)

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
            headers = {
                'Authorization': 'Bearer %s' % self.api_key
            }
            url = self.prefix + 'v1/' + fixture['path']
            if 'query' in fixture:
                url += '?' + fixture['query']

            if fixture['method'] == 'get':
                self.log("get %s" % url)
                res = requests.get(url, headers=headers)
                self.add_result(res, fixture)
            elif fixture['method'] == 'post':
                self.log("post %s with data %s" %
                         (url, json.dumps(fixture['data'])))
                res = requests.post(url, headers=headers, json=fixture['data'])
                self.add_result(res, fixture)

    def add_result(self, res, fixture):
        self.log("status: %d" % res.status_code)
        if (res.status_code != 200):
            self.log("Error: %s" % res.text)
            self.output[fixture['name']] = {
                'error': res.status_code,
                'text': res.text
            }
        else:
            self.fixture_values[fixture['name']] = res.json()
            if 'silent' not in fixture or not fixture['silent']:
                self.output[fixture['name']] = res.json()

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
