#!/usr/bin/env python3
import json
import os
import re
import traceback

import boto3
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load environment variables
load_dotenv()

# ------------------------------
# Couchbase setup with environment variables
# ------------------------------
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

# ------------------------------
# Bedrock setup with explicit credentials
# ------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# Create Bedrock client with explicit credentials
bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

app = Flask(__name__)


# ------------------------------
# Utility functions
# ------------------------------
def format_usd(amount):
    try:
        return f"${amount:,.0f}"
    except Exception:
        return str(amount)


def clean_text(text):
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"^\*+", "", text)
    text = re.sub(r"\*+$", "", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text


def bullet_recommendation(text):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return "\n".join([f"- {s.strip()}" for s in sentences if s.strip()])


def format_old_data(old_data):
    """Create human-readable string describing changes."""
    changes = []
    for field, change in old_data.items():
        old_value = change.get("old_value", "N/A")
        audit_date = change.get("audit_date", "")
        changes.append(f"- {field}: was '{old_value}' (as of {audit_date})")
    return "\n".join(changes)


# ------------------------------
# Health check
# ------------------------------
@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


# ------------------------------
# Generate summary for a single lead
# ------------------------------
@app.route("/generate_summary", methods=["POST"])
def generate_summary():
    try:
        data = request.get_json(force=True)
        print("📥 Raw incoming request data:", data)

        lead_id = data.get("lead_id")
        sales_lead = data.get("sales_lead")
        old_data = data.get("old_data", {})

        if not lead_id or not sales_lead:
            return jsonify({"error": "Missing lead_id or sales_lead"}), 400

        # Normalize key to avoid double 'lead::'
        doc_key = lead_id
        if doc_key.startswith("lead::lead::"):
            doc_key = doc_key.replace("lead::lead::", "lead::", 1)

        # Format USD fields
        market_cap = format_usd(sales_lead.get("market_cap_usd", 0))
        annual_sales = format_usd(sales_lead.get("annual_sales_usd", 0))
        last_deal = format_usd(sales_lead.get("last_deal_size_usd", 0))

        # Include old_data changes in prompt
        old_changes_text = format_old_data(old_data)

        lead_score = sales_lead.get("lead_score", 0)
        lead_score_text = f"{lead_score}/100" if lead_score >= 0 else "N/A"

        # Build prompt for Bedrock
        prompt = f"""
You are an expert enterprise sales strategist with 15+ years of experience in B2B sales and account management. Your expertise includes lead qualification, pipeline management, and strategic account development.

TASK: Analyze the following sales lead data and provide a concise executive summary followed by actionable recommendations.

FORMAT REQUIREMENTS:
- Use plain text only (no markdown, bold, or italic formatting)
- Format all currency values as USD with dollar signs and commas (e.g., $1,234,567)
- Follow this exact structure:

Summary: [4-5 sentences describing the current lead state and key changes since last update]

Recommendation: [4-5 specific, actionable bullet points for next steps, just output sentences]

LEAD CHANGE HISTORY:
{old_changes_text if old_changes_text else "No prior changes recorded - this is the initial lead record."}

CURRENT LEAD PROFILE:
Company: {sales_lead.get('company_name', 'N/A')}
Market Region: {sales_lead.get('primary_market_region', 'N/A')}
Market Cap: {market_cap}
Annual Revenue: {annual_sales}
Lead Status: {sales_lead.get('lead_status', 'N/A')}
Pipeline Stage: {sales_lead.get('pipeline_stage', 'N/A')}
Deal Size: {last_deal}
Contact: {sales_lead.get('sales_contact_name', 'N/A')} ({sales_lead.get('sales_contact_email', 'N/A')})
Lead Source: {sales_lead.get('lead_source', 'N/A')}
Last Contact Date: {sales_lead.get('date_of_last_contact', 'N/A')}
CRM Activity: {"Active" if sales_lead.get('crm_activity_flag', False) else "Inactive"}
Lead Score: {lead_score_text}
Priority Level: {"HIGH PRIORITY" if sales_lead.get('high_priority_flag', False) else "Standard"}
Notes: {sales_lead.get('notes', 'None')}

ANALYSIS INSTRUCTIONS:
1. In the summary, focus on the lead's current position in the sales cycle and any significant changes
2. For recommendations, prioritize immediate actions that will advance this lead through the pipeline
3. Consider the lead's market position, deal size potential, current engagement level and notes
4. Make recommendations specific and time-bound where possible

Generate your response now:
"""

        # Call Bedrock model
        response = bedrock.invoke_model(
            modelId="meta.llama3-70b-instruct-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"prompt": prompt, "temperature": 0.7}),
        )

        response_body = json.loads(response["body"].read())
        generated_text = response_body.get("generation", "").strip()

        # Parse summary and recommendation
        summary_match = re.search(
            r"(?i)summary:\s*(.*?)(?=\n\s*recommendation:|\Z)",
            generated_text,
            re.DOTALL,
        )
        recommendation_match = re.search(
            r"(?i)recommendation:\s*(.*)", generated_text, re.DOTALL
        )

        summary = summary_match.group(1).strip() if summary_match else generated_text
        recommendation = (
            recommendation_match.group(1).strip() if recommendation_match else ""
        )

        # Cleanup
        summary = clean_text(summary)
        recommendation = clean_text(recommendation)

        # Extract recommendation if embedded in summary
        rec_from_summary = re.search(
            r"Recommendation:\s*(.*)", summary, re.DOTALL | re.IGNORECASE
        )
        if rec_from_summary and not recommendation:
            recommendation = rec_from_summary.group(1).strip()
            summary = re.sub(
                r"Recommendation:.*", "", summary, flags=re.DOTALL | re.IGNORECASE
            ).strip()

        # Bullet points for recommendation
        recommendation = bullet_recommendation(recommendation)

        # High-priority flag
        if sales_lead.get("high_priority_flag", False):
            recommendation = "[ High-priority lead ]\n" + recommendation

        # ------------------------------
        # Option 1: Merge with existing document to preserve old_data
        # ------------------------------
        try:
            # Get existing document if it exists
            existing_doc = {}
            try:
                existing_doc = collection.get(doc_key).content_as[dict]
            except Exception:
                pass  # doc might not exist yet

            # Merge new fields, preserve old_data
            merged_doc = {
                **existing_doc,  # keeps old_data and other fields
                "sales_lead": sales_lead,
                "summary": summary,
                "recommendation": recommendation,
            }

        except Exception as e:
            print(f"❌ Couchbase upsert error for {doc_key}: {e}")

        print(f"✅ Returning document {doc_key} with old_data preserved")
        return jsonify(
            {"lead_id": doc_key, "summary": summary, "recommendation": recommendation}
        )

    except Exception as e:
        print("❌ Error in /generate_summary:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
