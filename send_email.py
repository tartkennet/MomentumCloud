import os, smtplib, ssl
from email.message import EmailMessage

TO = os.environ["TO_EMAIL"]
FROM = os.environ["FROM_EMAIL"]
HOST = os.environ["SMTP_HOST"]
PORT = int(os.environ["SMTP_PORT"])
USER = os.environ["SMTP_USER"]
PWD  = os.environ["SMTP_PASS"]

def main():
    msg = EmailMessage()
    msg["Subject"] = "Momentum.xlsx – daglig uppdatering"
    msg["From"] = FROM
    msg["To"] = TO
    msg.set_content("Här är dagens uppdaterade Momentum.xlsx (incremental fetch).")

    with open("Momentum.xlsx", "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application",
                       subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       filename="Momentum.xlsx")

    context = ssl.create_default_context()
    with smtplib.SMTP(HOST, PORT) as s:
        s.starttls(context=context)
        s.login(USER, PWD)
        s.send_message(msg)

if __name__ == "__main__":
    main()
