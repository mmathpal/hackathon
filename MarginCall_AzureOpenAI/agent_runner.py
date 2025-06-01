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
def send_email_with_attachment(receiver_email, subject, body_text, json_file_path, text_file_path):
    sender_email = os.getenv("GMAIL_EMAIL")
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
            <p>Attached are the detailed <b>JSON</b> and <b>Text</b> reports.</p>
            <p>Regards,<br>Margin Call Forecasting Agent 🤖</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html"))

    # Attach JSON file
    with open(json_file_path, "r") as f:
        mime_json = MIMEText(f.read(), "json")
        mime_json.add_header("Content-Disposition", "attachment", filename=os.path.basename(json_file_path))
        msg.attach(mime_json)

    # Attach Text file
    with open(text_file_path, "r") as f:
        mime_text = MIMEText(f.read(), "plain")
        mime_text.add_header("Content-Disposition", "attachment", filename=os.path.basename(text_file_path))
        msg.attach(mime_text)

    # ✅ Use SMTP_SSL
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)

    print("✅ Email sent successfully via Gmail SSL!")

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
        description="Calls the forecast API to get 3-day margin call forecast for a client."
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
        f"I need to use the Forecast Tool to get the 3-day margin call forecast for '{client_name}'."
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

    # Save JSON and Text Report
    json_data_path = os.path.join(reports_dir, f"{client}_forecast.json")
    text_file_path = os.path.join(reports_dir, f"{client}_forecast.txt")

    # Save forecast API data
    forecast_data = call_forecast_api(client)
    with open(json_data_path, "w") as f:
        json.dump(forecast_data, f, indent=4)

    # Save text summary
    with open(text_file_path, "w") as f:
        f.write(summary)

    print("✅ Files created in reports/ folder.")

    # Send Email
    receiver_email = input("Enter Receiver Email: ")
    subject = f"📧 Margin Call Forecast Report for {client}"

    send_email_with_attachment(receiver_email, subject, summary, json_data_path, text_file_path)