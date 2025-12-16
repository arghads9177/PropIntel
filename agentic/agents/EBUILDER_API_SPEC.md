# eBuilder API Specification

## Base Configuration
- **Base URL**: `https://ebuilder.myaastha.in/ebuilderlbapi/api/`
- **Auth Token**: `Bearer QXN0OEA6M21zMXBw` (in `Authorization` header)
- **Organization Code**: `aastha` (required in all POST payloads as `ocode`)

---

## Endpoints

### 1. `/project/search` (POST)
**Purpose**: Fetch project metadata (branch, status, timelines, towers, docs)

**Request Payload**:
```json
{
  "ocode": "aastha",
  "shortname": "optional project shortname",
  "branch": "optional branch filter (ASANSOL, BANDEL)",
  "status": "optional status (Running, Complete, Hold)"
}
```

**Response**: Array of project objects
```json
[
  {
    "_id": "...",
    "shortname": "WATERFORD GATE",
    "fullname": "watergate",
    "branch": "ASANSOL",
    "cname": "Incite India Construction Pvt Ltd",
    "status": "Running",
    "towers": 1,
    "commencedate": "2025-10-25T11:01:19.277Z",
    "approxcompletedate": "2025-12-25T11:01:19.277Z",
    "ocode": "aastha"
  }
]
```

**Key Fields**:
- `shortname`: Unique project code
- `fullname`: Display name
- `branch`: City/location (ASANSOL, BANDEL)
- `status`: New, Running, Hold, Complete
- `towers`: Number of towers
- `bankaccountno`: Payment account
- `docs`: Array of document objects

---

### 2. `/towerproperty/availablePropertyForWebSite` (POST)
**Purpose**: Get property availability summary and floor-level details

**Request Payload**:
```json
{
  "ocode": "aastha",
  "shortname": "Rohinadihi Project",
  "tname": "Ashirbad",
  "ptype": "Flat"
}
```

**Response**:
```json
{
  "summary": [
    {
      "pname": "TYPE A",
      "total": 4,
      "booked": 4,
      "available": 0
    }
  ],
  "details": [
    {
      "floor": 0,
      "pname": "TYPE A",
      "area": 672,
      "total": 1,
      "booked": 1,
      "available": 0
    }
  ],
  "garages": [
    {
      "pname": "4 Wheeler Open",
      "total": 3,
      "booked": 2,
      "available": 1
    }
  ]
}
```

**Key Fields**:
- `summary`: Per property-type aggregates (total/booked/available)
- `details`: Floor-level breakdown with area
- `garages`: Parking/garage availability

---

### 3. `/towerproperty/unsoldPropertiesOfProject` (POST)
**Purpose**: List all unsold properties with rates and financial details

**Request Payload**:
```json
{
  "ocode": "aastha",
  "ptype": "Flat",
  "shortname": "optional filter by project",
  "branch": "optional filter by city"
}
```

**Response**: Array of unsold property records
```json
[
  {
    "_id": "...",
    "shortname": "Basu Tower",
    "tname": "ALAKANADA - PHASE - I",
    "ptype": "Flat",
    "pname": "G-5",
    "floor": 0,
    "noofunit": 1,
    "area": 915,
    "builduparea": 732,
    "rate": 2500,
    "amount": 2287500,
    "ocode": "aastha"
  }
]
```

**Key Fields**:
- `rate`: Price per square foot
- `amount`: Total price for the unit
- `area`: Carpet area
- `builduparea`: Built-up area
- `noofunit`: Number of units (usually 1 for properties)

---

## Query Patterns → Intent Mapping

| User Query Pattern | API Intent | Primary Endpoint |
|---|---|---|
| "How many flats in X project?" | `AVAILABILITY_BY_PROJECT` | `/availablePropertyForWebSite` |
| "Available shops in Asansol?" | `AVAILABILITY_BY_CITY` | `/unsoldPropertiesOfProject` |
| "Which project has most garages?" | `AVAILABILITY_SUMMARY` | `/unsoldPropertiesOfProject` |
| "Rate of flat in Y?" | `PRICE_LOOKUP` | `/unsoldPropertiesOfProject` |
| "Compare prices of Z and W" | `PRICE_COMPARISON` | `/unsoldPropertiesOfProject` |
| "How many units sold in X?" | `BOOKING_STATUS` | `/availablePropertyForWebSite` |
| "Show unsold flats with rates" | `UNSOLD_PROPERTIES` | `/unsoldPropertiesOfProject` |
| "Project status in Bandel?" | `PROJECT_METADATA` | `/project/search` |

---

## Implementation Notes

1. **Always include** `ocode: "aastha"` in POST payloads
2. **Authentication**: Add `Authorization: Bearer QXN0OEA6M21zMXBw` header
3. **Content-Type**: `application/json`
4. **Error handling**: Handle 401 (auth), 404 (not found), 500 (server errors), network timeouts
5. **Property types**: Use exact casing: `Flat`, `Garage`, `Shop`
6. **Branch names**: Use uppercase: `ASANSOL`, `BANDEL`
