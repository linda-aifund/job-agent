"""HTML email templates for job notifications."""

from datetime import datetime

from job_agent.jobs.models import JobListing


def render_job_email(jobs: list[JobListing], dry_run: bool = False) -> tuple[str, str]:
    """Render an HTML email with matched job listings.

    Returns (subject, html_body).
    """
    date_str = datetime.now().strftime("%B %d, %Y")
    prefix = "[DRY RUN] " if dry_run else ""
    subject = f"{prefix}Job Agent: {len(jobs)} new matching jobs - {date_str}"

    job_rows = "\n".join(_render_job_row(job, i + 1) for i, job in enumerate(jobs))

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            background: #1a73e8;
            color: white;
            padding: 24px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 22px;
            font-weight: 600;
        }}
        .header p {{
            margin: 8px 0 0;
            opacity: 0.9;
            font-size: 14px;
        }}
        .content {{
            padding: 24px;
        }}
        .job-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            transition: border-color 0.2s;
        }}
        .job-card:hover {{
            border-color: #1a73e8;
        }}
        .job-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }}
        .job-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1a73e8;
            text-decoration: none;
            margin: 0;
        }}
        .job-title a {{
            color: #1a73e8;
            text-decoration: none;
        }}
        .job-title a:hover {{
            text-decoration: underline;
        }}
        .score-badge {{
            background: #e8f5e9;
            color: #2e7d32;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .score-high {{
            background: #e8f5e9;
            color: #2e7d32;
        }}
        .score-medium {{
            background: #fff3e0;
            color: #ef6c00;
        }}
        .score-low {{
            background: #fce4ec;
            color: #c62828;
        }}
        .job-company {{
            font-size: 14px;
            color: #555;
            margin: 4px 0;
        }}
        .job-meta {{
            font-size: 13px;
            color: #777;
            margin: 4px 0;
        }}
        .job-reason {{
            font-size: 13px;
            color: #666;
            margin-top: 8px;
            font-style: italic;
        }}
        .footer {{
            background: #fafafa;
            padding: 16px 24px;
            text-align: center;
            font-size: 12px;
            color: #999;
            border-top: 1px solid #eee;
        }}
        .rank {{
            color: #999;
            font-size: 13px;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Daily Job Matches</h1>
            <p>{len(jobs)} new job{'' if len(jobs) == 1 else 's'} found - {date_str}</p>
        </div>
        <div class="content">
            {job_rows}
        </div>
        <div class="footer">
            Sent by Job Agent | Automated daily job matching
        </div>
    </div>
</body>
</html>"""

    return subject, html


def _render_job_row(job: JobListing, rank: int) -> str:
    """Render a single job card."""
    # Score badge color
    if job.match_score >= 0.7:
        score_class = "score-high"
    elif job.match_score >= 0.4:
        score_class = "score-medium"
    else:
        score_class = "score-low"

    score_pct = int(job.match_score * 100)

    meta_parts = []
    if job.location:
        meta_parts.append(job.location)
    if job.salary:
        meta_parts.append(job.salary)
    if job.job_type:
        meta_parts.append(job.job_type)
    if job.remote:
        meta_parts.append("Remote")
    if job.source:
        meta_parts.append(f"via {job.source}")

    meta_line = " &middot; ".join(meta_parts)

    # Truncate description for email
    desc = job.description[:200] + "..." if len(job.description) > 200 else job.description

    reason_html = ""
    if job.match_reason:
        reason_html = f'<div class="job-reason">{job.match_reason}</div>'

    desc_html = ""
    if desc:
        desc_html = f'<div style="font-size:13px;color:#555;margin-top:8px;">{desc}</div>'

    return f"""
        <div class="job-card">
            <div class="job-header">
                <div class="job-title">
                    <span class="rank">#{rank}</span>
                    <a href="{job.url}">{job.title}</a>
                </div>
                <span class="score-badge {score_class}">{score_pct}% match</span>
            </div>
            <div class="job-company">{job.company}</div>
            <div class="job-meta">{meta_line}</div>
            {desc_html}
            {reason_html}
        </div>"""


def render_test_email() -> tuple[str, str]:
    """Render a test email to verify SMTP configuration."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"Job Agent - Test Email ({now})"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; padding: 20px;">
    <h2>Job Agent - Test Email</h2>
    <p>This is a test email from Job Agent.</p>
    <p>If you received this, your email configuration is working correctly.</p>
    <p style="color: #999; font-size: 12px;">Sent at: {now}</p>
</body>
</html>"""
    return subject, html
