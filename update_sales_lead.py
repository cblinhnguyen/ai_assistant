#!/usr/bin/env python3
from datetime import datetime, timezone
import os

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.exceptions import DocumentNotFoundException
from couchbase.options import ClusterOptions
from dotenv import load_dotenv

from sales_lead import (
    lead_score_weighted,
    random_lead_status_and_pipeline_stage,
    random_notes,
)

# Load environment variables
load_dotenv()

# Couchbase connection config
COUCHBASE_CONNSTR = os.getenv("COUCHBASE_CONNSTR")
COUCHBASE_USERNAME = os.getenv("COUCHBASE_USERNAME")
COUCHBASE_PASSWORD = os.getenv("COUCHBASE_PASSWORD")
COUCHBASE_BUCKET = os.getenv("COUCHBASE_BUCKET")
COUCHBASE_SCOPE = os.getenv("COUCHBASE_SCOPE")
COUCHBASE_COLLECTION = os.getenv("COUCHBASE_COLLECTION")


def update_document(doc):
    if "sales_lead" not in doc:
        return doc, False

    audit_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    old_data = doc.get("old_data", {})
    changed = False

    # lead_status and pipeline_stage
    current_pipeline = doc["sales_lead"].get("pipeline_stage")
    current_status = doc["sales_lead"].get("lead_status")
    new_status, new_pipeline = random_lead_status_and_pipeline_stage()
    if new_status != current_status or new_pipeline != current_pipeline:
        old_data["lead_status"] = {
            "old_value": current_status,
            "audit_date": audit_date,
        }
        old_data["pipeline_stage"] = {
            "old_value": current_pipeline,
            "audit_date": audit_date,
        }
        doc["sales_lead"]["lead_status"] = new_status
        doc["sales_lead"]["pipeline_stage"] = new_pipeline
        changed = True

    # notes
    current_note = doc["sales_lead"].get("notes")
    new_note = random_notes()
    if new_note != current_note:
        old_data["notes"] = {"old_value": current_note, "audit_date": audit_date}
        doc["sales_lead"]["notes"] = new_note
        changed = True

    # lead_score
    current_score = doc["sales_lead"].get("lead_score", 0)
    new_score = lead_score_weighted(
        doc["sales_lead"].get("last_deal_size_usd", 0),
        new_status,
        new_pipeline,
        doc["sales_lead"].get("crm_activity_flag", False),
    )
    if new_score != current_score:
        old_data["lead_score"] = {"old_value": current_score, "audit_date": audit_date}
        doc["sales_lead"]["lead_score"] = new_score
        changed = True

    # high_priority_flag based on lead_score
    doc["sales_lead"]["high_priority_flag"] = doc["sales_lead"]["lead_score"] >= 80

    if changed:
        doc["old_data"] = old_data
        return doc, True

    return doc, False


def main():
    cluster = Cluster(
        COUCHBASE_CONNSTR,
        ClusterOptions(PasswordAuthenticator(COUCHBASE_USERNAME, COUCHBASE_PASSWORD)),
    )
    bucket = cluster.bucket(COUCHBASE_BUCKET)
    collection = bucket.default_collection()

    query = f"SELECT META().id FROM `{COUCHBASE_BUCKET}`"
    result = cluster.query(query)

    total = 0
    updated = 0

    for row in result:
        doc_id = row["id"]
        try:
            res = collection.get(doc_id)
            doc = res.content_as[dict]

            updated_doc, changed = update_document(doc)
            if changed:
                collection.upsert(doc_id, updated_doc)
                updated += 1
            total += 1

        except DocumentNotFoundException:
            continue

    print(f"Processed {total} documents.")
    print(f"Documents updated: {updated}")


if __name__ == "__main__":
    main()
