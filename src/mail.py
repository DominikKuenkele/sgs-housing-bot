import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@dataclass
class SMTPServerConfig:
    server: str
    port: int
    user: str
    password: str


class Mail:
    def __init__(self, smtp_server_config: SMTPServerConfig) -> None:
        self.smtp_server_config = smtp_server_config

    def send(self, subject: str, sender: str, receivers: list[str], content: str):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(receivers)
        message["Date"] = formatdate(localtime=True)
        message.set_content(content)

        log.info("contacting SMTP server...")

        with smtplib.SMTP_SSL(
            self.smtp_server_config.server, self.smtp_server_config.port
        ) as smtp:
            smtp.login(self.smtp_server_config.user, self.smtp_server_config.password)
            log.info("Logged into SMTP server.")
            smtp.send_message(message)
            log.info("Message sent.")
