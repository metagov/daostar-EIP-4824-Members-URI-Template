from flask import Flask, jsonify, request, render_template
import requests
import time
import random
import redis
import os
import json
from flask_cors import CORS
import asyncio
import aiohttp

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

async def safe_request(url, json_payload, retries=5, initial_delay=3):
    """Make API requests with handling for rate limits using exponential backoff."""
    delay = initial_delay
    async with aiohttp.ClientSession() as session:
        for attempt in range(retries):
            async with session.post(url, json=json_payload) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status in (429, 503):
                    sleep_time = delay + random.uniform(0, delay / 2)
                    print(f"Rate limited or service unavailable. Retrying in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                    delay *= 2
                else:
                    print(f"Request failed with status code {response.status}: {await response.text()}")
                    return None
    raise Exception("Maximum retries exceeded with status code 429 or 503. Consider increasing retry count or delay.")

async def fetch_votes_paginated(space, order_direction='asc', initial_created_gt=None, refresh=False):
    """Fetch paginated votes and unique voters from Snapshot Hub GraphQL API, handling pagination only if a cursor is provided."""
    cache_key = f"members-{space}-{order_direction}-{initial_created_gt}"
    if not refresh:
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

    data = await safe_request(url, {'query': query, 'variables': variables})
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

        print("Setting Cache for offchain members")
        r.set(cache_key, json.dumps((list(unique_voters), last_cursor)))  

    return unique_voters, last_cursor

async def fetch_onchain_members(onchain_slug, cursor=None, refresh=False):
    """Fetch onchain members and delegates from Tally API, with pagination."""
    cache_key = f"onchain-members-{onchain_slug}-{cursor}"
    if not refresh:
        cached_data = r.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

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
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json={"query": query_org_id}, headers=headers) as response_org_id:
            if response_org_id.status != 200:
                raise Exception(f"Failed to fetch organization ID: {await response_org_id.text()}")
            organization_id = (await response_org_id.json())['data']['organizationSlugToId']

            if cursor:
                # Query only delegates when cursor is present
                query_org_members = """
                query Delegates($input: DelegatesInput!) {
                    delegates(input: $input) {
                        pageInfo {
                            lastCursor
                        }
                        nodes {
                            ... on Delegate {
                                account {
                                    address
                                }
                                organization {
                                    chainIds
                                }
                            }
                        }
                    }
                }
                """
                variables = {
                    "input": {
                        "filters": {
                            "organizationId": organization_id
                        },
                        "page": {
                            "afterCursor": cursor
                        }
                    }
                }
            else:
                # Query both delegates and organization members when cursor is absent
                query_org_members = """
                query Delegates($input: DelegatesInput!, $organizationMembersInput2: OrganizationMembersInput!) {
                    delegates(input: $input) {
                        pageInfo {
                            lastCursor
                        }
                        nodes {
                            ... on Delegate {
                                account {
                                    address
                                }
                                organization {
                                    chainIds
                                }
                            }
                        }
                    }
                    organizationMembers(input: $organizationMembersInput2) {
                        nodes {
                            ... on Member {
                                account {
                                    address
                                }
                                organization {
                                    chainIds
                                }
                                role
                            }
                        }
                    }
                }
                """
                variables = {
                    "input": {
                        "filters": {
                            "organizationId": organization_id
                        }
                    },
                    "organizationMembersInput2": {
                        "filters": {
                            "organizationId": organization_id
                        }
                    }
                }

        async with session.post(api_url, json={"query": query_org_members, "variables": variables}, headers=headers) as response_org_members:
            if response_org_members.status != 200:
                raise Exception(f"Failed to fetch organization members: {await response_org_members.text()}")

            data = await response_org_members.json()
            delegates = data['data']['delegates']['nodes']
            last_cursor = data['data']['delegates']['pageInfo']['lastCursor']

            # Only include organization members if they were queried
            onchain_members = []
            if not cursor and 'organizationMembers' in data['data']:
                onchain_members = data['data']['organizationMembers']['nodes']

            print("Setting Cache for onchain members")
            r.set(cache_key, json.dumps((onchain_members, delegates, last_cursor)))  

    return onchain_members, delegates, last_cursor



@app.route('/members/<space>', methods=['GET'])
async def get_unique_voters(space):
    """Endpoint to fetch unique voters."""
    print("Fetching Members Data...")
    offchain_cursor_str = request.args.get('offchain_cursor')
    onchain_cursor_str = request.args.get('onchain_cursor')
    onchain_slug = request.args.get('onchain')
    refresh = request.args.get('refresh') == 'true'

    try:
        offchain_cursor = int(offchain_cursor_str) if offchain_cursor_str is not None else None
    except ValueError:
        return jsonify({"error": "Invalid offchain cursor format. Cursor must be an integer."}), 400

    try:
        onchain_cursor = int(onchain_cursor_str) if onchain_cursor_str is not None else None
    except ValueError:
        return jsonify({"error": "Invalid onchain cursor format. Cursor must be an integer."}), 400

    unique_voters_set, offchain_last_cursor = await fetch_votes_paginated(space, initial_created_gt=offchain_cursor, refresh=refresh)
    unique_voters_list = [{"id": voter, "type": "EthereumAddress"} for voter in unique_voters_set]

    formatted_members = {
        "@context": "http://daostar.org/schemas",
        "type": "DAO",
        "name": space,
        "members" : {
        "offchain": {
            "members": unique_voters_list,
            "offchain_cursor_str": offchain_last_cursor,
        }, },
        
    }

    if onchain_slug:
        onchain_members, delegates, onchain_last_cursor = await fetch_onchain_members(onchain_slug, cursor=onchain_cursor, refresh=refresh)
        formatted_onchain_members = [
            {"id": f"{member['account']['address']}", "role": member['role'], "type": "EthereumAddress"} 
            for member in onchain_members
        ]
        formatted_delegates = [
            {"id": f"{delegate['account']['address']}", "role": "delegate",  "type": "EthereumAddress"} 
            for delegate in delegates
        ]

        formatted_members["onchain"] = {
            "members": formatted_onchain_members + formatted_delegates,
            "onchain_cursor_str": onchain_last_cursor
        }

    return jsonify({"Members": formatted_members})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
