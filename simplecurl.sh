curl -v --location --request POST 'https://khk-local.wss.daily.co:8080/users/signup' \
--header 'Content-Type: application/json' \
--data-raw '{
    "invite_token": {"like": "D4i%"},
    "password": "wahooweeehawweewaw",
    "email": "moishe+h1_6@daily.co"
}'
