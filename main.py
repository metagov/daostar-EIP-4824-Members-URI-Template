from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/fetch_dao_data', methods=['GET'])
def fetch_dao_data():
    # API endpoint
    url = "https://hub.snapshot.org/graphql"

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
        "first": 200
    }

    # Making the POST request
    response = requests.post(url, json={'query': query, 'variables': variables})

    # Check if the request was successful
    if response.status_code == 200:
        # Parsing the response
        data = response.json()
        followers = data['data']['follows']

        # Preparing the formatted JSON with follower IDs and additional information
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
