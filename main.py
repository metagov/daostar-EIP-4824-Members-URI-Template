from flask import Flask, jsonify, request, render_template
import requests
import time
import random
import redis
import os
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize Redis client
redis_url = os.getenv('REDIS_URL', 'localhost')

if redis_url.startswith('redis://'):
    print("redis prod connected")
    r = redis.Redis.from_url(redis_url, db=0, decode_responses=True)
else:
    print("redis local connected")
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    
@app.route('/')
def docs():
    return render_template('docs.html')

def safe_request(url, json_payload, retries=5, initial_delay=3):
    """Make API requests with handling for rate limits using exponential backoff."""
    delay = initial_delay
    for attempt in range(retries):
        response = requests.post(url, json=json_payload)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429 or response.status_code == 503:
            sleep_time = delay + random.uniform(0, delay / 2)
            print(f"Rate limited or service unavailable. Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)
            delay *= 2
        else:
            print(f"Request failed with status code {response.status_code}: {response.text}")
            return None
    raise Exception("Maximum retries exceeded with status code 429 or 503. Consider increasing retry count or delay.")

def fetch_votes_paginated(space, order_direction='asc', initial_created_gt=None):
    """Fetch paginated votes and unique voters from Snapshot Hub GraphQL API, handling pagination only if a cursor is provided."""
    cache_key = f"members-{space}-{order_direction}-{initial_created_gt}"
    cached_data = r.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    url = "https://hub.snapshot.org/graphql"
    unique_voters = set()
    last_cursor = initial_created_gt  # Start from provided cursor, if any

    query = """
    query ($spaceId: String!, $where: VoteWhere!, $orderDirection: OrderDirection!) {
      votes(where: $where, orderDirection: $orderDirection) {
        created
        voter
      }
      space(id: $spaceId) {
        admins
        members
        moderators
      }
    }
    """
    variables = {
        "spaceId": space,
        "where": {"space": space, "created_gt": last_cursor},
        "orderDirection": order_direction,
    }

    if last_cursor:
        variables['where']['created_gt'] = last_cursor  # Pagination based on cursor

    data = safe_request(url, {'query': query, 'variables': variables})
    if data and 'data' in data and 'votes' in data['data']:
        votes = data['data']['votes']
        admins = data['data']['space']['admins']
        members = data['data']['space']['members']
        moderators = data['data']['space']['moderators']

        for vote in votes:
            unique_voters.add(vote['voter'])
        
        if not initial_created_gt == 0:   
            for admin in admins:
                unique_voters.add(admin)
            
            for member in members:
                unique_voters.add(member)
            
            for moderator in moderators:
                unique_voters.add(moderator)

        if votes:
            last_cursor = votes[-1]['created']
            print("Cursor set: " + str(last_cursor))
           

        print("Setting Cache for 10 Hours")
        r.set(cache_key, json.dumps((list(unique_voters), last_cursor)), ex=36000)  # Cache for 10 hours

    return unique_voters, last_cursor

def fetch_onchain_members(onchain_slug):
    """Fetch onchain members from Tally API."""
    api_url = "https://api.tally.xyz/query"
    api_key = str(os.getenv('TALLY_API_KEY'))

    if not api_key:
        raise Exception("TALLY_API_KEY environment variable not set")

    query_org_id = """
    query {
      organizationSlugToId(slug: "%s")
    }
    """ % onchain_slug
    headers = {
        "Api-key": f"{api_key}",
        "Content-Type": "application/json"
    }
    response_org_id = requests.post(api_url, json={"query": query_org_id}, headers=headers)
    if response_org_id.status_code != 200:
        raise Exception(f"Failed to fetch organization ID: {response_org_id.text}")
    
    organization_id = response_org_id.json()['data']['organizationSlugToId']

    query_org_members = """
    query {
      organizationMembers(input: {filters: {organizationId: "%s"}}) {
        nodes {
        ... on Member {
          role
          account {
            address
            type
          }
        }
        }
      }
    }
    """ % organization_id

    response_org_members = requests.post(api_url, json={"query": query_org_members}, headers=headers)
    if response_org_members.status_code != 200:
        raise Exception(f"Failed to fetch organization members: {response_org_members.text}")

    onchain_members = response_org_members.json()['data']['organizationMembers']['nodes']
    return onchain_members

@app.route('/members/<space>', methods=['GET'])
def get_unique_voters(space):
    """Endpoint to fetch unique voters."""
    print("Fetching Members Data...")
    cursor_str = request.args.get('cursor')
    onchain_slug = request.args.get('onchain')

    try:
        cursor = int(cursor_str) if cursor_str is not None else None
    except ValueError:
        return jsonify({"error": "Invalid cursor format. Cursor must be an integer."}), 400

    unique_voters_set, last_cursor = fetch_votes_paginated(space, initial_created_gt=cursor)
    unique_voters_list = [{"id": voter, "type": "EthereumAddress"} for voter in unique_voters_set]

    formatted_members = {
        "offchain": {
            "members": unique_voters_list,
            "next_cursor": last_cursor,
        },
        "@context": "http://daostar.org/schemas",
        "type": "DAO",
        "name": space
    }

    if onchain_slug:
        onchain_members = fetch_onchain_members(onchain_slug)
        formatted_onchain_members = [
            {"id": f"{member['account']['address']}", "role": member['role']} 
            for member in onchain_members
        ]
        formatted_members["onchain"] = {
            "members": formatted_onchain_members
        }

    return jsonify(formatted_members)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
