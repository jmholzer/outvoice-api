from typing import Dict
import boto3
from botocore.exceptions import ClientError
import os
import json

class EmailManager():
    """
    TODO: Docstring 
    """
    def init_ses_client(self):
        self.ses_client = boto3.client('ses', region_name="eu-central-1")

    def generate_greeting(self):
        """
        Generates the greeting to use in an email based on the time of day
        (UK time zone).
        """
        pass

    def send_email(self):
        """
        Sends an email with a subject, html message body and invoice attachment.
        """
        pass

    def __init__(self, recipient_group):
        # Set object values by argument
        self.recipient_group = recipient_group 

        # Set object values with function calls
        self.init_ses_client()
