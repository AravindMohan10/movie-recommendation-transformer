# backend/app/email_service.py
"""
Production-grade email service using Resend (free tier: 3000 emails/month)
Fallback to SMTP for development or when Resend is not configured
"""
import os
import logging
import urllib.parse
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Resend configuration (free tier: 3000 emails/month)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@resend.dev")  # Default resend domain

# SMTP fallback configuration (Gmail, SendGrid, etc.)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")

# Frontend URL for reset links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


async def send_password_reset_email(email: str, reset_token: str, username: str) -> bool:
    """
    Send password reset email using Resend or SMTP fallback.
    
    Returns True if email was sent successfully, False otherwise.
    """
    # URL encode the token to handle special characters properly
    encoded_token = urllib.parse.quote(reset_token, safe='')
    reset_link = f"{FRONTEND_URL}/reset-password?token={encoded_token}"
    logger.info(f"Generated reset link for {email}, token length: {len(reset_token)}")
    
    subject = "Reset Your CineAI Password"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Your Password</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">🎬 CineAI</h1>
        </div>
        <div style="background: white; padding: 40px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #333; margin-top: 0;">Password Reset Request</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your password for your CineAI account. Click the button below to reset your password:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
                    Reset Password
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="color: #667eea; word-break: break-all; font-size: 12px; background: #f5f5f5; padding: 10px; border-radius: 5px;">{reset_link}</p>
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                <strong>This link will expire in 1 hour.</strong> If you didn't request a password reset, please ignore this email.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #999; font-size: 12px; margin: 0;">
                If you're having trouble clicking the button, copy and paste the URL above into your web browser.
            </p>
        </div>
        <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
            <p>© {os.getenv('CURRENT_YEAR', '2025')} CineAI. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Reset Your CineAI Password

Hi {username},

We received a request to reset your password for your CineAI account.

Click this link to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email.

---
© 2025 CineAI. All rights reserved.
    """
    
    # Try Resend first (production-ready, free tier)
    if RESEND_API_KEY:
        try:
            return await _send_via_resend(email, subject, html_body, text_body)
        except Exception as e:
            logger.warning(f"Resend email failed: {e}, falling back to SMTP")
    
    # Fallback to SMTP
    if SMTP_USER and SMTP_PASSWORD:
        try:
            return await _send_via_smtp(email, subject, html_body, text_body)
        except Exception as e:
            logger.error(f"SMTP email failed: {e}")
            return False
    
    # No email service configured - log for development
    logger.warning("No email service configured. Reset link for %s: %s", email, reset_link)
    return True


async def _send_via_resend(email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email using Resend API"""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": RESEND_FROM_EMAIL,
                    "to": [email],
                    "subject": subject,
                    "html": html_body,
                    "text": text_body,
                },
                timeout=10.0,
            )
            
            if response.status_code == 200:
                logger.info(f"Password reset email sent via Resend to {email}")
                return True
            else:
                logger.error(f"Resend API error: {response.status_code} - {response.text}")
                return False
                
    except ImportError:
        logger.warning("httpx not installed. Install with: pip install httpx")
        return False
    except Exception as e:
        logger.error(f"Error sending email via Resend: {e}")
        raise


async def _send_via_smtp(email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email using SMTP (Gmail, SendGrid, etc.)"""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_FROM_EMAIL or SMTP_USER
        msg['To'] = email
        
        # Add both HTML and text versions
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Password reset email sent via SMTP to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email via SMTP: {e}")
        raise
