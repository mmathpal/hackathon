import logging
import os
import os.path
import json
import requests
import azure.functions as func
from langchain.agents import Tool, initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

# ✅ Utility to call forecast API
def call_forecast_api(client_name):
    fastapi_base_url = os.getenv("FASTAPI_BASE_URL")
    if not fastapi_base_url:
        raise ValueError("FASTAPI_BASE_URL not set in environment variables")

    url = f"{fastapi_base_url}/forecast"
    payload = {"Client": client_name}
    logging.info(f"Calling Forecast API at {url} with payload: {payload}")

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API call failed with status {response.status_code}: {response.text}")

# ✅ Utility to send email
def send_email_with_attachment(receiver_email, subject, body_text, json_file_path, text_file_path):
    sender_email = os.getenv("GMAIL_EMAIL")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))

    if not sender_email or not sender_password:
        raise ValueError("GMAIL_EMAIL and/or GMAIL_APP_PASSWORD not set in environment variables")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

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

    with open(json_file_path, "r") as f:
        mime_json = MIMEText(f.read(), "json")
        mime_json.add_header("Content-Disposition", "attachment", filename=os.path.basename(json_file_path))
        msg.attach(mime_json)

    with open(text_file_path, "r") as f:
        mime_text = MIMEText(f.read(), "plain")
        mime_text.add_header("Content-Disposition", "attachment", filename=os.path.basename(text_file_path))
        msg.attach(mime_text)

    logging.info("Connecting to Gmail SMTP server...")
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)

    logging.info("✅ Email sent successfully!")

# ✅ Agent runner
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

    task_prompt = (
        f"I need to use the Forecast Tool to get the 3-day margin call forecast for '{client_name}'."
    )

    return agent.run(task_prompt)

# ✅ Main Function - No POST body required anymore
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('🔔 Azure Function HTTP Triggered')

    try:
        # Basic Health Check (Optional)
        if req.method == "GET":
            return func.HttpResponse("✅ Margin Forecast Function is running!", status_code=200)

        # Read client name and receiver email from environment
        client_name = os.getenv("CLIENT_NAME")
        receiver_email = os.getenv("RECEIVER_EMAIL")

        if not client_name or not receiver_email:
            return func.HttpResponse("CLIENT_NAME or RECEIVER_EMAIL not set in environment variables.", status_code=500)

        logging.info(f"Running forecast for Client: {client_name}, sending report to: {receiver_email}")

        reports_dir = "/tmp/reports"
        os.makedirs(reports_dir, exist_ok=True)

        # Run Agent
        summary = run_agent_for_client(client_name)

        # Save Reports
        json_data_path = os.path.join(reports_dir, f"{client_name}_forecast.json")
        text_file_path = os.path.join(reports_dir, f"{client_name}_forecast.txt")

        forecast_data = call_forecast_api(client_name)

        with open(json_data_path, "w") as f:
            json.dump(forecast_data, f, indent=4)

        with open(text_file_path, "w") as f:
            f.write(summary)

        logging.info("✅ Files created successfully.")

        subject = f"📧 Margin Call Forecast Report for {client_name}"
        send_email_with_attachment(receiver_email, subject, summary, json_data_path, text_file_path)

        logging.info(f"✅ Email sent to {receiver_email}.")
        return func.HttpResponse(f"✅ Forecast Report for {client_name} sent to {receiver_email}", status_code=200)

    except Exception as e:
        logging.error(f"❌ Error occurred: {str(e)}", exc_info=True)
        return func.HttpResponse(f"❌ Error: {str(e)}", status_code=500)