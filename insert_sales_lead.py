#!/usr/bin/env python3
import os
import random
import uuid

from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from dotenv import load_dotenv

from sales_lead import (
    LEAD_SOURCES,
    MARKET_REGIONS,
    fake,
    generate_company_name,
    get_quarter_dates,
    lead_score_weighted,
    random_date,
    random_lead_status_and_pipeline_stage,
)

# Load environment variables
load_dotenv()

COUCHBASE_CONNSTR = os.getenv("COUCHBASE_CONNSTR")
COUCHBASE_USERNAME = os.getenv("COUCHBASE_USERNAME")
COUCHBASE_PASSWORD = os.getenv("COUCHBASE_PASSWORD")
COUCHBASE_BUCKET = os.getenv("COUCHBASE_BUCKET")
COUCHBASE_SCOPE = os.getenv("COUCHBASE_SCOPE")
COUCHBASE_COLLECTION = os.getenv("COUCHBASE_COLLECTION")


cluster = Cluster(
    COUCHBASE_CONNSTR,
    ClusterOptions(PasswordAuthenticator(COUCHBASE_USERNAME, COUCHBASE_PASSWORD)),
)
bucket = cluster.bucket(COUCHBASE_BUCKET)
collection = bucket.scope(COUCHBASE_SCOPE).collection(COUCHBASE_COLLECTION)


def generate_random_record():
    quarters = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]

    lead_id = str(uuid.uuid4())
    last_deal_size = random.randint(25_000, 5_000_000)
    quarter = random.choice(quarters)

    # Get quarter date range for last contact date
    start_date, end_date = get_quarter_dates(quarter)
    last_contact_date = random_date(start_date, end_date)

    # Generate realistic status and pipeline combinations using constants
    lead_status, pipeline_stage = random_lead_status_and_pipeline_stage()

    crm_activity = random.choice([True, False])
    score = lead_score_weighted(
        last_deal_size, lead_status, pipeline_stage, crm_activity
    )

    return {
        "lead_id": lead_id,
        "sales_lead": {
            "company_name": generate_company_name(),
            "quarter": quarter,
            "market_cap_usd": random.randint(50_000_000, 10_000_000_000),
            "annual_sales_usd": random.randint(5_000_000, 2_000_000_000),
            "number_of_customers": random.randint(500, 100_000),
            "primary_market_region": random.choice(MARKET_REGIONS),
            "sales_contact_name": fake.name(),
            "sales_contact_email": fake.email(),
            "date_of_last_contact": last_contact_date,
            "lead_status": lead_status,
            "pipeline_stage": pipeline_stage,
            "last_deal_size_usd": last_deal_size,
            "lead_source": random.choice(LEAD_SOURCES),
            "notes": fake.sentence(nb_words=12),
            "crm_activity_flag": crm_activity,
            "lead_score": score,
            "high_priority_flag": score >= 80,
        },
    }


def main():
    # Generate and insert records
    num_records = 5
    success_count = 0
    error_count = 0

    for _ in range(num_records):
        doc = generate_random_record()
        doc_key = f"lead::{doc['lead_id']}"
        try:
            collection.insert(doc_key, doc)
            success_count += 1
        except Exception as e:
            error_count += 1

    print(
        f"✅ Import completed: {success_count} records inserted, {error_count} errors."
    )


if __name__ == "__main__":
    main()
