import logging
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class MailSendException(Exception):
    pass


@dataclass
class SMTPServerConfig:
    server: str
    port: int
    user: str
    password: str


class MailServer:
    def __init__(self, smtp_server_config: SMTPServerConfig) -> None:
        self.smtp_server_config = smtp_server_config
        self.registered_messages: list[EmailMessage] = []

    def register_message(self, subject: str, receiver: str, content: str):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.smtp_server_config.user
        message["To"] = receiver
        message["Date"] = formatdate(localtime=True)
        message.set_content(content)

        self.registered_messages.append(message)

    def send_all(self, attempts=1):
        while attempts > 0:
            try:
                log.info("contacting SMTP server...")

                with smtplib.SMTP_SSL(
                    self.smtp_server_config.server, self.smtp_server_config.port
                ) as smtp:
                    smtp.login(
                        self.smtp_server_config.user, self.smtp_server_config.password
                    )
                    log.info("Logged into SMTP server.")
                    log.info("sending %s messages...", len(self.registered_messages))
                    for message in self.registered_messages:
                        smtp.send_message(message)
                    log.info("Messages sent.")
                    break
            except smtplib.SMTPAuthenticationError:
                log.error(
                    "Failed to connect to server. Remaining attempts: %s", attempts - 1
                )
                attempts -= 1
                time.sleep(1)

        if attempts == 0:
            log.error("Failed to connect to the SMTP server.")
            raise MailSendException("Failed to connect to the SMTP server.")
