CREATE CONSTRAINT IF NOT EXISTS
FOR (c:Country)
REQUIRE c.code IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS
FOR (e:Entity)
REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS
FOR (f:Filing)
REQUIRE f.id IS UNIQUE;
CREATE INDEX IF NOT EXISTS
FOR (f:Filing)
ON (f.icij_sar_id);
CREATE INDEX IF NOT EXISTS
FOR (e:Entity)
ON (e.name);
CREATE INDEX IF NOT EXISTS
FOR (f:Filing)
ON (f.begin);
CREATE INDEX IF NOT EXISTS
FOR (f:Filing)
ON (f.end);
CREATE INDEX IF NOT EXISTS
FOR (f:Filing)
ON (f.amount);
CREATE INDEX IF NOT EXISTS
FOR (c:Country)
ON (c.name);

LOAD CSV WITH HEADERS FROM "https://raw.githubusercontent.com/jexp/fincen/main/download_transactions_map.csv" AS value
MERGE (s:Filing {id: value.id})
SET s += value;

LOAD CSV WITH HEADERS FROM "https://raw.githubusercontent.com/jexp/fincen/main/download_bank_connections.csv" AS value
MATCH (f:Filing {icij_sar_id: value.icij_sar_id})
MERGE (filer:Entity {id: value.filer_org_name_id})
  ON CREATE SET
    filer.name = value.filer_org_name,
    filer.location =
      point({
        latitude: toFloat(value.filer_org_lat),
        longitude: toFloat(value.filer_org_lng)
      })
MERGE (other:Entity {id: value.entity_b_id})
  ON CREATE SET
    other.name = value.entity_b,
    other.location =
      point({
        latitude: toFloat(value.entity_b_lat),
        longitude: toFloat(value.entity_b_lng)
      }),
    other.country = value.entity_b_iso_code
MERGE (c:Country {code: value.entity_b_iso_code})
  ON CREATE SET c.name = value.entity_b_country
MERGE (f)<-[:FILED]-(filer)
MERGE (f)-[:CONCERNS]->(other)
MERGE (other)-[:COUNTRY]->(c);

MATCH (f:Filing)
SET f.transactions = toInteger(f.number_transactions)
SET f.amount = toFloat(f.amount_transactions)
SET
  f.end =
    date(
      datetime({
        epochSeconds:
          coalesce(apoc.date.parse(f.end_date, "s", "MMM dd, yyyy"), 0)
      }))
SET
  f.begin =
    date(
      datetime({
        epochSeconds:
          coalesce(apoc.date.parse(f.begin_date, "s", "MMM dd, yyyy"), 0)
      }))

MERGE (ben:Entity {id: f.beneficiary_bank_id})
  ON CREATE SET
    ben.name = f.beneficiary_bank,
    ben.location =
      point({
        latitude: toFloat(f.beneficiary_lat),
        longitude: toFloat(f.beneficiary_lng)
      })
MERGE (cben:Country {code: f.beneficiary_iso})
MERGE (ben)-[:COUNTRY]->(cben)
MERGE (f)-[:BENEFITS]->(ben)

MERGE (filer:Entity {id: f.filer_org_name_id})
  ON CREATE SET
    filer.name = f.filer_org_name,
    filer.location =
      point({
        latitude: toFloat(f.filer_org_lat),
        longitude: toFloat(f.filer_org_lng)
      })
MERGE (f)<-[:FILED]-(filer)

MERGE (org:Entity {id: f.originator_bank_id})
  ON CREATE SET
    org.name = f.originator_bank,
    org.location =
      point({latitude: toFloat(f.origin_lat), longitude: toFloat(f.origin_lng)})
MERGE (corg:Country {code: f.originator_iso})
MERGE (org)-[:COUNTRY]->(corg)
MERGE (f)-[:ORIGINATOR]->(org);