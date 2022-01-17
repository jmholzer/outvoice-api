import os
import time


def print_document(file_path: str) -> None:
    """
    Send the document at the specified path to
    the printer with the specified name.

    Arguments:
    file_path -- path to the file to be printed
    printer_name -- name of the local printer to send to
    """
    #while not os.path.exists(file_path):
    #    time.sleep(0.1)

    os.system(f"lp {file_path}")
    
    # look into lpstat for status of print jobs