from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import inspect
from typing import Optional
from pydantic import BaseModel
from pdf import generate_invoice
from local_print import print_document
from db import SqliteConnector
from utility import snake_to_camel
from copy import deepcopy
from requests import post


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
    firstName: str
    lastName: str
    invoiceDate: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    postCode: str
    receiptAmount: str
    receiptNumber: str
    receiptDescription: str
    method: str


class ClientForm(BaseModel):
    firstName: str
    lastName: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    postCode: str
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
    boring = dir(type('dummy', (BaseModel,), {}))
    return [
        item[0]
        for item in inspect.getmembers(request_cls)
        if item[0] not in boring
    ]


def download_invoice(request_body: dict) -> FileResponse:
    """
    Returns a pdf file of an invoice.

    Arguments:
    request_body -- information on client submitted by caller.
    """

    invoice = generate_invoice(request_body)
    return FileResponse(invoice,
        media_type="application/pdf",
    )


def print_invoice(request_body: dict) -> None:
    """
    Send a pdf of an invoice to a printer attached
    to the linux computer running the api process.

    Arguments:
    request_body -- information on client submitted by caller.
    """
    invoice_file_path = generate_invoice(request_body)
    print_document(invoice_file_path)


def add_client_using_invoice(request_body: dict) -> None:
    """
    Helper function for converting an invoice generation
    request to a request to add user to the client database
    using the add_client() function.

    Arguments:
    client_invoice_form -- information on client submitted by caller.
    """
    request_body_copy = deepcopy(request_body)
    del request_body_copy["receiptAmount"]
    del request_body_copy["receiptNumber"]
    del request_body_copy["receiptDescription"]
    request_body_copy["method"] = "add"
    add_client(request_body_copy)


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
        "print": print_invoice
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
        tuple(request_body[snake_to_camel(key)] for key in 
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
        tuple(request_body[snake_to_camel(key)] for key in 
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
        request_body["firstName"],
        request_body["lastName"]
    )
    
    return([
        {snake_to_camel(key): row[key] for key in row.keys()}
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