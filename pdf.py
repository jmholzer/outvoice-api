import io
import os
from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.pdf import PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from datetime import datetime


pdfmetrics.registerFont(TTFont('OpenSans', 'OpenSans-Regular.ttf'))


def format_date(date):
    """
    Convert the date from the format received in
    the API call to a UK-formatted date

    Arguments:
    date -- date received in API call
    """
    return datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")


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


def generate_invoice_address_line(form: dict) -> str:
    if form["addressLine2"]:
        return (
            '\n'.join([
                form["firstName"] + ' ' + form["lastName"],
                form["addressLine1"],
                form["addressLine2"],
                form["city"],
                form["postCode"]
            ])
        )
    else:
        return (
            '\n'.join([
                form["firstName"] + ' ' + form["lastName"],
                form["addressLine1"],
                form["city"],
                form["postCode"]
            ])
        )


def generate_invoice_overlay(client_form: dict) -> PageObject:
    """
    Create a PDF page (overlay) of invoice information
    that can be rendered on top of a blank invoice page.

    Arguments:
    client_form -- data about the client passed from
        the API end-point
    """
    packet = io.BytesIO()
    invoice_layer_canvas = canvas.Canvas(packet)
    invoice_layer_canvas.setPageSize((A4))
    text = invoice_layer_canvas.beginText()
    text.setFont('OpenSans', 8)

    line = client_form["receiptNumber"]
    text.setTextOrigin(29.5*mm, 241.5*mm)
    text.textLines(line)

    line = format_date(client_form["invoiceDate"])
    text.setTextOrigin(65.5*mm, 241.5*mm)
    text.textLines(line)

    line = generate_invoice_address_line(client_form)
    text.setTextOrigin(29.5*mm, 224.5*mm)
    text.textLines(line)

    invoice_layer_canvas.drawText(text)
    invoice_layer_canvas.save()
    packet.seek(0)
    return PdfFileReader(packet).getPage(0)


def generate_invoice(client_form: dict) -> str:
    """
    Generate and save an invoice as a PDF.
    Returns absolute path of saved invoice.

    Arguments:
    client_form -- data about the client passed from
        the API end-point
    """
    template_path = "resources/invoice.pdf"
    template_path = generate_absolute_path(template_path)

    output_path = (
        "invoices/"
        + "_".join([
            client_form["firstName"],
            client_form["lastName"],
            client_form["invoiceDate"],
            datetime.now().strftime("%H_%M_%S")
        ])
    )
    output_path = generate_absolute_path(output_path)

    # Read the blank invoice
    invoice = read_first_page(template_path)
    # Generate an overlay using client data
    overlay = generate_invoice_overlay(client_form)
    # Merge the overlay on top of the blank invoice.
    invoice.mergePage(overlay)
    # Write the result
    write_page_to_file(invoice, output_path)

    return output_path