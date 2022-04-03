from typing import Dict
import boto3
from botocore.exceptions import ClientError
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utility import generate_absolute_path

class EmailManager():
    """
    Manage building and sending emails with attachments to clients on behalf
    of companies, using an email enabled for use with AWS SES (Amazon Web
    Services Simple Email Service)

    Attributes:
        ses_client: the interface to the AWS SES API in Python.
        sender: a dict containing the name and client-facing email of the
            company controlling the outvoice instance.
    """

    def __init__(self):
        # Set object values with function calls
        self.ses_client = self.init_ses_client()
        # Read the name of the company controlling the outvoice instance
        self.sender = self.init_sender(self)

    def init_ses_client(self):
        return boto3.client('ses', region_name="eu-central-1")

    def init_sender(self) -> None:
        """
        Initialises a dict containing information on the sender
        (name, email address) from a file representing the company controlling
        the instance of outvoice.
        """
        company_file_path = generate_absolute_path("/resources/company/company.json")
        with open(company_file_path) as company_file:
            return json.load(company_file)

    def read_body(self) -> str:
        """
        Reads the html body from a file with fixed, predetermined location.
        """
        html_file_path = generate_absolute_path("/resources/email/body.html")
        with open(html_file_path, "r") as html_file:
            return html_file.read()

    def format_body(self, html_body: str, invoice_meta: dict) -> str:
        """
        Formats the supplied email html body with values specific to the 

        Arguments:
        html_body -- a string containing the html body of the email.
        invoice_meta -- a dict containing the meta data on the invoice
            necessary to address the client.
        """
        html_body.format(
            first_name=invoice_meta["first_name"],
            sender=self.sender["company_name"],
            invoice_date=invoice_meta["invoice_date"],
        )
        return html_body

    def construct_email(self, invoice_file_path: str):
        """
        Creates a multipart MIME message with a subject, html message body and
        attached invoice, ready to be sent by EmailManager.send_email.

        Arguments:
        invoice_file_path: absolute path of the invoice to be attached.
        """
        message = MIMEMultipart("mixed")
        #message["Subject"] = 

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
    
    
