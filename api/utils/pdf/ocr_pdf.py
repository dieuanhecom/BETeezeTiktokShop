import logging
import platform
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytesseract
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
from PIL import Image

from api import setup_logging

# Setup logger
logger = logging.getLogger("api.utils.pdf.ocr_pdf")
setup_logging(logger=logger, level=logging.INFO)


# Window users need to specify the path
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Tesseract-OCR\tesseract.exe"
    path_to_poppler_exe = Path(r"C:\Library\bin")
elif platform.system() == "Darwin":  # macOS
    # Try to detect poppler path for macOS (via homebrew)
    poppler_paths = [
        "/opt/homebrew/bin",  # Apple Silicon (M1/M2)
        "/usr/local/bin",     # Intel Macs
        "/usr/bin",           # System binaries
    ]
    
    poppler_path = None
    for path in poppler_paths:
        if os.path.exists(os.path.join(path, "pdftoppm")):
            poppler_path = path
            logger.info(f"Found poppler at: {poppler_path}")
            break
    
    if not poppler_path:
        logger.warning("Poppler not found in standard locations")
    
    # Try to detect tesseract path for macOS
    tesseract_paths = [
        "/opt/homebrew/bin/tesseract",  # Apple Silicon (M1/M2) 
        "/usr/local/bin/tesseract",      # Intel Macs
        "/usr/bin/tesseract",            # System binaries
    ]
    
    tesseract_cmd = None
    for path in tesseract_paths:
        if os.path.exists(path):
            tesseract_cmd = path
            logger.info(f"Found tesseract at: {tesseract_cmd}")
            break
    
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        logger.warning("Tesseract not found in standard locations")


def __parse_info(info: str) -> Optional[dict]:
    try:
        info = info.strip()
        parts = info.split("\n")
        print(f"==>> parts: {parts}")

        name = parts[0]
        details = parts[-1]

        address = info.replace(name, "").replace(details, "").strip()

        while "\n" in address:
            address = address.replace("\n", " ")

        # Get zipcode
        zipcode = details.split()[-1]
        details = details.replace(zipcode, "").strip()

        # Get the state abbreviation
        state = details.split()[-1]
        details = details.replace(state, "").strip()

        # Get the city
        city = details.strip()

        return {
            "name": name,
            "address": address,
            "city": city,
            "state": state,
            "zipcode": zipcode,
        }
    except Exception as e:
        logger.error("An error occurred while parsing the info: ", exec_info=e)
        return None


def __clean_tracking_id(tracking_id: str):
    tracking_id = tracking_id.strip()
    tracking_id = tracking_id.replace(",", "")
    tracking_id = tracking_id.replace(".", "")
    tracking_id = tracking_id.replace(" ", "")

    return tracking_id


def _ocr_image(file_path: str, image: Image) -> dict:
    try:
        # Check if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.pytesseract.TesseractNotFoundError:
            logger.error("Tesseract is not installed or not found in PATH")
            return {
                "file": file_path,
                "status": "error",
                "message": "Tesseract OCR is not installed. Please install it with: brew install tesseract",
                "data": None,
            }
        
        # Read the image info
        x, y = image.size
        logger.info(f"{file_path}: Image size: {x}x{y}")

        # (x1, y1, x2, y2)
      
        tracking_id_img = image.crop((430, 2300, 1450, 2517))
        user_info = image.crop((320, 1480, 1656, 1786))


        # Extract text from image
        tracking_id: str = __clean_tracking_id(pytesseract.image_to_string(tracking_id_img))
        user_info: str = pytesseract.image_to_string(user_info)

        # Parse user info
        user_info = __parse_info(user_info)

        if user_info is None:
            return {
                "file": file_path,
                "status": "error",
                "message": "Có lỗi xảy ra khi parse thông tin người nhận. Kiểm tra lại shipping label",
                "data": None,
            }

        logger.info(f"OCR file {file_path} successfully, user_info: {user_info}, tracking_id: {tracking_id}")

        # Return the result
        data = {"tracking_id": tracking_id}
        data.update(user_info)

        return {
            "file": file_path,
            "status": "success",
            "message": "OCR file PDF thành công",
            "data": data,
        }
    except pytesseract.pytesseract.TesseractNotFoundError as e:
        logger.error("Tesseract not found", exc_info=e)
        return {
            "file": file_path,
            "status": "error",
            "message": "Tesseract OCR is not installed. Please install it with: brew install tesseract",
            "data": None,
        }
    except Exception as e:
        logger.error("An error occurred while processing the image", exc_info=e)
        return {
            "file": file_path,
            "status": "error",
            "message": f"Có lỗi xảy ra khi OCR file PDF: {str(e)}",
            "data": None,
        }


