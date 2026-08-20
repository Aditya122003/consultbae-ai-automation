# Email notification service for ConsultBae Automation Platform
# Handles SMTP dispatch via Gmail for duplicate alerts and new candidate notifications in a clean, corporate light theme

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "mycoding2025@gmail.com"
SENDER_PASSWORD = "ezluxpngzgjqwory"  # App password without spaces
DEFAULT_RECIPIENT = "mycoding2025@gmail.com"


def send_duplicate_candidate_alert(candidate_data: dict, matched_candidate: dict, recipient: str = DEFAULT_RECIPIENT) -> bool:
    """Dispatches clean, professional light-themed email notification when a duplicate candidate is detected."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[ConsultBae Alert] Duplicate Candidate Detected - {candidate_data.get('full_name', 'Unknown')}"
        msg["From"] = f"ConsultBae Automation System <{SENDER_EMAIL}>"
        msg["To"] = recipient

        now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
              background-color: #f8fafc;
              color: #1e293b;
              margin: 0;
              padding: 30px 15px;
            }}
            .wrapper {{
              max-width: 580px;
              margin: 0 auto;
              background-color: #ffffff;
              border: 1px solid #e2e8f0;
              border-radius: 8px;
              overflow: hidden;
              box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            }}
            .header {{
              padding: 24px 28px 20px;
              border-bottom: 1px solid #edf2f7;
            }}
            .tag {{
              display: inline-block;
              font-size: 11px;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 0.5px;
              padding: 3px 8px;
              border-radius: 4px;
              background-color: #fef2f2;
              color: #dc2626;
              border: 1px solid #fecaca;
              margin-bottom: 10px;
            }}
            .title {{
              font-size: 18px;
              font-weight: 700;
              color: #0f172a;
              margin: 0 0 6px 0;
            }}
            .subtitle {{
              font-size: 13px;
              color: #64748b;
              margin: 0;
            }}
            .content {{
              padding: 24px 28px;
            }}
            .notice-card {{
              background-color: #fffbeb;
              border: 1px solid #fef3c7;
              border-left: 3px solid #f59e0b;
              padding: 12px 16px;
              border-radius: 4px;
              font-size: 13px;
              color: #92400e;
              margin-bottom: 22px;
              line-height: 1.5;
            }}
            .section-title {{
              font-size: 13px;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 0.5px;
              color: #475569;
              margin: 0 0 10px 0;
            }}
            table {{
              width: 100%;
              border-collapse: collapse;
              margin-bottom: 20px;
              font-size: 13px;
            }}
            th {{
              background-color: #f8fafc;
              color: #475569;
              font-weight: 600;
              text-align: left;
              padding: 10px 12px;
              border-bottom: 1px solid #e2e8f0;
              border-top: 1px solid #e2e8f0;
            }}
            td {{
              padding: 10px 12px;
              border-bottom: 1px solid #f1f5f9;
              color: #334155;
            }}
            .field-name {{
              font-weight: 600;
              color: #64748b;
              width: 25%;
            }}
            .highlight-match {{
              color: #dc2626;
              font-weight: 600;
            }}
            .footer {{
              padding: 16px 28px;
              background-color: #f8fafc;
              border-top: 1px solid #e2e8f0;
              font-size: 12px;
              color: #94a3b8;
              text-align: center;
            }}
          </style>
        </head>
        <body>
          <div class="wrapper">
            <div class="header">
              <span class="tag">Duplicate Alert</span>
              <h1 class="title">Candidate Match Detected</h1>
              <p class="subtitle">An application was submitted with contact details matching an existing profile in MySQL.</p>
            </div>
            
            <div class="content">
              <div class="notice-card">
                <strong>System Notice:</strong> Deduplication rules blocked creating a duplicate profile. Below is the field-by-field comparison for your review.
              </div>

              <div class="section-title">Submission Comparison</div>
              <table>
                <thead>
                  <tr>
                    <th class="field-name">Field</th>
                    <th>New Submission</th>
                    <th>Existing Record (ID #{matched_candidate.get('id', 'N/A')})</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="field-name">Name</td>
                    <td>{candidate_data.get('full_name', '-')}</td>
                    <td>{matched_candidate.get('full_name', '-')}</td>
                  </tr>
                  <tr>
                    <td class="field-name">Phone</td>
                    <td class="highlight-match">{candidate_data.get('phone', '-')}</td>
                    <td>{matched_candidate.get('phone', '-')}</td>
                  </tr>
                  <tr>
                    <td class="field-name">Email</td>
                    <td>{candidate_data.get('email', '-')}</td>
                    <td>{matched_candidate.get('email', '-')}</td>
                  </tr>
                  <tr>
                    <td class="field-name">Skills</td>
                    <td>{candidate_data.get('skills', '-')}</td>
                    <td>{matched_candidate.get('skills', '-')}</td>
                  </tr>
                  <tr>
                    <td class="field-name">City</td>
                    <td>{candidate_data.get('city', '-')}</td>
                    <td>{matched_candidate.get('city', '-')}</td>
                  </tr>
                </tbody>
              </table>

              <p style="font-size: 12px; color: #64748b; margin: 0; line-height: 1.4;">
                No manual action required if this is a known applicant. The master record remains intact.
              </p>
            </div>

            <div class="footer">
              ConsultBae Talent & Automation Platform • Generated on {now_str}
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

        print(f"✅ Professional light email sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")
        return False


def send_new_candidate_success_email(candidate_data: dict, assigned_category: str, recipient: str = DEFAULT_RECIPIENT) -> bool:
    """Dispatches clean, professional light-themed confirmation email when a new candidate is saved."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[ConsultBae] New Candidate Ingested - {candidate_data.get('full_name', 'Unknown')}"
        msg["From"] = f"ConsultBae Automation System <{SENDER_EMAIL}>"
        msg["To"] = recipient

        now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
              background-color: #f8fafc;
              color: #1e293b;
              margin: 0;
              padding: 30px 15px;
            }}
            .wrapper {{
              max-width: 580px;
              margin: 0 auto;
              background-color: #ffffff;
              border: 1px solid #e2e8f0;
              border-radius: 8px;
              overflow: hidden;
              box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            }}
            .header {{
              padding: 24px 28px 20px;
              border-bottom: 1px solid #edf2f7;
            }}
            .tag {{
              display: inline-block;
              font-size: 11px;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 0.5px;
              padding: 3px 8px;
              border-radius: 4px;
              background-color: #ecfdf5;
              color: #059669;
              border: 1px solid #a7f3d0;
              margin-bottom: 10px;
            }}
            .title {{
              font-size: 18px;
              font-weight: 700;
              color: #0f172a;
              margin: 0 0 6px 0;
            }}
            .subtitle {{
              font-size: 13px;
              color: #64748b;
              margin: 0;
            }}
            .content {{
              padding: 24px 28px;
            }}
            .info-grid {{
              background-color: #f8fafc;
              border: 1px solid #e2e8f0;
              border-radius: 6px;
              padding: 16px 20px;
              margin-bottom: 20px;
            }}
            .info-row {{
              display: flex;
              padding: 6px 0;
              font-size: 13px;
              border-bottom: 1px solid #edf2f7;
            }}
            .info-row:last-child {{
              border-bottom: none;
            }}
            .info-label {{
              width: 30%;
              font-weight: 600;
              color: #64748b;
            }}
            .info-value {{
              width: 70%;
              color: #1e293b;
            }}
            .category-badge {{
              display: inline-block;
              background-color: #eff6ff;
              color: #2563eb;
              border: 1px solid #bfdbfe;
              padding: 2px 8px;
              border-radius: 4px;
              font-size: 12px;
              font-weight: 600;
            }}
            .footer {{
              padding: 16px 28px;
              background-color: #f8fafc;
              border-top: 1px solid #e2e8f0;
              font-size: 12px;
              color: #94a3b8;
              text-align: center;
            }}
          </style>
        </head>
        <body>
          <div class="wrapper">
            <div class="header">
              <span class="tag">New Profile Ingested</span>
              <h1 class="title">Candidate Added to Directory</h1>
              <p class="subtitle">A verified candidate application has been ingested and categorized via AI.</p>
            </div>
            
            <div class="content">
              <div class="info-grid">
                <div class="info-row">
                  <div class="info-label">Full Name</div>
                  <div class="info-value"><strong>{candidate_data.get('full_name')}</strong></div>
                </div>
                <div class="info-row">
                  <div class="info-label">Phone Number</div>
                  <div class="info-value">{candidate_data.get('phone')}</div>
                </div>
                <div class="info-row">
                  <div class="info-label">Email</div>
                  <div class="info-value">{candidate_data.get('email') or 'N/A'}</div>
                </div>
                <div class="info-row">
                  <div class="info-label">City</div>
                  <div class="info-value">{candidate_data.get('city') or 'N/A'}</div>
                </div>
                <div class="info-row">
                  <div class="info-label">Skills</div>
                  <div class="info-value">{candidate_data.get('skills') or 'N/A'}</div>
                </div>
                <div class="info-row">
                  <div class="info-label">Domain Category</div>
                  <div class="info-value"><span class="category-badge">{assigned_category}</span></div>
                </div>
              </div>

              <p style="font-size: 12px; color: #64748b; margin: 0; line-height: 1.4;">
                This profile is now accessible in the Talent Directory and available for assignment.
              </p>
            </div>

            <div class="footer">
              ConsultBae Talent & Automation Platform • Generated on {now_str}
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())

        print(f"✅ Professional light email sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ Failed to send new candidate email: {e}")
        return False
