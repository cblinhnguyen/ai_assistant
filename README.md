# AI Sales Lead Assistant

An intelligent sales lead management system that combines a **Streamlit web interface** for lead management with **AI-powered analysis** using **Flask**, **AWS Bedrock**, and **Couchbase Eventing**.

## What This Project Does

This comprehensive sales lead management solution provides:

**🎯 Lead Management Interface (Streamlit)**
- Create new sales leads with detailed company information
- Edit and update existing lead records
- View lead summaries and AI-generated recommendations
- Manage lead status, pipeline stages, and priority levels

**🤖 AI-Powered Analysis (Flask + AWS Bedrock)**
- Automatically generates executive summaries for sales leads
- Creates actionable recommendations with 4-5 specific next steps
- Analyzes lead changes and provides strategic insights
- Formats financial data (market cap, revenue, deal sizes) professionally

**🔄 Real-Time Processing (Couchbase Eventing)**
- Monitors sales lead updates in real-time
- Triggers AI analysis automatically when leads are modified
- Preserves historical data to track lead progression
- Prevents infinite processing loops with smart flagging

**💾 Data Persistence (Couchbase)**
- Stores all lead information, summaries, and recommendations
- Maintains complete audit trail of lead changes
- Enables historical analysis and trend tracking
- Supports enterprise-scale data management

The system seamlessly integrates lead management workflows with AI-powered insights, helping sales teams make data-driven decisions and advance leads through the sales pipeline more effectively.

---

## 🌟 Features

- Generates 2–3 sentence **executive summaries** for sales leads
- Creates actionable **recommendations** with 4–5 next steps
- Preserves `old_data` to avoid overwriting historical information
- Formats all USD amounts (e.g., `$1,234,567`)
- Logs both Flask and Eventing activity for traceability

---

## 🧰 Dependencies
- Python 3.13+
- Flask
- Couchbase Python SDK
- Boto3 (AWS SDK for Python)
- re (regular expressions)
- json
- traceback

## 🚀 How to Run the Applications

### Setup Instructions

#### 1. Create and Activate Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Create Environment Configuration
Create a `.env` file in the same directory as `app.py` with the following environment variables:

```env
# Couchbase Configuration
COUCHBASE_CONNSTR=<your_couchbase_connection_string>
COUCHBASE_USERNAME=<your_couchbase_username>
COUCHBASE_PASSWORD=<your_couchbase_password>
COUCHBASE_BUCKET=sales_lead
COUCHBASE_SCOPE=_default
COUCHBASE_COLLECTION=_default

# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=<your_aws_access_key>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
AWS_REGION=us-east-1
```

#### 4. Deploy and Activate Couchbase Eventing Function
1. Open Couchbase Web Console
2. Navigate to **Eventing** section
3. Deploy the `AI_Assistant.json` eventing function
4. **Activate** the function to enable automatic processing

#### 5. Run the Applications

**Terminal 1 - Flask API Server:**
```bash
python app.py
```
The Flask server will run on `http://localhost:5001`

**Terminal 2 - Streamlit Web Interface:**
```bash
streamlit run streamlit_app.py
```
The Streamlit app will run on `http://localhost:8501`

### Important Notes
- Both applications must be running simultaneously for full functionality
- The Flask API handles the AI processing and Couchbase integration
- The Streamlit app provides the web interface for viewing and managing sales leads
- Ensure the `AI_Assistant.json` eventing function is **activated** in Couchbase for automatic processing
- The eventing function will automatically trigger when sales lead documents are updated in Couchbase
