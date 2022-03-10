import io
from operator import inv
import os
from json import load
from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.pdf import PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfgen.textobject import PDFTextObject
from datetime import datetime
from copy import copy
from typing import List, Optional


pdfmetrics.registerFont(TTFont('OpenSans', 'OpenSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('OpenSans-Italic', 'OpenSans-Italic.ttf'))


def generate_absolute_path(relative_path: str) -> str:
    """
    Generate an absolute path to a file.

    Arguments:
    relative_path -- path relative to current script. 
    """
    path_to_script = os.path.dirname(os.path.abspath(__file__))
    return path_to_script + "/" + relative_path


def write_page_to_file(page: PageObject, output_file_path: str) -> None:
    """
    Save a single page as a PDF document.

    Arguments:
    page -- page to save as as PDF
    output_file_path -- absolute path to save PDF
    """
    output = PdfFileWriter()
    output.addPage(page)
    output_stream = open(output_file_path, "wb")
    output.write(output_stream)
    output_stream.close()


def read_first_page(input_file_path: str) -> PageObject:
    """
    Read the first page from an existing PDF document.

    Arguments:
    input_file_path -- absolute path to save PDF
    """
    in_ = PdfFileReader(open(input_file_path, "rb"))
    return in_.getPage(0)


def write_text_to_overlay(
        line: str,
        text: PDFTextObject,
        layout: dict,
        x_offset: Optional[float] = 0,
        y_offset: Optional[float] = 0
    ) -> None:
    """
    Write the text at the given position, with a given font and size. Modifies the
    passed PDFTextObject (text) in place and does not return a value.

    Arguments:
        line -- the line of text to to write.
        text -- the reportlab PDFTextObject object attached to the overlay canvas.
        layout -- a dict that contains the following fields:
            x_origin -- the x position (mm) to start the text at on the overlay.
            y_origin -- the y position (mm) to start the text at on the overlay.
            font -- the font to use for the text to write.
            size -- the size of the text to write.
    """
    x, y = layout["x_origin"] + x_offset, layout["y_origin"] + y_offset
    text.setFont(layout["font"], layout["size"])
    text.setTextOrigin(x * mm, y * mm)
    text.textLines(line)


def format_date(invoice_form: dict):
    """
    Convert date from the format received in the API call to
    a localised (British) date in-place.

    Arguments:
    invoice_form -- data about the client passed from
        the API end-point.
    """
    invoice_form["date"] = datetime.strptime(invoice_form["date"], "%Y-%m-%d").strftime("%d/%m/%Y")


def format_address_line(invoice_form: dict) -> str:
    """
    Add formatted address line to invoice_form in-place.

    Arguments:
    invoice_form -- data about the client passed from
        the API end-point.
    """
    invoice_form["address"] = (
        '\n'.join([
            invoice_form["first_name"] + ' ' + invoice_form["last_name"],
            invoice_form["address_line_1"],
            invoice_form.get("address_line_2", ""),
            invoice_form["city"],
            invoice_form["post_code"]
        ])
    )

def delete_unused_keys(invoice_form: dict) -> None:
    """
    Delete the keys (in-place) that are no longer used as 
    a result of generating formatted output strings.

    Arguments:
    invoice_form -- data about the client passed from
        the API end-point.
    """
    for key in [
        "first_name",
        "last_name",
        "address_line_1",
        "address_line_2",
        "city",
        "post_code"
    ]:
        del invoice_form[key]


def format_invoice_form_input(invoice_form: dict) -> None:
    """
    Makes in-place formatting changes to the dict containing
    the form input used to generate an invoice.

    Arguments:
    invoice_form -- data about the client passed from
        the API end-point.
    """
    format_address_line(invoice_form)
    format_date(invoice_form)
    delete_unused_keys(invoice_form)
    

def generate_invoice_overlay(
        invoice_form: dict,
        page_number: int,
        total_pages: int
    ) -> PageObject:
    """
    Create a PDF page (overlay) of invoice information
    that can be rendered on top of a blank invoice page.

    Arguments:
    invoice_form -- data about the client passed from
        the API end-point.
    """
    relative_layout_file_path = "layouts/default.json"
    layout_file_path = generate_absolute_path(relative_layout_file_path)
    with open(layout_file_path, "r") as layout_file:
        layout = load(layout_file)

    packet = io.BytesIO()
    invoice_layer_canvas = canvas.Canvas(packet)
    invoice_layer_canvas.setPageSize((A4))
    text = invoice_layer_canvas.beginText()
    
    write_text_to_overlay(invoice_form["receiptNumber"], text, layout["invoice_number"])

    date = format_date(invoice_form["invoice_date"])
    write_text_to_overlay(date, text, layout["date"])

    address = generate_invoice_address_line(invoice_form)
    write_text_to_overlay(address, text, layout["address"])

    line_item_offset = 0
    for line_item in invoice_form["line_items"]:
        for key in line_item:
            write_text_to_overlay(
                line_item[key],
                text,
                layout["line_item"][key],
                y_offset=line_item_offset
            )
        line_item_offset -= 5

    subtotal = invoice_form["subtotal"]
    text.setTextOrigin(167.5*mm, 117*mm)
    text.textLines(subtotal)

    tax = invoice_form["tax"]
    text.setTextOrigin(167.5*mm, 112*mm)
    text.textLines(tax)

    terms = "Pay on or before " + invoice_form["pay_date"]
    text.setTextOrigin(29.5*mm, 65*mm)
    text.textLines(terms)

    balance = invoice_form["balance"]
    text.setTextOrigin(159*mm, 85*mm)
    text.setFont('OpenSans', 14)
    text.textLines(balance)

    page_number_line = f"Page {page_number + 1} of {total_pages}"
    text.setTextOrigin(180*mm, 10*mm)
    text.setFont('OpenSans', 8)
    text.textLines(page_number_line)

    if page_number + 1 < total_pages:
        turn_over_line = "(Invoice continues overleaf)"
        text.setTextOrigin(159*mm, 80*mm)
        text.setFont('OpenSans-Italic', 8)
        text.textLines(turn_over_line)

    invoice_layer_canvas.drawText(text)
    invoice_layer_canvas.save()
    packet.seek(0)

    return PdfFileReader(packet).getPage(0)


def generate_line_item_lists(line_items: List[str]) -> List[List[str]]:
    """
    Takes a list of line items and splits it into
    a list of sublists, such that each sublist contains
    nine line items (enough to fill one invoice page).

    Arguments:
        line_items -- the list of line items to split into sublists
    """
    n = len(line_items)
    return [line_items[j:j+10] for j in range(0, n, 9)]


def generate_output_path(invoice_form: dict) -> str:
    """
    Takes in a dict representing the submitted form data
    and returns a string indicating where the generated
    pdf should be saved.

    Arguments:
        invoice_form -- the form data used to generate the invoice.
    """
    output_path = (
        "invoices/"
        + "_".join([
            invoice_form["first_name"],
            invoice_form["last_name"],
            invoice_form["invoice_date"],
            datetime.now().strftime("%H_%M_%S")
        ])
    )
    return generate_absolute_path(output_path)


def generate_invoice_pages(invoice_form: dict) -> List[PageObject]:
    """
    Returns a list of finished invoice pages (PageObjects).

    Arguments:
        invoice_form -- the form data used to generate the invoice.
    """
    page_template_path = generate_absolute_path("resources/invoice.pdf")
    line_item_lists = generate_line_item_lists(invoice_form["line_items"])
    invoice_pages = []

    total_pages = len(line_item_lists)
    for page_number, line_item_list in enumerate(line_item_lists):
        invoice_form_copy = copy(invoice_form)
        invoice_form_copy["line_items"] = line_item_list

        # Read the blank invoice
        invoice_page = read_first_page(page_template_path)
        # Generate an overlay using client data
        overlay = generate_invoice_overlay(invoice_form_copy, page_number, total_pages)
        # Merge the overlay on top of the blank invoice.
        invoice_page.mergePage(overlay)
        # Add page to the finished invoice.
        invoice_pages.append(invoice_page)
    
    return invoice_pages


def generate_invoice(invoice_form: dict) -> str:
    """
    Generate and save an invoice as a PDF.
    Returns absolute path of saved invoice.

    Arguments:
        invoice_form -- the form data used to generate the invoice.
    """
    output_path = generate_output_path(invoice_form)

    # invoice is an object that stores all generated invoice pages.
    invoice = PdfFileWriter()
    invoice_pages = generate_invoice_pages(invoice_form)
    for i, invoice_page in enumerate(invoice_pages):
        invoice.insertPage(invoice_page, i)
    # Write the result
    with open(output_path, "wb") as output_file:
        invoice.write(output_file)

    return output_path