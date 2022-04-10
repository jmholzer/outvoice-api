from typing import Dict, Optional
import boto3
from botocore.exceptions import ClientError
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from utility import generate_absolute_path, format_uk_date
import os


class EmailManager:
    """
    Manage building and sending emails with attachments to clients on behalf
    of companies, using an email enabled for use with AWS SES (Amazon Web
    Services Simple Email Service)

    Attributes:
        ses_client: the interface to the AWS SES API in Python.
        sender: a dict containing the name and client-facing email of the
            company controlling the outvoice instance.
    """

    def __init__(self, invoice_meta: Dict[str, str]):
        # Set object values with function calls
        self.ses_client = self.init_ses_client()
        # Read the name of the company controlling the outvoice instance
        self.sender = self.init_sender()
        # Initialise a dict containing meta data for the invoice being sent
        self.invoice_meta = invoice_meta
        # Initialise the email 'fields' (subject, html body, )
        self.fields = self.init_fields()

    def init_ses_client(self):
        """
        Returns an interface to SES.
        """
        return boto3.client("ses", region_name="eu-central-1")

    def init_sender(self) -> None:
        """
        Initialises a dict containing information on the sender
        (name, email address) from a file representing the company controlling
        the instance of outvoice.
        """
        company_file_path = generate_absolute_path("/resources/company/company.json")
        with open(company_file_path) as company_file:
            return json.load(company_file)

    def init_fields(self) -> Dict[str, str]:
        """
        Initialise the 'fields' of the email; subject, html body, text body and sender.
        """
        fields = self.read_fields()
        self.format_body(fields)
        self.format_subject(fields)
        self.format_sender(fields)
        return fields

    def read_fields(self) -> str:
        """
        Reads the html body, subject and sender from a file with fixed,
        predetermined location into a dictionary.
        """
        fields = {"text_body": "", "html_body": "", "subject": "", "sender": ""}
        for field in fields:
            file_path = generate_absolute_path(f"/resources/email/{field}")
            with open(file_path, "r") as file:
                fields[field] = file.read()
        return fields

    def format_body(self, fields: Dict[str, str]) -> None:
        """
        Formats the supplied email html body with values specific to the
        invoice being generated.

        Arguments:
        fields -- a dict containing the contents of the email.
        invoice_meta -- a dict containing the meta data on the invoice
            necessary to address the client.
        """
        for body_type in ["text_body", "html_body"]:
            fields[body_type] = fields[body_type].format(
                first_name=self.invoice_meta["first_name"],
                sender=self.sender["company_name"],
                invoice_date=format_uk_date(self.invoice_meta["invoice_date"]),
            )

    def format_subject(self, fields: Dict[str, str]) -> None:
        """
        Formats the supplied email subject line with values specific to the
        invoice being generated.

        Arguments:
        fields -- a dict containing the contents of the email.
        """
        fields["subject"] = fields["subject"].format(sender=self.sender["company_name"])

    def format_sender(self, fields: Dict[str, str]) -> None:
        """
        Formats the supplied email sender line with values specific to the
        invoice being generated.

        Arguments:
        fields -- a dict containing the contents of the email.
        """
        fields["sender"] = fields["sender"].format(
            sender=self.sender["company_name"], email=self.sender["email"]
        )

    def construct_email_meta(self, message: MIMEMultipart) -> None:
        """
        Adds the 'subject', 'to' and 'from' metadata to a MIME multipart email
        message.

        Arguments:
        message -- the MIME multipart message to add metadata to.
        fields -- a dictionary containing the metadata.
        """
        message["Subject"] = self.fields["subject"]
        message["From"] = self.fields["sender"]
        message["To"] = self.invoice_meta["email_address"]

    def construct_email(self, invoice_file_path: str):
        """
        Creates a multipart MIME message with a subject, html message body and
        attached invoice, ready to be sent by EmailManager.send_email.

        Arguments:
        invoice_meta: meta data on the invoice being generated.
        invoice_file_path: absolute path of the invoice to be attached.
        """
        message = MIMEMultipart("mixed")
        self.construct_email_meta(message)
        body = MIMEMultipart("alternative")
        body.attach(MIMEText(self.fields["html_body"], "html", "utf-8"))
        body.attach(MIMEText(self.fields["text_body"], "text", "utf-8"))
        message.attach(body)
        attachment = MIMEApplication(open(invoice_file_path, "rb").read())
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(invoice_file_path),
        )
        message.attach(attachment)
        return message

    def send_email(
        self, message: MIMEMultipart, cc_recipient: Optional[str] = ""
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
                Source=self.sender["email"],
                Destinations=[self.invoice_meta["email_address"]],
                RawMessage={"Data": message.as_string()},
            )
            if "MessageId" in response:
                return True
        except ClientError as e:
            print(e)
            return False
