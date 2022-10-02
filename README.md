# daily-fixtures
Parse JSON files to make REST API calls to daily.co

Sample command line:
`python daily-fixture.py staging test.json output.json`

You can use values from previous calls by indexing them with the name of the previous call, eg.
`"query": "room=${room-list.data[0].name}"`
where `room-list` is the name of a previous call.
