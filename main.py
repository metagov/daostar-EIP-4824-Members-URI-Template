from flask import Flask, jsonify
import requests
import time

app = Flask(__name__)

def safe_request(url, json_payload, retries=5, initial_delay=3):
    """Make API requests with handling for rate limits using exponential backoff."""
    delay = initial_delay
    for attempt in range(retries):
        response = requests.post(url, json=json_payload)
        if response.status_code == 200:
            return response.json()  # Return JSON data directly
        elif response.status_code == 429:
            print(f"Rate limited. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Increase delay exponentially
        else:
            print(f"Request failed with status code {response.status_code}: {response.text}")
            break  # Break the loop if failure is not due to rate limiting
    else:  # This else corresponds to the for, not the if
        raise Exception("Maximum retries exceeded with status code 429. Consider increasing retry count or delay.")

def fetch_votes_paginated(space, order_direction='asc', initial_created_gt=None):
    """Fetch paginated votes and unique voters from Snapshot Hub GraphQL API."""
    url = "https://hub.snapshot.org/graphql"
    unique_voters = set()
    created_gt = initial_created_gt

    query = """
    query Votes($where: VoteWhere, $first: Int!) {
      votes(where: $where, first: $first) {
        created
        voter
      }
    }
    """
    variables = {
        "where": {"space": space, "created_gt": created_gt} if created_gt else {"space": space},
        "first": 100  # Adjust the pagination limit as required
    }

    data = safe_request(url, {'query': query, 'variables': variables})
    votes = data['data']['votes']

    # Process all votes
    while votes:
        for vote in votes:
            unique_voters.add(vote['voter'])

        # Prepare for pagination
        created_gt = votes[-1]['created']
        variables['where']['created_gt'] = created_gt
        data = safe_request(url, {'query': query, 'variables': variables})
        votes = data['data']['votes']

    return unique_voters

@app.route('/', methods=['GET'])
def api_documentation():
    """API documentation endpoint."""
    return """
    <h1>API Documentation</h1>
    <h2>Endpoint: /members</h2>
    <p><strong>Description:</strong> Fetches unique voter data from the Snapshot Hub API.</p>
    <p><strong>HTTP Method:</strong> GET</p>
    <p><strong>URL Structure:</strong> /members</p>
    <p><strong>Response Format:</strong> JSON</p>
    <p><strong>Example Request:</strong> GET /members</p>
    """

@app.route('/members', methods=['GET'])
def get_unique_voters():
    """Endpoint to fetch unique voters."""
    space = 'beets.eth'
    unique_voters_set = fetch_votes_paginated(space)
    unique_voters_list = [{"id": voter, "type": "EthereumAddress"} for voter in unique_voters_set]

    formatted_members = {
        "members": unique_voters_list,
        "@context": "http://daostar.org/schemas",
        "type": "DAO",
        "name": space
    }

    return jsonify(formatted_members)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
