# daily-fixtures
Parse JSON files to make REST API calls to daily.co

## Usage

usage: daily-fixture.py [-h] [-v VERBOSE] [-f FILE] [-o OUTPUT_FILE] environment

Daily fixtures library

positional arguments:
  environment           The environment (local, staging or prod)

options:
  -h, --help            show this help message and exit
  -v VERBOSE, --verbose VERBOSE
                        Verbose mode
  -f FILE, --file FILE  The fixture file. If not specified will read from STDIN
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        The output file. If not specified will write to STDOUT


## Description

daily-fixtures is a utility to easily make Daily REST API calls. It allows using the results of api calls in subsequent calls.

For instance, you can create a fixture to get the most recent 5 meetings like so:

```
{
    "fixtures": [
        {
                "name": "all-meetings",
                "path": "meetings",
                "method": "get",
                "silent": true
        },
        {
                "name": "after",
                "path": "meetings",
                "query": "timeframe_start=${all-meetings.data[4].start_time}",
                "method": "get"
        }
    ]
}
```

(obviously you can do the same with a limit in one request, but this is for illustration purposes)
