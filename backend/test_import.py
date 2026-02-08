
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    print("Successfully imported docling.document_converter")
except ImportError as e:
    print(f"Failed to import docling.document_converter: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

try:
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode, AcceleratorOptions, AcceleratorDevice, TesseractCliOcrOptions
    print("Successfully imported docling.datamodel.pipeline_options")
except ImportError as e:
    print(f"Failed to import docling.datamodel.pipeline_options: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

try:
    from docling.chunking import HybridChunker
    print("Successfully imported docling.chunking")
except ImportError as e:
    print(f"Failed to import docling.chunking: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
