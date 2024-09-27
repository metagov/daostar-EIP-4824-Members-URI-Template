# EIP-4824 Members URI API Documentation

---

## 1. Root Endpoint

**Endpoint:** `/`  
**Method:** `GET`  
**Description:** Renders the documentation page.

---

## 2. Get Unique Voters

**Endpoint:** `/members/<space>`  
**Method:** `GET`  
**Description:** Fetches unique voters for a given space. Optionally fetches on-chain members and delegates if `onchain` parameter is provided.

### Parameters:

- **`space` (path parameter):**
  - **Type:** `string`
  - **Description:** The space ID from which to fetch the unique voters.

- **`offchain_cursor` (query parameter, optional):**
  - **Type:** `integer`
  - **Description:** Cursor for paginating off-chain votes.

- **`onchain_cursor` (query parameter, optional):**
  - **Type:** `integer`
  - **Description:** Cursor for paginating on-chain members and delegates.

- **`onchain` (query parameter, optional):**
  - **Type:** `string`
  - **Description:** The slug of the on-chain organization to fetch members and delegates from.

- **`refresh` (query parameter, optional):**
  - **Type:** `boolean`
  - **Description:** If set to `true`, forces a refresh of the cached data.

### Response:

- **200 OK**
  - **Content-Type:** `application/json`
  - **Description:** Returns the list of unique voters, and optionally on-chain members and delegates, with pagination cursors.

  ```json
  {
    "Members": {
      "@context": "http://daostar.org/schemas",
      "type": "DAO",
      "name": "Example DAO",
      "members": {
        "offchain": {
          "members": [
            {"id": "0x123...", "type": "EthereumAddress"},
            {"id": "0x456...", "type": "EthereumAddress"}
          ],
          "offchain_cursor_str": 123456789
        },
        "onchain": {
          "members": [
            {"id": "0xabc...", "role": "member", "type": "EthereumAddress"},
            {"id": "0xdef...", "role": "delegate", "type": "EthereumAddress"}
          ],
          "onchain_cursor_str": 987654321
        }
      }
    }
  }
