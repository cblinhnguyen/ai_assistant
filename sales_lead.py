"""
Sales Lead Management System
Contains all constants, utility functions, and random value generators
"""

from datetime import datetime, timedelta
import random

from faker import Faker

# Initialize Faker
fake = Faker()


class LeadStatus:
    """Lead status constants"""
    PROSPECT = "Prospect"
    QUALIFIED = "Qualified"
    NEGOTIATION = "Negotiation"
    WON = "Won"
    LOST = "Lost"


class PipelineStage:
    """Pipeline stage constants"""
    DISCOVERY = "Discovery"
    PROPOSAL_SENT = "Proposal Sent"
    CONTRACT_SENT = "Contract Sent"
    NEGOTIATION = "Negotiation"
    CLOSED_WON = "Closed Won"
    CLOSED_LOST = "Closed Lost"


class MarketRegion:
    """Market region constants"""
    NORTH_AMERICA = "North America"
    EUROPE = "Europe"
    SOUTHEAST_ASIA = "Southeast Asia"
    SOUTH_AMERICA = "South America"
    MIDDLE_EAST = "Middle East"
    AFRICA = "Africa"


class LeadSource:
    """Lead source constants"""
    REFERRAL = "Referral"
    COLD_CALL = "Cold Call"
    INBOUND_WEB_LEAD = "Inbound Web Lead"
    TRADE_SHOW = "Trade Show"
    PARTNER_REFERRAL = "Partner Referral"
    AD_CAMPAIGN = "Ad Campaign"


# Lead status lists for easy iteration
LEAD_STATUSES = [
    LeadStatus.PROSPECT,
    LeadStatus.QUALIFIED,
    LeadStatus.NEGOTIATION,
    LeadStatus.WON,
    LeadStatus.LOST
]

# Pipeline stages lists for easy iteration
PIPELINE_STAGES = [
    PipelineStage.DISCOVERY,
    PipelineStage.PROPOSAL_SENT,
    PipelineStage.CONTRACT_SENT,
    PipelineStage.NEGOTIATION,
    PipelineStage.CLOSED_WON,
    PipelineStage.CLOSED_LOST
]

# Market regions lists for easy iteration
MARKET_REGIONS = [
    MarketRegion.NORTH_AMERICA,
    MarketRegion.EUROPE,
    MarketRegion.SOUTHEAST_ASIA,
    MarketRegion.SOUTH_AMERICA,
    MarketRegion.MIDDLE_EAST,
    MarketRegion.AFRICA
]

# Lead sources lists for easy iteration
LEAD_SOURCES = [
    LeadSource.REFERRAL,
    LeadSource.COLD_CALL,
    LeadSource.INBOUND_WEB_LEAD,
    LeadSource.TRADE_SHOW,
    LeadSource.PARTNER_REFERRAL,
    LeadSource.AD_CAMPAIGN
]

# Status to pipeline stage mapping
STATUS_PIPELINE_MAPPING = {
    LeadStatus.PROSPECT: [PipelineStage.DISCOVERY, PipelineStage.PROPOSAL_SENT, PipelineStage.CONTRACT_SENT, PipelineStage.NEGOTIATION],
    LeadStatus.QUALIFIED: [PipelineStage.DISCOVERY, PipelineStage.PROPOSAL_SENT, PipelineStage.CONTRACT_SENT, PipelineStage.NEGOTIATION],
    LeadStatus.NEGOTIATION: [PipelineStage.PROPOSAL_SENT, PipelineStage.CONTRACT_SENT, PipelineStage.NEGOTIATION],
    LeadStatus.WON: [PipelineStage.CLOSED_WON],
    LeadStatus.LOST: [PipelineStage.CLOSED_LOST]
}

# Lead score calculation mappings
STATUS_SCORES = {
    LeadStatus.WON: 25,
    LeadStatus.NEGOTIATION: 15,
    LeadStatus.QUALIFIED: 10,
    LeadStatus.PROSPECT: 5,
    LeadStatus.LOST: -10
}

PIPELINE_SCORES = {
    PipelineStage.CLOSED_WON: 25,
    PipelineStage.CONTRACT_SENT: 15,
    PipelineStage.PROPOSAL_SENT: 10,
    PipelineStage.DISCOVERY: 5,
    PipelineStage.CLOSED_LOST: -10,
    PipelineStage.NEGOTIATION: 20
}


# Utility Functions
def random_date(start, end):
    """Generate a random date between start and end dates"""
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime(
        "%Y-%m-%d"
    )


def generate_company_name():
    """Generate a random company name with suffix"""
    suffixes = [
        "Inc.",
        "LLC",
        "Corp.",
        "Holdings",
        "Ventures",
        "Systems",
        "Solutions",
        "Partners",
        "Group",
    ]
    return f"{fake.company()} {random.choice(suffixes)}"


def random_notes():
    """Generate random notes for leads"""
    notes_samples = [
        "Contacted client, awaiting response.",
        "Sent proposal, pending approval.",
        "Negotiations ongoing, positive signs.",
        "Lost contact, follow-up needed.",
        "Client requested revised pricing.",
    ]
    return random.choice(notes_samples)


def random_lead_score(current_score):
    """Generate a random lead score variation"""
    delta = random.choice([-5, 5])
    return max(0, min(100, current_score + delta))


def lead_score_weighted(last_deal_size, lead_status, pipeline_stage, crm_active):
    """Calculate weighted lead score based on various factors"""
    score = random.randint(20, 50)
    deal_score = min(last_deal_size / 166666, 30)
    score += deal_score
    if lead_status in (LeadStatus.WON, LeadStatus.LOST):
        return 0
    score += STATUS_SCORES.get(lead_status, 0)
    score += PIPELINE_SCORES.get(pipeline_stage, 0)
    if crm_active:
        score += 10
    return min(max(int(score), 0), 100)


def get_quarter_dates(quarter):
    """Get start and end dates for a given quarter"""
    quarter_dates = {
        "Q1 2025": (datetime(2025, 1, 1), datetime(2025, 3, 31)),
        "Q2 2025": (datetime(2025, 4, 1), datetime(2025, 6, 30)),
        "Q3 2025": (datetime(2025, 7, 1), datetime(2025, 9, 30)),
        "Q4 2025": (datetime(2025, 10, 1), datetime(2025, 12, 31)),
    }
    return quarter_dates.get(quarter, (datetime(2025, 1, 1), datetime(2025, 3, 31)))


def random_lead_status_and_pipeline_stage():
    """Generate a random but realistic lead status and pipeline stage combination"""
    choices = []
    for status in LEAD_STATUSES:
        for stage in STATUS_PIPELINE_MAPPING[status]:
            choices.append((status, stage))
    return random.choice(choices)
