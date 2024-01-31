from flask import Flask, jsonify, request  # Import 'request' from flask
import requests

app = Flask(__name__)

@app.route('/', methods=['GET'])
def api_documentation():
    documentation = """
    <h1>Welcome to the Lodestar Finance Members API</h1>
    <h1>API Documentation</h1>

    <h2>Endpoint: /members</h2>
    <p><strong>Description:</strong> This endpoint fetches member data from the Snapshot Hub GraphQL API.</p>

    <p><strong>HTTP Method:</strong> GET</p>

    <p><strong>URL Structure:</strong> /members?first=[number]</p>

    <p><strong>Query Parameters:</strong></p>
    <ul>
        <li><code>first</code> (optional): An integer specifying the number of members to fetch. If not provided, defaults to 200.</li>
    </ul>

    <p><strong>Response Format:</strong> The response is in JSON format. It contains member data fetched from the Snapshot Hub GraphQL API. The data includes the IDs of the members and other related information.</p>

    <p><strong>Example Request:</strong> GET /members?first=100</p>
    <p>This request will fetch data for the first 100 members.</p>

    <p><strong>Example Response:</strong></p>
    <pre>{
    "members": [
        {
            "id": "0x123...",
            "type": "EthereumAddress"
        },
        // ... more members ...
    ],
    "@context": {
        "@vocab": "http://daostar.org/"
    },
    "type": "DAO",
    "name": "YourDAOName"
}</pre>

    <p><strong>Notes:</strong></p>
    <ul>
        <li>This endpoint is used to interact with the Snapshot Hub GraphQL API.</li>
        <li>The <code>first</code> query parameter allows for basic control over the number of members returned.</li>
        <li>The response structure and content might vary based on the data available from the Snapshot Hub API.</li>
    </ul>
    """
    return documentation

@app.route('/members', methods=['GET'])
def fetch_dao_data():
    # API endpoint
    url = "https://hub.snapshot.org/graphql"

    # Get 'first' parameter from query string, default to 200 if not provided
    first_param = request.args.get('first', default=200, type=int)

    # GraphQL query
    query = """
    query ($followsWhere2: FollowWhere, $first: Int!) {
      votes(where: $followsWhere2, first: $first) {
        id
      }
    }
    """

    # Variables for the query
    variables = {
        "followsWhere2": {
            "space": "lodestarfinance.eth"
        },
        "first": first_param  # Use the parameter from the query string
    }

    # Making the POST request
    response = requests.post(url, json={'query': query, 'variables': variables})

    if response.status_code == 200:
        # Parsing the response
        data = response.json()
        followers = data['data']['follows']

        # Preparing the formatted JSON according to DAO URI
        formatted_followers = {
            "members": [{"id": follower["id"], "type": "EthereumAddress"} for follower in followers],
            "@context": {"@vocab": "http://daostar.org/"},
            "type": "DAO",
            "name": "lodestarfinance.eth"
        }

        return jsonify(formatted_followers)
    else:
        return jsonify({"error": "Failed to fetch data"}), response.status_code

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
