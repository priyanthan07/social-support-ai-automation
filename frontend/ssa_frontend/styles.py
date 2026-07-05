"""Custom CSS theme for the Social Support portal."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
    padding: 1.5rem 2rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.15);
}

.main-header h1 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 700;
}

.main-header p {
    margin: 0.4rem 0 0 0;
    opacity: 0.9;
}

.card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
}

.card-title {
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 0.75rem;
}

.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
}

.badge-approve { background: #dcfce7; color: #166534; }
.badge-decline { background: #fee2e2; color: #991b1b; }
.badge-review { background: #fef3c7; color: #92400e; }
.badge-processing { background: #dbeafe; color: #1d4ed8; }

.stepper {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 1rem 0;
}

.step {
    flex: 1;
    min-width: 100px;
    text-align: center;
    padding: 0.75rem 0.5rem;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #f1f5f9;
    color: #64748b;
}

.step.active { background: #2563eb; color: white; }
.step.done { background: #dcfce7; color: #166534; }

.metric-box {
    background: #f8fafc;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #0f172a;
}

.metric-label {
    font-size: 0.8rem;
    color: #64748b;
}

.stButton > button {
    border-radius: 10px;
    font-weight: 600;
}
</style>
"""
