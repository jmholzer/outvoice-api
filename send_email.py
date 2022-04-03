from typing import Dict
import boto3
from botocore.exceptions import ClientError
import json
from email.mime.multipart import MIMEMultipart
from utility import generate_absolute_path

class EmailManager():
    """
    TODO: Docstring 
    """

    def __init__(self):
        # Set object values with function calls
        self.init_ses_client()
        # Read the name of the company controlling the outvoice instance
        self.get_sender(self)

    def init_ses_client(self):
        self.ses_client = boto3.client('ses', region_name="eu-central-1")

    def get_sender(self) -> None:
        """
        Initialises a dict containing information on the sender
        (name, email address) from a file representing the
        company controlling the instance of outvoice.
        """
        company_file_path = generate_absolute_path("/company_information/company.json")
        with open(company_file_path) as company_file:
            self.sender = json.load(company_file)

    def send_email(
            self,
            recipient: str,
            cc_recipient: str,
            message: MIMEMultipart
        ) -> bool:
        """
        Sends a MIME multipart email with a subject, html message body and
        attached invoice, returns True to indicate success, False to indicate
        failure.

        Arguments:
        recipient -- email address of the primary recipient.
        cc_recipient -- email address of the cc recipient.
        message -- the multipart MIME email to send.
        """
        try:
            response = self.ses_client.send_raw_email(
                Source=self.sender.email,
                Destinations=[
                    recipient
                ],
                RawMessage={
                    'Data': message.as_string()
                }
            )
            if "MessageId" in response:
                return True
        except ClientError as e:
            return False