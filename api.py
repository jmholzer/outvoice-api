from urllib import request
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import inspect
from typing import Optional, List, Dict, Union
from pydantic import BaseModel
from pdf import generate_invoice
from db import SqliteConnector
from copy import deepcopy
from mailer import EmailManager

app = FastAPI()


origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://outvoice.com",
    "http://www.outvoice.com"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


class InvoiceForm(BaseModel):
    first_name: str
    last_name: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    post_code: str
    invoice_number: str
    invoice_date: str
    pay_date: str
    line_items: List[Dict[str, str]]
    tax: str
    subtotal: str
    email_address: str
    cc_email_address: str
    method: str

class ClientForm(BaseModel):
    first_name: str
    last_name: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    post_code: str
    method: str


# The name and order of columns in the client database
client_db_row_schema = [
    "first_name",
    "last_name",
    "address_line_1",
    "address_line_2",
    "city",
    "post_code"
]


def get_request_fields(request_cls):
    dummy_base_model = dir(type('dummy', (BaseModel,), {}))
    return [
        item[0]
        for item in inspect.getmembers(request_cls)
        if item[0] not in dummy_base_model
    ]


def strip_emails_from_request(request_body: dict) -> FileResponse:
    """
    Deletes the key-value pairs for email addresses, which are not
    required in order to generate in invoice.

    Arguments:
    request_body -- information on client submitted by caller.
    """
    del request_body["email_address"]
    del request_body["cc_email_address"]


def add_client_using_invoice(request_body: dict) -> None:
    """
    Helper function for converting an invoice generation
    request to a request to add user to the client database
    using the add_client() function.

    Arguments:
    client_invoice_form -- information on client submitted by caller.
    """
    request_body_copy = deepcopy(request_body)
    del request_body_copy["invoice_number"]
    request_body_copy["method"] = "add"
    add_client(request_body_copy)


def download_invoice(request_body: dict) -> FileResponse:
    """
    Returns a pdf file of an invoice.

    Arguments:
    request_body -- information on client submitted by caller.
    """
    strip_emails_from_request(request_body)
    invoice_file_path = generate_invoice(request_body)
    return FileResponse(invoice_file_path,
        media_type="application/pdf",
    )


def email_invoice(request_body: dict) -> None:
    invoice_meta = {
        "first_name": request_body["first_name"],
        "email_address": request_body["email_address"],
        "invoice_date": request_body["invoice_date"]
    }
    email_manager = EmailManager(invoice_meta)
    strip_emails_from_request(request_body)
    invoice_file_path = generate_invoice(request_body)
    message = email_manager.construct_email(invoice_file_path)
    success = email_manager.send_email(message)
    return {"success": success}


@app.post("/invoice")
async def root(client_invoice_form: InvoiceForm):
    """
    API endpoint for the 'invoice' resource.

    Arguments:
    client_invoice_form -- information on client submitted by caller.
    """
    
    """
    Create a dictionary out of client_invoice_form
    as this keeps pdf.py independent of BaseModel (fastapi)
    """
    request_fields = get_request_fields(client_invoice_form)
    request_body = {
        request_field: getattr(client_invoice_form, request_field)
        for request_field in request_fields
    }

    add_client_using_invoice(request_body)

    method_routes = {
        "download": download_invoice,
        "email": email_invoice
    }

    method = request_body["method"]
    del request_body["method"]
    return method_routes[method](request_body)


def add_client(request_body: dict) -> list:
    """
    Add a row matching the data in request_body into
    the address table in the client database.

    Arguments:
    request_body -- information on client to add
        submitted by the caller.
    """
    sqlite_connector = SqliteConnector("clients.db")
    sqlite_connector.enter_address(
        tuple(request_body[key] for key in 
            client_db_row_schema)
    )


def remove_client(request_body: dict):
    """
    Remove the row matching the data in request_body from
    the address table in the client database.

    Arguments:
    request_body -- information on client to remove
        submitted by the caller.
    """
    sqlite_connector = SqliteConnector("clients.db")
    result = sqlite_connector.remove_address(
        tuple(request_body[key] for key in 
            client_db_row_schema)
    )

    return {"success": True} if result else {"success": False}


def search_client(request_body: dict) -> list:
    """
    Searches the address table in the client database 
    for an address matching a given first and last name.
    Returns an array of dicts, each dict representing 
    a row of matching results.

    Arguments:
    request_body -- information on client to search for
        submitted by the caller.
    """
    sqlite_connector = SqliteConnector("clients.db")

    results = sqlite_connector.search_address(
        request_body["first_name"],
        request_body["last_name"]
    )
    
    return([
        {key: row[key] for key in row.keys()}
        for row in results
    ])


@app.post("/client")
async def root(client_action_form: ClientForm):
    """
    API endpoint for the 'client' resource.

    Arguments:
    client_action_form -- information on client to search for
        submitted by the caller.
    """

    request_fields = get_request_fields(client_action_form)
    request_body = {
        request_field: getattr(client_action_form, request_field)
        for request_field in request_fields
    }

    method_routes = {
        "add": add_client,
        "remove": remove_client,
        "search": search_client
    }

    method = request_body["method"]
    del request_body["method"]
    return method_routes[method](request_body)