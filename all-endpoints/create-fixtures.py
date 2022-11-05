import json
import re
import sys

fixtures = {
    'fixtures': [
        {
            'name': 'xdomain',
            'path': '/',
            'method': 'get',
            'silent': True
        },
        {
            'name': 'xrooms',
            'path': '/rooms',
            'method': 'get',
            'silent': True
        },
        {
            'name': 'xmeetings',
            'path': '/meetings',
            'method': 'get'
        }
    ]
}

ignore_paths = ['boxes', '_ks_']

variables = {
    ':domain': '${xdomain.domain_id}',
    ':roomId': '${xrooms[0].id}',
    ':room': '${xrooms[0].id}',
    #':meetingId': '${xmeetings[0].id}'
}

for line in sys.stdin:
    line = line.rstrip()

    if any(ignore_path in line for ignore_path in ignore_paths):
        print("Ignoring %s" % line, file=sys.stderr)
        continue

    line = line[1:]
    fixture_name = line.replace('/', '-')

    inserts = re.findall(':[a-zA-Z]+', line)
    replaced_all = True
    if inserts:
        for insert in inserts:
            if insert in variables:
                line = line.replace(insert, variables[insert])
            else:
                replaced_all = False

    if not replaced_all:
        print("Unable to replace %s" % line, file=sys.stderr)
        continue

    fixture = {
        'name': fixture_name,
        'path': line,
        'method': 'get',
        'raw': True
    }

    fixtures['fixtures'].append(fixture)

print(json.dumps(fixtures, indent=2))
