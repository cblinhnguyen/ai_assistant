#!/usr/bin/env python3
"""
AI Sales Lead Assistant - Streamlit Web Application

This application provides a comprehensive web interface for managing sales leads
with AI-powered insights and recommendations. It allows users to:

- View all sales leads with filtering and search capabilities
- Create new sales leads with automatic lead scoring
- Edit existing leads with audit trail functionality
- Display AI-generated summaries and recommendations
- Track lead metrics and pipeline value

The application uses Couchbase as the backend database and Streamlit for the
web interface. Lead scoring is calculated using weighted algorithms based on
deal size, lead status, pipeline stage, and CRM activity.
"""

# Standard library imports
from datetime import datetime, timezone
import os
import uuid

# Third-party imports for database connectivity
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from dotenv import load_dotenv
import streamlit as st

# Local imports for sales lead data models and utilities
from sales_lead import (
    LEAD_SOURCES,  # Available lead source options
    LEAD_STATUSES,  # Available lead status options
    LeadSource,  # Lead source enumeration
    LeadStatus,  # Lead status enumeration
    MARKET_REGIONS,  # Available market region options
    MarketRegion,  # Market region enumeration
    PIPELINE_STAGES,  # Available pipeline stage options
    PipelineStage,  # Pipeline stage enumeration
    lead_score_weighted,  # Lead scoring algorithm
)

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# CONFIGURATION SECTION
# =============================================================================

# Couchbase database connection parameters
# These are loaded from environment variables for security and flexibility
COUCHBASE_CONNSTR = os.getenv("COUCHBASE_CONNSTR")  # Couchbase connection string
COUCHBASE_USERNAME = os.getenv("COUCHBASE_USERNAME")  # Database username
COUCHBASE_PASSWORD = os.getenv("COUCHBASE_PASSWORD")  # Database password
COUCHBASE_BUCKET = os.getenv("COUCHBASE_BUCKET")  # Database bucket name
COUCHBASE_SCOPE = os.getenv("COUCHBASE_SCOPE")  # Database scope name
COUCHBASE_COLLECTION = os.getenv("COUCHBASE_COLLECTION")  # Database collection name

# Streamlit page configuration
# Sets up the web application's appearance and behavior
st.set_page_config(
    page_title="AI Sales Lead Assistant",  # Browser tab title
    page_icon="📊",  # Browser tab icon (chart emoji)
    layout="wide",  # Use wide layout for better space utilization
    initial_sidebar_state="expanded",  # Start with sidebar expanded
)

# =============================================================================
# CUSTOM CSS STYLES
# =============================================================================

