"""Offline ML pipeline for the Social Support AI prototype.

Modules:
    schema             -- canonical applicant feature schema
    rules              -- documented ground-truth eligibility logic (labels)
    generate_data      -- synthetic labeled dataset generation
    train              -- scikit-learn model training + evaluation + artifacts
    generate_documents -- sample applicant documents for the end-to-end demo
"""

__version__ = "0.1.0"
