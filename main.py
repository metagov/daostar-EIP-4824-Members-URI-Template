from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/', methods=['GET'])
def api_documentation():
    documentation = """
    <h1>Lodestar Finance Members URI</h1>
    <h1>API Documentation</h1>

    <h2>Endpoint: /members</h2>
    <p><strong>Description:</strong> This endpoint fetches unique voter data from the Snapshot Hub GraphQL API, paginated by the <code>created</code> field of votes.</p>

    <p><strong>HTTP Method:</strong> GET</p>

    <p><strong>URL Structure:</strong> /members</p>

    <p><strong>Query Parameters:</strong> None. This endpoint does not require any query parameters. It fetches all unique voters for the <code>lodestarfinance.eth</code> space, paginated based on the <code>created</code> parameter of the last vote in each fetched batch.</p>

    <p><strong>Response Format:</strong> The response is in JSON format. It contains a list of unique voters fetched from the Snapshot Hub GraphQL API, formatted according to the DAO URI specification.</p>

    <p><strong>Example Request:</strong> GET /members</p>
    <p>This request will fetch data for all unique voters associated with the <code>lodestarfinance.eth</code> space, sorted in ascending order by their vote creation time.</p>

    <p><strong>Example Response:</strong></p>
    <pre>{
    "members": [
        {
            "id": "0x09cC15Dda77789d42c0133c909E88Fb6E3Af793A",
            "type": "EthereumAddress"
        },
        {
            "id": "0xBdda09f18494226a27477b7cFc9Ed2a3F8076168",
            "type": "EthereumAddress"
        },
        // ... more unique voters ...
    ],
    "@context": {
        "@vocab": "http://daostar.org/"
    },
    "type": "DAO",
    "name": "lodestarfinance.eth"
}</pre>

    <p><strong>Notes:</strong></p>
    <ul>
        <li>This endpoint fetches data through paginated requests to the Snapshot Hub GraphQL API, ensuring that all unique voters are retrieved without missing any due to pagination limits.</li>
        <li>The data is presented in a format that includes the voter's Ethereum address, the type of address, and contextual information according to the DAO URI specification.</li>
        <li>As this process involves multiple requests to the Snapshot Hub API, response times may vary based on the total number of votes.</li>
    </ul>
    """
    return documentation

def fetch_votes_paginated(space, order_direction='asc', initial_created_gt=None):
    url = "https://hub.snapshot.org/graphql"
    unique_voters = set()
    created_gt = initial_created_gt

    while True:
        query = """
        query Votes($where: VoteWhere, $orderDirection: OrderDirection) {
          votes(where: $where, orderDirection: $orderDirection) {
            created
            voter
          }
        }
        """
        variables = {
            "where": {"space": space, "created_gt": created_gt} if created_gt else {"space": space},
            "orderDirection": order_direction
        }

        response = requests.post(url, json={'query': query, 'variables': variables})
        if response.status_code == 200:
            data = response.json()['data']['votes']
            if not data:
                break  

            created_gt = data[-1]['created']  

            for vote in data:
                unique_voters.add(vote['voter'])
        else:
            raise Exception(f"Failed to fetch data, status code: {response.status_code}")

    return unique_voters

@app.route('/members', methods=['GET'])
def get_unique_voters():
    space = 'lodestarfinance.eth'  
    unique_voters_set = fetch_votes_paginated(space=space, order_direction='asc')
    unique_voters_list = [{"id": voter, "type": "EthereumAddress"} for voter in unique_voters_set]

    formatted_members = {
        "members": unique_voters_list,
        "@context": {"@vocab": "http://daostar.org/"},
        "type": "DAO",
        "name": space,
    }

    return jsonify(formatted_members) 

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