def process_pdf_to_info(pdf_path: str) -> dict:
    """
        Convert an PDF shipping label into a dictionary of shipping information
    Args:
        pdf_path (str): The path to the PDF file

    Returns:
        dict: A dictionary of shipping information
    """
    # DEVELOPMENT MODE: Mock data for testing without Poppler
    # Remove this block when Poppler is installed
    if os.environ.get('MOCK_OCR', 'false').lower() == 'true':
        import random
        logger.warning("MOCK OCR MODE: Using fake data for testing")
        
        # Simulate multi-page PDF (randomly 1-3 pages)
        num_pages = random.randint(1, 3)
        
        if num_pages == 1:
            # Single page mock
            mock_data = {
                "file": pdf_path,
                "status": "success", 
                "message": "MOCK: OCR file PDF thành công (using fake data)",
                "data": {
                    "tracking_id": f"94001091060299{random.randint(10000000, 99999999)}",
                    "name": f"Test Customer {random.randint(1, 100)}",
                    "address": f"{random.randint(100, 999)} Main Street",
                    "city": random.choice(["New York", "Los Angeles", "Chicago", "Houston"]),
                    "state": random.choice(["NY", "CA", "IL", "TX"]),
                    "zipcode": f"{random.randint(10000, 99999)}"
                }
            }
            return mock_data
        else:
            # Multi-page mock
            pages = []
            for page_num in range(1, num_pages + 1):
                pages.append({
                    "file": f"{pdf_path}_page_{page_num}",
                    "status": "success",
                    "message": f"MOCK: Page {page_num} processed successfully",
                    "page_number": page_num,
                    "data": {
                        "tracking_id": f"94001091060299{random.randint(10000000, 99999999)}",
                        "name": f"Test Customer {random.randint(1, 100)}",
                        "address": f"{random.randint(100, 999)} {random.choice(['Main', 'Oak', 'Elm', 'Pine'])} Street",
                        "city": random.choice(["New York", "Los Angeles", "Chicago", "Houston"]),
                        "state": random.choice(["NY", "CA", "IL", "TX"]),
                        "zipcode": f"{random.randint(10000, 99999)}"
                    }
                })
            
            return {
                "file": pdf_path,
                "status": "success",
                "message": f"MOCK: Processed {num_pages} pages successfully",
                "total_pages": num_pages,
                "successful_pages": num_pages,
                "failed_pages": 0,
                "pages": pages
            }
    
    try:
        if platform.system() == "Windows":
            PIL_pdf_pages = convert_from_path(pdf_path, 500, poppler_path=path_to_poppler_exe)
            PIL_pdf_pages[0].save("C:/workspace/trong.png", "PNG")
        else:
            # For macOS/Linux systems
            try:
                if platform.system() == "Darwin" and poppler_path:
                    PIL_pdf_pages = convert_from_path(pdf_path, 500, poppler_path=poppler_path)
                else:
                    PIL_pdf_pages = convert_from_path(pdf_path, 500)
            except PDFInfoNotInstalledError:
                logger.error("Poppler is not installed or not found in PATH")
                # Suggest installation instructions
                if platform.system() == "Darwin":
                    logger.info("Please install poppler with: brew install poppler")
                elif platform.system() == "Linux":
                    logger.info("Please install poppler with your package manager, e.g., apt install poppler-utils")
                
                return {
                    "file": pdf_path,
                    "status": "error",
                    "message": "Poppler is not installed. Please install it first to process PDF files.",
                    "data": None,
                }

        # Process all pages in the PDF
        if len(PIL_pdf_pages) == 0:
            return {
                "file": pdf_path,
                "status": "error",
                "message": "PDF file is empty or corrupted",
                "data": None,
            }
        
        # If single page, return single result for backward compatibility
        if len(PIL_pdf_pages) == 1:
            output = _ocr_image(file_path=f"{pdf_path}_page_1", image=PIL_pdf_pages[0])
            return output
        
        # If multiple pages, process each page and return array of results
        logger.info(f"Processing {len(PIL_pdf_pages)} pages from PDF")
        all_results = []
        
        for page_num, page_image in enumerate(PIL_pdf_pages, start=1):
            logger.info(f"Processing page {page_num} of {len(PIL_pdf_pages)}")
            page_result = _ocr_image(
                file_path=f"{pdf_path}_page_{page_num}", 
                image=page_image
            )
            # Add page number to result
            page_result["page_number"] = page_num
            all_results.append(page_result)
        
        # Return aggregated results for multi-page PDF
        successful_pages = [r for r in all_results if r["status"] == "success"]
        failed_pages = [r for r in all_results if r["status"] == "error"]
        
        return {
            "file": pdf_path,
            "status": "success" if successful_pages else "error",
            "message": f"Processed {len(successful_pages)} of {len(PIL_pdf_pages)} pages successfully",
            "total_pages": len(PIL_pdf_pages),
            "successful_pages": len(successful_pages),
            "failed_pages": len(failed_pages),
            "pages": all_results  # Return all page results
        }
    except Exception as e:
        logger.error(f"Failed to process PDF: {str(e)}", exc_info=e)
        return {
            "file": pdf_path,
            "status": "error",
            "message": f"Có lỗi xảy ra khi xử lý file PDF: {str(e)}",
            "data": None,
        }
