"""
Final report generation formatting.
"""

def generate_markdown_report(report_data: dict) -> str:
    """Generate a markdown version of the final feedback report."""
    md = f"# Interview Feedback Report\n\n"
    md += f"## Overall Recommendation: {report_data.get('hiring_recommendation', 'Unknown').replace('_', ' ').upper()}\n\n"
    
    md += "### Scores\n"
    md += f"- Overall: {report_data.get('overall_score', 0)}/100\n"
    md += f"- Technical: {report_data.get('technical_score', 0)}/100\n"
    md += f"- Behavioral: {report_data.get('behavioral_score', 0)}/100\n"
    md += f"- Coding: {report_data.get('coding_score', 0)}/100\n\n"
    
    md += "### Summary\n"
    md += f"{report_data.get('summary', '')}\n\n"
    
    md += "### Strengths\n"
    for s in report_data.get("strengths", []):
        md += f"- {s}\n"
        
    md += "\n### Areas for Improvement\n"
    for w in report_data.get("weaknesses", []):
        md += f"- {w}\n"
        
    md += "\n### Detailed Feedback\n"
    md += f"{report_data.get('detailed_feedback', '')}\n"
    
    return md
