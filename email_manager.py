from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText
from typing import *
import smtplib

class GmailManager:

    @staticmethod 
    def __init_mime_container(receiver   : str, 
                              sender     : str, 
                              subject    : str, 
                              content    : str) -> MIMEMultipart:
        
        container = MIMEMultipart()
        container["subject"] = subject
        container["from"   ] = sender
        container["to"     ] = receiver
        container.attach(MIMEText(content))
        return container

    def __init__(self, account : str, password : str) -> None:

        assert isinstance(account, str)
        
        assert isinstance(password, str)

        self.credentials = (account, password)

    def send(self, receiver : str, subject : str, body : str) -> bool:

        assert isinstance(receiver, str)

        assert isinstance(subject, str)

        assert isinstance(body, str)

        with smtplib.SMTP(host = "smtp.gmail.com", port = "587") as smtp:

            try:

                smtp.ehlo()
                smtp.starttls()
                smtp.login(*self.credentials)
                smtp.send_message(self.__init_mime_container(
                    receiver, self.credentials[0], subject, body)
                )

            except (KeyboardInterrupt):

                raise 

            except (Exception):

                return False 

            return True 