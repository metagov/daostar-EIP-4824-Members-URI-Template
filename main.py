from flask import Flask, jsonify, request  # Import 'request' from flask
import requests

app = Flask(__name__)

@app.route('/', methods=['GET'])
def fetch_dao_data():
    # API endpoint
    url = "https://hub.snapshot.org/graphql"

    # Get 'first' parameter from query string, default to 200 if not provided
    first_param = request.args.get('first', default=200, type=int)

    # GraphQL query
    query = """
    query ($followsWhere2: FollowWhere, $first: Int!) {
      follows(where: $followsWhere2, first: $first) {
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
    app.run(debug=True)
