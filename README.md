# Lodestar Finance Members URI
## API Documentation
### Endpoint: /members
**Description:** This endpoint fetches unique voter data from the Snapshot Hub GraphQL API, paginated by the created field of votes.

**HTTP Method:** GET

**URL Structure:** /members

**Query Parameters:** None. This endpoint does not require any query parameters. It fetches all unique voters for the lodestarfinance.eth space, paginated based on the created parameter of the last vote in each fetched batch.

**Response Format:** The response is in JSON format. It contains a list of unique voters fetched from the Snapshot Hub GraphQL API, formatted according to the DAO URI specification.

**Example Request:** GET /members

This request will fetch data for all unique voters associated with the lodestarfinance.eth space, sorted in ascending order by their vote creation time.

**Example Response:**

{
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
}


##### Notes:

This endpoint fetches data through paginated requests to the Snapshot Hub GraphQL API, ensuring that all unique voters are retrieved without missing any due to pagination limits.
The data is presented in a format that includes the voter's Ethereum address, the type of address, and contextual information according to the DAO URI specification.
As this process involves multiple requests to the Snapshot Hub API, response times may vary based on the total number of votes.


## Build Instructions

###### pip install -r requirements.txt

###### python3 main.py
