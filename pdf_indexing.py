from promptflow import tool
import subprocess
import sys

def install_packages():
    """
    Install required packages for the workflow.
    This function installs 'azure-ai-formrecognizer' and 'python-dotenv' using pip.

    @return: None
    """
    subprocess.check_call([sys.executable, "-m", "pip", "install", "azure-ai-formrecognizer==3.2.0", "python-dotenv"])

# Install the necessary packages
install_packages()

import json
from typing import Any, Dict
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os

# Replace with your Azure Form Recognizer endpoint and key
endpoint = "YOUR_ENDPOINT"
key = "YOUR_KEY"

def extract_text(result: Any) -> list:
    """
    Extracts text content from the analyzed document.

    @param result: The result object returned by the Form Recognizer analysis.
    @type result: Any

    @return: A list of strings where each string represents a line of text in the document.
    @rtype: list
    """
    texts = []
    for page in result.pages:
        for line in page.lines:
            texts.append(line.content)
    return texts

def extract_structure(result: Any) -> list:
    """
    Extracts structural information from the analyzed document, such as page dimensions and line details.

    @param result: The result object returned by the Form Recognizer analysis.
    @type result: Any

    @return: A list of dictionaries, each representing the structure of a page in the document.
    @rtype: list
    """
    structures = []
    for page in result.pages:
        structure_data = {
            "page_number": page.page_number,
            "width": page.width,
            "height": page.height,
            "unit": page.unit,
            "lines": []
        }
        for line in page.lines:
            line_data = {
                "content": line.content,
                "spans": [{"offset": span.offset, "length": span.length} for span in line.spans]
            }
            structure_data["lines"].append(line_data)
        
        structures.append(structure_data)
    return structures

def extract_tables(result: Any) -> list:
    """
    Extracts table data from the analyzed document, including cell content and position.

    @param result: The result object returned by the Form Recognizer analysis.
    @type result: Any

    @return: A list of dictionaries, each representing a table found in the document.
    @rtype: list
    """
    tables = []
    for table_idx, table in enumerate(result.tables):
        table_data = {
            "table_index": table_idx,
            "row_count": table.row_count,
            "column_count": table.column_count,
            "cells": []
        }
        for cell in table.cells:
            cell_data = {
                "row_index": cell.row_index,
                "column_index": cell.column_index,
                "content": cell.content,
                "bounding_regions": [{"page_number": region.page_number, "polygon": [point for point in region.polygon]} for region in cell.bounding_regions]
            }
            table_data["cells"].append(cell_data)
        tables.append(table_data)
    return tables

# Define the tool function for promptflow workflow
@tool
def pdf_indexing(input_url: str) -> Dict[str, Any]:
    """
    Analyzes a PDF document from a given URL and extracts text, structure, and table data.
    The extracted data is then structured and returned in a JSON format suitable for indexing.

    @param input_url: The URL of the PDF document to analyze.
    @type input_url: str

    @return: A dictionary containing the structured data extracted from the PDF.
    @rtype: Dict[str, Any]
    """
    # Initialize the DocumentAnalysisClient with Azure Form Recognizer credentials
    document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    # Start the document analysis process for the specified document URL
    poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-layout", input_url)
    result = poller.result()

    # Extract text, structure and table data from the analysis result
    text_data = extract_text(result)
    structure_data = extract_structure(result)
    table_data = extract_tables(result)

    # Combine all extracted data into one JSON structure
    document_data = {
        "embeddings": {
            "api_base": "YOUR_API_BASE",
            "api_type": "azure",
            "api_version": "2023-07-01-preview",
            "batch_size": "1",
            "connection": {
              "id": "YOUR_ID"
            },
            "connection_type": "workspace_connection",
            "deployment": "text-embedding-ada-002",
            "dimension": 1536,
            "kind": "open_ai",
            "model": "text-embedding-ada-002",
            "schema_version": "2"
          },
          "index": {
            "api_version": "2023-07-01-preview",
            "connection": {
              "id": "YOUR_ID"
            },
            "connection_type": "workspace_connection",
            "endpoint": "YOUR_ENDPOINT",
            "engine": "azure-sdk",
            "field_mapping": {
              "content": "content",
              "embedding": "contentVector",
              "metadata": "content"
            },
            "index": "YOUR_INDEX",
            "kind": "acs",
            "semantic_configuration_name": "azureml-default"
          },
          "extracted_data": {
              "text": text_data,
              "structure": structure_data,
              "tables": table_data
          }
    }

    # Convert the combined data to a JSON string
    document_data_json = json.dumps(document_data)

    return {
        "document_data": document_data_json
    }