# Custom CSS for enhanced UI styling and visual hierarchy
# These styles improve the user experience with better visual indicators
st.markdown(
    """
<style>
    /* Main application header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;           /* Primary blue color */
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Metric card styling for dashboard statistics */
    .metric-card {
        background-color: #f0f2f6;    /* Light gray background */
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;  /* Blue left border for emphasis */
    }
    
    /* Lead container styling for individual lead cards */
    .lead-container {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e0e0e0;      /* Subtle border */
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);  /* Soft shadow for depth */
        margin-bottom: 1rem;
    }
    
    /* Base priority badge styling */
    .priority-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;           /* Rounded corners */
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    /* High priority badge - red color scheme */
    .priority-badge-high {
        background-color: #f44336;     /* Red background */
        color: white;
    }
    
    /* Medium priority badge - orange color scheme */
    .priority-badge-medium {
        background-color: #ff9800;     /* Orange background */
        color: white;
    }
    
    /* Low priority badge - green color scheme */
    .priority-badge-low {
        background-color: #4caf50;     /* Green background */
        color: white;
    }
    
    /* Closed priority badge - gray color scheme */
    .priority-badge-closed {
        background-color: #757575;     /* Gray background */
        color: white;
    }
    
    /* High lead score text styling */
    .lead-score-high {
        color: #f44336;               /* Red text for high scores */
        font-weight: bold;
        font-size: 1.2em;
    }
    
    /* Medium lead score text styling */
    .lead-score-medium {
        color: #ff9800;               /* Orange text for medium scores */
        font-weight: bold;
        font-size: 1.1em;
    }
    
    /* Low lead score text styling */
    .lead-score-low {
        color: #4caf50;               /* Green text for low scores */
        font-weight: bold;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# DATABASE CONNECTION AND UTILITY FUNCTIONS
# =============================================================================


@st.cache_resource
def get_couchbase_connection():
    """
    Initialize and return a cached Couchbase database connection.

    This function establishes a connection to the Couchbase cluster using
    the configuration from environment variables. The connection is cached
    by Streamlit to improve performance and avoid repeated connection attempts.

    Returns:
        tuple: (cluster, collection) if successful, (None, None) if failed

    Raises:
        Exception: If connection fails, displays error message to user
    """
    try:
        # Create cluster connection with authentication
        cluster = Cluster(
            COUCHBASE_CONNSTR,
            ClusterOptions(
                PasswordAuthenticator(COUCHBASE_USERNAME, COUCHBASE_PASSWORD)
            ),
        )

        # Get the specific bucket, scope, and collection
        bucket = cluster.bucket(COUCHBASE_BUCKET)
        collection = bucket.scope(COUCHBASE_SCOPE).collection(COUCHBASE_COLLECTION)

        return cluster, collection
    except Exception as e:
        st.error(f"Failed to connect to Couchbase: {e}")
        return None, None


def format_usd(amount):
    """
    Format a numeric amount as USD currency string.

    Args:
        amount (int/float): The amount to format

    Returns:
        str: Formatted currency string (e.g., "$1,000,000")
    """
    try:
        return f"${amount:,.0f}"
    except Exception:
        return str(amount)


def format_lead_score(score):
    """
    Format a lead score for display, showing N/A for negative scores (closed leads).

    Args:
        score (int/float/None): The lead score to format

    Returns:
        str: Formatted score string ("N/A" for negative/None scores, otherwise "XX/100")
    """
    if score is None or score < 0:
        return "N/A"
    return f"{int(score)}/100"


def get_priority_badge_class(score):
    """
    Determine CSS class for priority badge based on lead score.

    Args:
        score (int/float/None): Lead score (negative scores indicate closed leads)

    Returns:
        str: CSS class name for priority badge styling
    """
    if score is None or score < 0:
        return "priority-badge-closed"  # Closed leads get closed styling
    elif score >= 80:
        return "priority-badge-high"
    elif score >= 50:
        return "priority-badge-medium"
    else:
        return "priority-badge-low"


def get_priority_text(score):
    """
    Get priority level text based on lead score.

    Args:
        score (int/float/None): Lead score (negative scores indicate closed leads)

    Returns:
        str: Priority level ("CLOSED", "HIGH", "MEDIUM", or "LOW")
    """
    if score is None or score < 0:
        return "CLOSED"
    elif score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    else:
        return "LOW"


def get_all_sales_leads(cluster, collection):
    """
    Retrieve all sales leads from the Couchbase database.

    This function queries the database for all documents with IDs starting
    with "lead::" and returns them sorted by lead score in descending order.

    Args:
        cluster: Couchbase cluster connection
        collection: Couchbase collection object

    Returns:
        list: List of lead dictionaries with 'id' and 'data' keys,
              sorted by lead score (highest first)
    """
    try:
        # Query for all documents with lead:: prefix
        query = f'SELECT META().id, * FROM `{COUCHBASE_BUCKET}`.{COUCHBASE_SCOPE}.{COUCHBASE_COLLECTION} WHERE META().id LIKE "lead::%"'
        result = cluster.query(query)
    except Exception as e:
        st.error(f"Error fetching sales leads: {e}")
        return []  # Return empty list instead of None

    # Process query results into lead objects
    leads = []
    for row in result:
        doc_id = row["id"]
        doc_data = row[COUCHBASE_COLLECTION]
        leads.append({"id": doc_id, "data": doc_data})

    # Sort leads by lead score in descending order (highest first)
    leads = sorted(
        leads, key=lambda x: x["data"]["sales_lead"]["lead_score"], reverse=True
    )

    return leads


# =============================================================================
# MAIN APPLICATION FUNCTIONS
# =============================================================================


def main():
    """
    Main application entry point that handles routing between different pages.

    This function determines which page to display based on URL parameters
    and session state, then routes to the appropriate page handler.

    Page routing logic:
    1. Edit page: If edit_lead_id is in query params or session state
    2. Create page: If show_create_form is True in session state
    3. Default: Main leads view page
    """
    # Display main application header
    st.markdown(
        '<h1 class="main-header">AI Sales Lead Assistant</h1>', unsafe_allow_html=True
    )

    # Initialize database connection
    cluster, collection = get_couchbase_connection()
    if not cluster:
        st.error("Cannot connect to Couchbase. Please check your configuration.")
        return

    # Route to appropriate page based on session state and URL parameters
    if "edit_lead_id" in st.query_params or "edit_lead_id" in st.session_state:
        # User is editing a specific lead
        edit_lead_page(cluster, collection)
    elif (
        "show_create_form" in st.session_state and st.session_state["show_create_form"]
    ):
        # User is creating a new lead
        create_new_lead_page(collection)
    else:
        # Default: Display all leads with filtering and search
        view_all_leads(cluster, collection)


def view_all_leads(cluster, collection):
    """
    Display the main leads dashboard with filtering, search, and metrics.

    This function shows all sales leads in a dashboard format with:
    - Key performance metrics (total leads, high priority count, average score, pipeline value)
    - Search and filtering capabilities
    - Individual lead cards with priority badges and key information
    - Action buttons for editing leads
    - AI summaries and recommendations (if available)

    Args:
        cluster: Couchbase cluster connection
        collection: Couchbase collection object
    """
    # Page header with action button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("All Sales Leads")
    with col2:
        # Button to navigate to create new lead page
        if st.button("Add New Lead", use_container_width=True):
            st.session_state["show_create_form"] = True
            st.rerun()

    # Retrieve all leads from database
    leads = get_all_sales_leads(cluster, collection)

    # Handle empty state
    if not leads:
        st.info("No sales leads found. Create some leads to get started!")
        return

    # =============================================================================
    # DASHBOARD METRICS SECTION
    # =============================================================================

    # Calculate key performance indicators
    col1, col2, col3, col4 = st.columns(4)

    total_leads = len(leads)

    # Count high priority leads (lead score >= 80)
    high_priority = sum(
        1
        for lead in leads
        if lead["data"].get("sales_lead", {}).get("high_priority_flag", False)
    )

    # Calculate average lead score across all leads (excluding negative scores for closed leads)
    valid_scores = [
        lead["data"].get("sales_lead", {}).get("lead_score", 0) 
        for lead in leads 
        if lead["data"].get("sales_lead", {}).get("lead_score", 0) >= 0
    ]
    avg_score = (
        sum(valid_scores) / len(valid_scores)
        if valid_scores
        else 0
    )

    # Calculate total pipeline value (sum of all last deal sizes)
    total_value = sum(
        lead["data"].get("sales_lead", {}).get("last_deal_size_usd", 0)
        for lead in leads
    )

    # Display metrics in dashboard cards
    with col1:
        st.metric("Total Leads", total_leads)
    with col2:
        st.metric("High Priority", high_priority)
    with col3:
        st.metric("Avg Lead Score", f"{avg_score:.1f}")
    with col4:
        st.metric("Total Pipeline Value", format_usd(total_value))

    # =============================================================================
    # SEARCH AND FILTER SECTION
    # =============================================================================

    st.subheader("Search & Filter")
    col1, col2, col3 = st.columns(3)

    # Search input for company name filtering
    with col1:
        search_term = st.text_input("Search by company name", "")

    # Status filter dropdown
    with col2:
        status_filter = st.selectbox(
            "Filter by status",
            ["All"] + LEAD_STATUSES,
        )

    # Priority filter dropdown based on lead scores
    with col3:
        priority_filter = st.selectbox(
            "Filter by priority",
            ["All", "High Priority", "Medium Priority", "Low Priority", "Closed Leads"],
        )

    # =============================================================================
    # LEAD FILTERING LOGIC
    # =============================================================================

    # Start with all leads and apply filters progressively
    filtered_leads = leads

    # Apply company name search filter (case-insensitive)
    if search_term:
        filtered_leads = [
            lead
            for lead in filtered_leads
            if search_term.lower()
            in lead["data"].get("sales_lead", {}).get("company_name", "").lower()
        ]

    # Apply lead status filter
    if status_filter != "All":
        filtered_leads = [
            lead
            for lead in filtered_leads
            if lead["data"].get("sales_lead", {}).get("lead_status") == status_filter
        ]

    # Apply priority filter based on lead score ranges
    if priority_filter == "High Priority":
        # High priority: lead score >= 80
        filtered_leads = [
            lead
            for lead in filtered_leads
            if lead["data"].get("sales_lead", {}).get("high_priority_flag", False)
        ]
    elif priority_filter == "Medium Priority":
        # Medium priority: 50 <= lead score < 80
        filtered_leads = [
            lead
            for lead in filtered_leads
            if 50 <= lead["data"].get("sales_lead", {}).get("lead_score", 0) < 80
        ]
    elif priority_filter == "Low Priority":
        # Low priority: 0 <= lead score < 50
        filtered_leads = [
            lead
            for lead in filtered_leads
            if 0 <= lead["data"].get("sales_lead", {}).get("lead_score", 0) < 50
        ]
    elif priority_filter == "Closed Leads":
        # Closed leads: negative or None lead scores
        filtered_leads = [
            lead
            for lead in filtered_leads
            if lead["data"].get("sales_lead", {}).get("lead_score", 0) < 0
        ]

    # Display filtered results count
    st.write(f"Showing {len(filtered_leads)} of {total_leads} leads")

    # =============================================================================
    # LEAD DISPLAY SECTION
    # =============================================================================

    # Display each filtered lead in a card format
    for lead in filtered_leads:
        sales_lead = lead["data"].get("sales_lead", {})
        lead_score = sales_lead.get("lead_score", 0)

        # Determine priority styling based on lead score
        priority_badge_class = get_priority_badge_class(lead_score)
        priority_text = get_priority_text(lead_score)

        # Create bordered container for each lead
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            # Left column: Company information and contact details
            with col1:
                # Company name with priority badge
                company_name = sales_lead.get("company_name", "N/A")
                st.markdown(
                    f'<h3>{company_name} <span class="priority-badge {priority_badge_class}">{priority_text}</span></h3>',
                    unsafe_allow_html=True,
                )

                # Contact information
                st.write(
                    f"**Contact:** {sales_lead.get('sales_contact_name', 'N/A')} ({sales_lead.get('sales_contact_email', 'N/A')})"
                )

                # Market region
                st.write(
                    f"**Region:** {sales_lead.get('primary_market_region', 'N/A')}"
                )

            # Middle column: Lead metrics and status
            with col2:
                st.metric("Lead Score", format_lead_score(lead_score))
                st.metric("Status", sales_lead.get("lead_status", "N/A"))
                st.metric("Pipeline Stage", sales_lead.get("pipeline_stage", "N/A"))

            # Right column: Financial metrics
            with col3:
                st.metric("Market Cap", format_usd(sales_lead.get("market_cap_usd", 0)))
                st.metric(
                    "Annual Sales", format_usd(sales_lead.get("annual_sales_usd", 0))
                )
                st.metric(
                    "Deal Size", format_usd(sales_lead.get("last_deal_size_usd", 0))
                )

            # Action button to edit the lead
            if st.button(f"Edit Lead", key=f"edit_{lead['id']}"):
                # Store lead ID in session state and navigate to edit page
                st.session_state["edit_lead_id"] = lead["id"]
                st.rerun()

            # =============================================================================
            # AI INSIGHTS SECTION
            # =============================================================================

            # Display AI-generated summary and recommendations if available
            if "summary" in lead["data"] and "recommendation" in lead["data"]:
                with st.expander("AI Summary & Recommendations"):
                    st.write("**Summary:**")
                    st.text(lead["data"].get("summary", "No summary available"))
                    st.write("**Recommendations:**")
                    st.text(
                        lead["data"].get(
                            "recommendation", "No recommendations available"
                        )
                    )

            # Display additional notes if available
            if sales_lead.get("notes"):
                with st.expander("Notes"):
                    st.write(sales_lead.get("notes"))


def edit_lead_page(cluster, collection):
    """
    Display the edit lead page with form for modifying existing lead data.

    This function handles the editing workflow:
    1. Validates that a lead is selected for editing
    2. Retrieves the selected lead from the database
    3. Displays a pre-populated form with current lead data
    4. Handles form submission and updates the database
    5. Maintains audit trail of all changes

    Args:
        cluster: Couchbase cluster connection
        collection: Couchbase collection object
    """
    st.header("Edit Sales Lead")

    # =============================================================================
    # LEAD SELECTION VALIDATION
    # =============================================================================

    # Check if a lead is selected for editing
    if "edit_lead_id" not in st.session_state:
        st.error(
            "No lead selected for editing. Please go back to 'View All Leads' and click 'Edit Lead' on a specific lead."
        )
        if st.button("Back to View All Leads"):
            st.rerun()
        return

    # =============================================================================
    # LEAD DATA RETRIEVAL
    # =============================================================================

    # Retrieve all leads and find the selected one
    leads = get_all_sales_leads(cluster, collection)
    selected_lead = None

    for lead in leads:
        if lead["id"] == st.session_state["edit_lead_id"]:
            selected_lead = lead
            break

    # Handle case where selected lead is not found
    if not selected_lead:
        st.error(
            "Selected lead not found. Please go back to 'View All Leads' and try again."
        )
        if st.button("Back to View All Leads"):
            del st.session_state["edit_lead_id"]
            st.rerun()
        return

    # Extract sales lead data for form population
    sales_lead = selected_lead["data"].get("sales_lead", {})

    # =============================================================================
    # PAGE NAVIGATION
    # =============================================================================

    # Back button to return to main leads view
    if st.button("Back to View All Leads"):
        del st.session_state["edit_lead_id"]
        st.rerun()

    # Display current lead being edited
    st.subheader(f"Editing: {sales_lead.get('company_name', 'N/A')}")

    # =============================================================================
    # EDIT FORM - COMPANY INFORMATION SECTION
    # =============================================================================

    with st.form(f"edit_lead_form_{selected_lead['id']}"):
        # Company Information Section
        st.subheader("Company Information")
        col1, col2 = st.columns(2)

        # Left column: Company details and financial information
        with col1:
            # Required field: Company name
            new_company_name = st.text_input(
                "Company Name *",
                value=sales_lead.get("company_name", ""),
                placeholder="Enter company name",
            )

            # Required field: Market region selection
            new_market_region = st.selectbox(
                "Primary Market Region *",
                MARKET_REGIONS,
                index=MARKET_REGIONS.index(
                    sales_lead.get("primary_market_region", MarketRegion.NORTH_AMERICA)
                ),
            )

            # Required field: Market capitalization
            new_market_cap = st.number_input(
                "Market Cap (USD) *",
                min_value=0,
                value=sales_lead.get("market_cap_usd", 0),
                step=1000000,
            )

            # Required field: Annual sales revenue
            new_annual_sales = st.number_input(
                "Annual Sales (USD) *",
                min_value=0,
                value=sales_lead.get("annual_sales_usd", 0),
                step=1000000,
            )

            # Optional field: Number of customers
            new_num_customers = st.number_input(
                "Number of Customers",
                min_value=0,
                value=sales_lead.get("number_of_customers", 0),
                step=100,
            )

        # Right column: Contact information and lead source
        with col2:
            # Required field: Sales contact name
            new_sales_contact_name = st.text_input(
                "Sales Contact Name *",
                value=sales_lead.get("sales_contact_name", ""),
                placeholder="Enter contact name",
            )

            # Required field: Sales contact email
            new_sales_contact_email = st.text_input(
                "Sales Contact Email *",
                value=sales_lead.get("sales_contact_email", ""),
                placeholder="Enter email address",
            )

            # Date handling with error recovery
            try:
                current_date = datetime.strptime(
                    sales_lead.get(
                        "date_of_last_contact", datetime.now().strftime("%Y-%m-%d")
                    ),
                    "%Y-%m-%d",
                ).date()
            except:
                # Fallback to current date if parsing fails
                current_date = datetime.now().date()

            # Date of last contact
            new_last_contact_date = st.date_input(
                "Date of Last Contact", value=current_date
            )

            # Lead source selection
            new_lead_source = st.selectbox(
                "Lead Source",
                LEAD_SOURCES,
                index=LEAD_SOURCES.index(
                    sales_lead.get("lead_source", LeadSource.REFERRAL)
                ),
            )

            # CRM activity flag
            new_crm_activity = st.checkbox(
                "CRM Activity Flag", value=sales_lead.get("crm_activity_flag", False)
            )

        # =============================================================================
        # EDIT FORM - LEAD STATUS & PIPELINE SECTION
        # =============================================================================

        st.subheader("Lead Status & Pipeline")
        col1, col2 = st.columns(2)

        # Left column: Lead status and pipeline stage
        with col1:
            # Required field: Lead status
            new_lead_status = st.selectbox(
                "Lead Status *",
                LEAD_STATUSES,
                index=LEAD_STATUSES.index(
                    sales_lead.get("lead_status", LeadStatus.PROSPECT)
                ),
            )

            # Required field: Pipeline stage
            new_pipeline_stage = st.selectbox(
                "Pipeline Stage *",
                PIPELINE_STAGES,
                index=PIPELINE_STAGES.index(
                    sales_lead.get("pipeline_stage", PipelineStage.DISCOVERY)
                ),
            )

        # Right column: Deal size
        with col2:
            # Required field: Last deal size
            new_last_deal_size = st.number_input(
                "Deal Size (USD) *",
                min_value=0,
                value=sales_lead.get("last_deal_size_usd", 0),
                step=10000,
            )

            # Display calculated lead score
            current_lead_score = sales_lead.get("lead_score", 0)
            st.metric("Current Lead Score", format_lead_score(current_lead_score))

            st.info(
                "💡 Lead score will be automatically calculated based on deal size, status, pipeline stage, and CRM activity. Negative scores indicate closed leads and display as 'N/A'."
            )

        # =============================================================================
        # EDIT FORM - ADDITIONAL INFORMATION SECTION
        # =============================================================================

        st.subheader("Additional Information")
        col1, col2 = st.columns(2)

        # Left column: Notes and additional information
        with col1:
            # Optional field: Notes
            new_notes = st.text_area(
                "Notes",
                value=sales_lead.get("notes", ""),
                placeholder="Enter updated notes",
            )

        # Right column: Quarter selection
        with col2:
            # Quarter selection with error handling
            quarter_options = ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]
            current_quarter = sales_lead.get("quarter", "Q1 2025")
            try:
                quarter_index = quarter_options.index(current_quarter)
            except ValueError:
                # Default to Q1 2025 if current quarter not found in options
                quarter_index = 0
            new_quarter = st.selectbox("Quarter", quarter_options, index=quarter_index)

        # =============================================================================
        # FORM SUBMISSION BUTTONS
        # =============================================================================

        col_save, col_cancel = st.columns(2)
        with col_save:
            submitted = st.form_submit_button("Save Changes", type="primary")
        with col_cancel:
            cancel = st.form_submit_button("Cancel")

        # Handle form cancellation
        if cancel:
            del st.session_state["edit_lead_id"]
            st.rerun()

        # =============================================================================
        # FORM VALIDATION AND SUBMISSION
        # =============================================================================

        if submitted:
            # Validate required fields
            if not all(
                [new_company_name, new_sales_contact_name, new_sales_contact_email]
            ):
                st.error("Please fill in all required fields (marked with *)")
            else:
                # =============================================================================
                # AUDIT TRAIL CREATION
                # =============================================================================

                # Create timestamp for audit trail
                audit_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                old_data = selected_lead["data"].get("old_data", {})
                changed = False

                # Calculate new lead score using weighted algorithm
                new_lead_score = lead_score_weighted(
                    new_last_deal_size,
                    new_lead_status,
                    new_pipeline_stage,
                    new_crm_activity,
                )

                # Define all fields to check for changes
                # Format: field_name: (new_value, old_value)
                fields_to_check = {
                    "company_name": (new_company_name, sales_lead.get("company_name")),
                    "primary_market_region": (
                        new_market_region,
                        sales_lead.get("primary_market_region"),
                    ),
                    "market_cap_usd": (
                        new_market_cap,
                        sales_lead.get("market_cap_usd"),
                    ),
                    "annual_sales_usd": (
                        new_annual_sales,
                        sales_lead.get("annual_sales_usd"),
                    ),
                    "number_of_customers": (
                        new_num_customers,
                        sales_lead.get("number_of_customers"),
                    ),
                    "sales_contact_name": (
                        new_sales_contact_name,
                        sales_lead.get("sales_contact_name"),
                    ),
                    "sales_contact_email": (
                        new_sales_contact_email,
                        sales_lead.get("sales_contact_email"),
                    ),
                    "date_of_last_contact": (
                        new_last_contact_date.strftime("%Y-%m-%d"),
                        sales_lead.get("date_of_last_contact"),
                    ),
                    "lead_source": (new_lead_source, sales_lead.get("lead_source")),
                    "crm_activity_flag": (
                        new_crm_activity,
                        sales_lead.get("crm_activity_flag"),
                    ),
                    "lead_status": (new_lead_status, sales_lead.get("lead_status")),
                    "pipeline_stage": (
                        new_pipeline_stage,
                        sales_lead.get("pipeline_stage"),
                    ),
                    "last_deal_size_usd": (
                        new_last_deal_size,
                        sales_lead.get("last_deal_size_usd"),
                    ),
                    "lead_score": (new_lead_score, sales_lead.get("lead_score")),
                    "notes": (new_notes, sales_lead.get("notes")),
                    "quarter": (new_quarter, sales_lead.get("quarter")),
                }

                # =============================================================================
                # AUDIT TRAIL PROCESSING
                # =============================================================================

                # Check each field for changes and create audit trail entries
                for field_name, (new_value, old_value) in fields_to_check.items():
                    if new_value != old_value:
                        # Record the old value and timestamp for audit trail
                        old_data[field_name] = {
                            "old_value": old_value,
                            "audit_date": audit_date,
                        }
                        changed = True

                # =============================================================================
                # DATABASE UPDATE LOGIC
                # =============================================================================

                if changed:
                    # Create updated document with all new values
                    updated_doc = selected_lead["data"].copy()

                    # Update all sales lead fields with new values
                    updated_doc["sales_lead"]["company_name"] = new_company_name
                    updated_doc["sales_lead"][
                        "primary_market_region"
                    ] = new_market_region
                    updated_doc["sales_lead"]["market_cap_usd"] = new_market_cap
                    updated_doc["sales_lead"]["annual_sales_usd"] = new_annual_sales
                    updated_doc["sales_lead"]["number_of_customers"] = new_num_customers
                    updated_doc["sales_lead"][
                        "sales_contact_name"
                    ] = new_sales_contact_name
                    updated_doc["sales_lead"][
                        "sales_contact_email"
                    ] = new_sales_contact_email
                    updated_doc["sales_lead"]["date_of_last_contact"] = (
                        new_last_contact_date.strftime("%Y-%m-%d")
                    )
                    updated_doc["sales_lead"]["lead_source"] = new_lead_source
                    updated_doc["sales_lead"]["crm_activity_flag"] = new_crm_activity
                    updated_doc["sales_lead"]["lead_status"] = new_lead_status
                    updated_doc["sales_lead"]["pipeline_stage"] = new_pipeline_stage
                    updated_doc["sales_lead"]["last_deal_size_usd"] = new_last_deal_size
                    updated_doc["sales_lead"]["lead_score"] = new_lead_score
                    updated_doc["sales_lead"]["notes"] = new_notes
                    updated_doc["sales_lead"]["quarter"] = new_quarter

                    # Update high priority flag based on new lead score (only for positive scores)
                    updated_doc["sales_lead"]["high_priority_flag"] = (
                        new_lead_score is not None and new_lead_score >= 80
                    )

                    # Preserve audit trail data
                    updated_doc["old_data"] = old_data

                    # Attempt to update the document in the database
                    try:
                        collection.upsert(selected_lead["id"], updated_doc)
                        st.success("Lead updated successfully!")
                    except Exception as e:
                        st.error(f"Error updating lead: {e}")
                else:
                    # No changes detected, inform user
                    st.info("No changes detected.")


def create_new_lead_page(collection):
    """
    Display the create new lead page with navigation.

    This function handles the create lead workflow by displaying
    the page header and navigation, then delegating to the form handler.

    Args:
        collection: Couchbase collection object
    """
    st.header("Create New Sales Lead")

    # Back button to return to main leads view
    if st.button("Back to View All Leads"):
        del st.session_state["show_create_form"]
        st.rerun()

    # Delegate to form handler
    create_new_lead_form(collection)


def create_new_lead_form(collection):
    """
    Display and handle the create new lead form.

    This function creates a comprehensive form for entering new lead data,
    validates the input, calculates lead score, and saves to the database.

    Args:
        collection: Couchbase collection object
    """
    with st.form("create_lead_form"):
        # =============================================================================
        # CREATE FORM - COMPANY INFORMATION SECTION
        # =============================================================================

        st.subheader("Company Information")
        col1, col2 = st.columns(2)

        # Left column: Company details and financial information
        with col1:
            # Required field: Company name
            company_name = st.text_input(
                "Company Name *", placeholder="Enter company name"
            )

            # Required field: Market region selection
            market_region = st.selectbox(
                "Primary Market Region *",
                MARKET_REGIONS,
            )

            # Required field: Market capitalization
            market_cap = st.number_input(
                "Market Cap (USD) *", min_value=0, value=0, step=1000000
            )

            # Required field: Annual sales revenue
            annual_sales = st.number_input(
                "Annual Sales (USD) *", min_value=0, value=0, step=1000000
            )

            # Optional field: Number of customers
            num_customers = st.number_input(
                "Number of Customers", min_value=0, value=0, step=100
            )

        # Right column: Contact information and lead source
        with col2:
            # Required field: Sales contact name
            sales_contact_name = st.text_input(
                "Sales Contact Name *", placeholder="Enter contact name"
            )

            # Required field: Sales contact email
            sales_contact_email = st.text_input(
                "Sales Contact Email *", placeholder="Enter email address"
            )

            # Date of last contact (defaults to current date)
            last_contact_date = st.date_input(
                "Date of Last Contact", value=datetime.now().date()
            )

            # Lead source selection
            lead_source = st.selectbox(
                "Lead Source",
                LEAD_SOURCES,
            )

            # CRM activity flag
            crm_activity = st.checkbox("CRM Activity Flag", value=False)

        # =============================================================================
        # CREATE FORM - LEAD STATUS & PIPELINE SECTION
        # =============================================================================

        st.subheader("Lead Status & Pipeline")
        col1, col2 = st.columns(2)

        # Left column: Lead status and pipeline stage
        with col1:
            # Required field: Lead status
            lead_status = st.selectbox(
                "Lead Status *",
                LEAD_STATUSES,
            )

            # Required field: Pipeline stage
            pipeline_stage = st.selectbox(
                "Pipeline Stage *",
                PIPELINE_STAGES,
            )

        # Right column: Deal size and additional information
        with col2:
            # Required field: Last deal size
            last_deal_size = st.number_input(
                "Deal Size (USD) *", min_value=0, value=0, step=10000
            )

            # Optional field: Notes
            notes = st.text_area("Notes", placeholder="Enter any additional notes")

            # Quarter selection
            quarter = st.selectbox(
                "Quarter", ["Q1 2025", "Q2 2025", "Q3 2025", "Q4 2025"]
            )

        # =============================================================================
        # FORM SUBMISSION BUTTONS
        # =============================================================================

        col_save, col_cancel = st.columns(2)
        with col_save:
            submitted = st.form_submit_button("Create Lead", type="primary")
        with col_cancel:
            cancel = st.form_submit_button("Cancel")

        # Handle form cancellation
        if cancel:
            del st.session_state["show_create_form"]
            st.rerun()

        # =============================================================================
        # FORM VALIDATION AND LEAD CREATION
        # =============================================================================

        if submitted:
            # Validate required fields
            if not all([company_name, sales_contact_name, sales_contact_email]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                # =============================================================================
                # LEAD SCORE CALCULATION
                # =============================================================================

                # Calculate lead score using weighted algorithm
                lead_score = lead_score_weighted(
                    last_deal_size, lead_status, pipeline_stage, crm_activity
                )

                # =============================================================================
                # LEAD DOCUMENT CREATION
                # =============================================================================

                # Generate unique lead ID and document key
                lead_id = str(uuid.uuid4())
                doc_key = f"lead::{lead_id}"

                # Create comprehensive lead document
                lead_doc = {
                    "lead_id": lead_id,
                    "sales_lead": {
                        "company_name": company_name,
                        "quarter": quarter,
                        "market_cap_usd": market_cap,
                        "annual_sales_usd": annual_sales,
                        "number_of_customers": num_customers,
                        "primary_market_region": market_region,
                        "sales_contact_name": sales_contact_name,
                        "sales_contact_email": sales_contact_email,
                        "date_of_last_contact": last_contact_date.strftime("%Y-%m-%d"),
                        "lead_status": lead_status,
                        "pipeline_stage": pipeline_stage,
                        "last_deal_size_usd": last_deal_size,
                        "lead_source": lead_source,
                        "notes": notes,
                        "crm_activity_flag": crm_activity,
                        "lead_score": lead_score,
                        "high_priority_flag": lead_score is not None and lead_score >= 80,  # Auto-set based on score
                    },
                }

                # =============================================================================
                # DATABASE INSERTION
                # =============================================================================

                try:
                    # Insert new lead document into database
                    collection.insert(doc_key, lead_doc)
                    st.success(f"Lead created successfully! Lead ID: {lead_id}")

                    # Navigate back to main page after successful creation
                    del st.session_state["show_create_form"]
                    st.rerun()

                except Exception as e:
                    st.error(f"Error creating lead: {e}")


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Start the Streamlit application
    main()
