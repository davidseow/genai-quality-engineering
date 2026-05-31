import os
from .client import triage_ticket
from .models import SupportTicket

ticket = SupportTicket(
    subject="Order hasn't arrived — been 3 weeks!",
    body=(
        "I placed order #98234 on the 1st of May. It is now the 22nd and "
        "nothing has arrived. I have a birthday event this weekend."
    ),
)

result = triage_ticket(ticket, project_id=os.environ["GCP_PROJECT_ID"])
print(f"Urgency : {result.urgency.value}")
print(f"Topic   : {result.topic}")
print(f"Reply   : {result.reply}")
