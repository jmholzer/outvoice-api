import io
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
from typing import List, Dict, Optional


pdfmetrics.registerFont(TTFont('OpenSans', 'OpenSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('OpenSans-Italic', 'OpenSans-Italic.ttf'))


# Name of the layout to use to generate the invoice.
LAYOUT_NAME = "default"


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
    invoice_date = datetime.strptime(invoice_form["invoice_date"], "%Y-%m-%d")
    invoice_date = invoice_date.strftime("%d/%m/%Y")
    invoice_form["invoice_date"] = invoice_date


def format_address_line(invoice_form: dict) -> None:
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


def format_terms_line(invoice_form: dict) -> None:
    """
    Add a line informing the customer of the terms of the invoice.

    Arguments:
    invoice_form -- data about the client passed from
        the API end-point.
    """
    invoice_form["terms"] = "Pay on or before " + invoice_form["pay_date"]


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
        "post_code",
        "pay_date"
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
    format_terms_line(invoice_form)
    delete_unused_keys(invoice_form)


def write_line_items(
        text: PDFTextObject,
        line_items: List[Dict[str,str]],
        layout: Dict[str,str]
    ) -> None:
    """
    Write a given array of line items to the supplied text object (invoice page).

    Arguments:
    text -- the reportlab PDFTextObject object attached to the overlay canvas.
    line_items -- the array of line items to write.
    layout -- a dict containing information on position and style of text.
    """
    line_item_offset = 0
    for line_item in line_items:
        for key in line_item:
            write_text_to_overlay(
                line_item[key],
                text,
                layout[key],
                y_offset=line_item_offset
            )
        line_item_offset -= 5


def write_page_number(
        text: PDFTextObject,
        page_number: int,
        total_pages: int,
        layout: Dict[str, Dict[str, str]]
    ) -> None:
    """
    Write a page number and (if necessary) a 'turnover prompt' to 
    the supplied text object (invoice page)

    Arguments:
    text -- the reportlab PDFTextObject object attached to the overlay canvas.
    page_number -- the number of the page being written on.
    total_pages -- the total number of pages in the invoice.
    layout -- a dict that contains the following fields:
            x_origin -- the x position (mm) to start the text at on the overlay.
            y_origin -- the y position (mm) to start the text at on the overlay.
            font -- the font to use for the text to write.
            size -- the size of the text to write.
    """
    page_number_line = f"Page {page_number + 1} of {total_pages}"
    write_text_to_overlay(page_number_line, text, layout["page_number_line"])
    if page_number + 1 < total_pages:
        turn_over_line = "(Invoice continues overleaf)"
        write_text_to_overlay(turn_over_line, text, layout["turn_over_line"])


def generate_invoice_overlay(
        invoice_form: Dict[str,str],
        layout: Dict[str,str],
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
    packet = io.BytesIO()
    invoice_layer_canvas = canvas.Canvas(packet)
    invoice_layer_canvas.setPageSize((A4))
    text = invoice_layer_canvas.beginText()

    for field in invoice_form:
        if field == "line_items":
            write_line_items(text, invoice_form["line_items"], layout["line_items"])
            continue
        write_text_to_overlay(invoice_form[field], text, layout[field])
    
    write_page_number(text, page_number, total_pages, layout)

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


def read_layout_file(layout_name):
    """
    Read the layout file with the specified name and return the dict
    loaded from the json therein.

    Arguments:
    layout_name -- the name of the layout to read.
    """
    file_path = generate_absolute_path(f"layouts/{layout_name}.json")
    with open(file_path, "r") as layout_file:
        layout = load(layout_file)
    return layout


def generate_invoice_pages(invoice_form: dict) -> List[PageObject]:
    """
    Returns a list of finished invoice pages (PageObjects).

    Arguments:
    invoice_form -- the form data used to generate the invoice.
    """
    page_template_path = generate_absolute_path("resources/invoice.pdf")
    line_item_lists = generate_line_item_lists(invoice_form["line_items"])
    invoice_pages = []
    layout = read_layout_file(LAYOUT_NAME)

    total_pages = len(line_item_lists)
    for page_number, line_item_list in enumerate(line_item_lists):
        invoice_form_copy = copy(invoice_form)
        invoice_form_copy["line_items"] = line_item_list

        # Read the blank invoice
        invoice_page = read_first_page(page_template_path)
        # Generate an overlay using client data
        overlay = generate_invoice_overlay(invoice_form_copy, layout, page_number, total_pages)
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
    format_invoice_form_input(invoice_form)
    invoice_pages = generate_invoice_pages(invoice_form)
    for i, invoice_page in enumerate(invoice_pages):
        invoice.insertPage(invoice_page, i)
    # Write the result
    with open(output_path, "wb") as output_file:
        invoice.write(output_file)

    return output_path