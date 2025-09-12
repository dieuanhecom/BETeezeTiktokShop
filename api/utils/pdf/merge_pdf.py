import PyPDF2
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def merge_pdf_files(pdf_results):
    """
    Merge multiple PDF files into one
    
    Args:
        pdf_results (list): List of download results from download_pdf_from_url
        
    Returns:
        dict: Result dictionary containing:
            - success (bool): Whether merge was successful
            - pdf_buffer (BytesIO): Merged PDF buffer if successful
            - successful_urls (list): List of successfully merged URLs
            - failed_urls (list): List of failed URLs with error messages
            - error (str): Error message if complete failure
    """
    
    successful_urls = []
    failed_urls = []
    
    # Separate successful and failed downloads
    for result in pdf_results:
        if result['success']:
            successful_urls.append(result['url'])
        else:
            failed_urls.append({
                'url': result['url'],
                'error': result['error']
            })
    
    # Check if we have any PDFs to merge
    if not successful_urls:
        logger.error("No PDFs were successfully downloaded")
        return {
            'success': False,
            'error': 'No PDFs were successfully downloaded',
            'successful_urls': [],
            'failed_urls': failed_urls
        }
    
    try:
        # Create PDF merger
        merger = PyPDF2.PdfMerger()
        
        # Add each successful PDF to merger
        for result in pdf_results:
            if result['success']:
                try:
                    pdf_buffer = result['data']
                    pdf_buffer.seek(0)  # Ensure we're at the beginning
                    merger.append(pdf_buffer)
                    logger.info(f"Added PDF from {result['url']} to merger")
                except Exception as e:
                    logger.error(f"Error adding PDF from {result['url']} to merger: {str(e)}")
                    # Move from successful to failed
                    successful_urls.remove(result['url'])
                    failed_urls.append({
                        'url': result['url'],
                        'error': f'Error during merge: {str(e)}'
                    })
        
        # Check if we still have PDFs after merge attempts
        if not successful_urls:
            logger.error("All PDFs failed during merge process")
            return {
                'success': False,
                'error': 'All PDFs failed during merge process',
                'successful_urls': [],
                'failed_urls': failed_urls
            }
        
        # Write merged PDF to buffer
        output_buffer = BytesIO()
        merger.write(output_buffer)
        merger.close()
        
        output_buffer.seek(0)
        
        logger.info(f"Successfully merged {len(successful_urls)} PDFs")
        
        return {
            'success': True,
            'pdf_buffer': output_buffer,
            'successful_urls': successful_urls,
            'failed_urls': failed_urls
        }
        
    except Exception as e:
        logger.error(f"Error during PDF merge: {str(e)}")
        return {
            'success': False,
            'error': f'Error during PDF merge: {str(e)}',
            'successful_urls': [],
            'failed_urls': failed_urls + [{
                'url': url,
                'error': 'Failed during merge process'
            } for url in successful_urls]
        }