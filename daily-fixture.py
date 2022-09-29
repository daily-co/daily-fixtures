import argparse
import json
import os
import re
import requests
from sys import prefix


class FixtureRunner():
    prefixes = {
        'local': 'https://khk-local.wss.daily.co:8080/api/',
        'staging': 'https://staging.daily.co/api/',
        'prod': 'https://api.daily.co/'
    }

    prefix = None
    fixture = None

    environment = None
    fixture_file = None
    output_file = None

    fixture_values = {}

    def __init__(self, environment, fixture_file, output_file):
        self.environment = environment
        self.fixture_file = fixture_file
        self.output_file = output_file
        pass

    def start(self):
        self.prefix = self.prefixes[self.environment]

        f = open(self.fixture_file)
        self.fixture = json.load(f)

    def set_properties(self):
        pass

    def parse_value_string(self, value):
        # TODO: make this recursive with object types
        if type(value) != str:
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
                    print("%s not found in %s" % (field, cur_obj))
                    break

            if isinstance(cur_obj, str) or isinstance(cur_obj, int):
                value = re.sub('\$\{(.*?)\}', str(cur_obj), value, count=1)
            else:
                print("%s does not resolve to a string or integer" % value)

        return value

    def run_fixtures(self, fixtures):
        for fixture in fixtures:
            parsed_fixture = {}
            for (key, value) in fixture.items():
                parsed_fixture[key] = self.parse_value_string(value)

            fixture = parsed_fixture
            headers = {
                'Authorization': 'Bearer %s' % os.environ['DAILY_API_KEY']
            }
            url = self.prefix + 'v1/' + fixture['path']
            if 'query' in fixture:
                url += '?' + fixture['query']

            if fixture['method'] == 'get':
                print("get %s" % url)
                res = requests.get(url, headers=headers)
                print("status: %d" % res.status_code)
                if (res.status_code != 200):
                    print("Error: %s" % res.text)
                    exit(1)
                self.fixture_values[fixture['name']] = res.json()
            elif fixture['method'] == 'post':
                print("post %s" % url)
                res = requests.post(url, headers=headers, json=fixture['data'])
                print("status: %d" % res.status_code)
                print(res.text)
                if (res.status_code != 200):
                    print("Error: %s" % res.text)
                    exit(1)
                self.fixture_values[fixture['name']] = res.json()

    def save_results(self):
        f = open(self.output_file, 'w')
        json.dump(self.fixture_values, f, indent=2)

    def run(self):
        self.start()
        if ('properties' in self.fixture):
            self.set_properties(self.fixture['properties'])

        self.run_fixtures(self.fixture['fixtures'])
        self.save_results()
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Daily fixtures library')
    parser.add_argument('environment', type=str,
                        help='The environment (local, staging or prod)')
    parser.add_argument('file', type=str,
                        help='The fixture file')
    parser.add_argument('output_file', type=str,
                        help='The output file')
    args = parser.parse_args()
    FixtureRunner(args.environment, args.file, args.output_file).run()
