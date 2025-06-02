import os
import json
import requests
from dotenv import load_dotenv
from langchain.agents import Tool, initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
import smtplib

load_dotenv()

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL")

def call_forecast_api(client_name):
    url = f"{FASTAPI_BASE_URL}/forecast"
    payload = {"Client": client_name}
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API call failed with status {response.status_code}: {response.text}")

# ---- Email Utility ----
def send_email_with_attachment(subject, body_text):
    sender_email = os.getenv("GMAIL_EMAIL")
    receiver_email = os.getenv("TO_EMAIL")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    # Email body
    body_text_html = body_text.replace('\n', '<br>')

    html_body = f"""
    <html>
        <body>
            <h2>📊 Margin Call Forecast Summary</h2>
            <p>{body_text_html}</p>
            <p>Regards,<br>Margin Call Agent</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html"))

    # ✅ Use SMTP_SSL
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)

    print("✅ Email sent successfully via Gmail!")

# ---- Agent Task ----
def run_agent_for_client(client_name):
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_CHAT_API_VERSION"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        temperature=0,
    )

    forecast_tool = Tool(
        name="Forecast Tool",
        func=lambda client_name: call_forecast_api(client_name),
        description="Calls the forecast API to get 3-day margin call forecast along with the confidence score for a client."
    )

    tools = [forecast_tool]

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # Task Prompt
    task_prompt = (
        f"I need to use the Forecast Tool to get the 3-day margin call forecast along with the confidence score for '{client_name}'."
    )

    return agent.run(task_prompt)

# ---- Main ----
if __name__ == "__main__":
    client = input("Enter Client Name: ")

    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    # Run agent
    summary = run_agent_for_client(client)

    # Save Text Report
    text_file_path = os.path.join(reports_dir, f"{client}_forecast.txt")
    
    with open(text_file_path, "w") as f:
        f.write(summary)

    print("✅ Files created in reports/ folder.")

    # Send Email
    subject = f"📧 Margin Call Forecast Report for {client}"

    send_email_with_attachment(subject, summary)