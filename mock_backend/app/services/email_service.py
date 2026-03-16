import smtplib
import logging
import asyncio
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """
    Service for sending emails to candidates and developers.
    """
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.mail_from = settings.MAIL_FROM
        self.developer_emails = settings.DEVELOPER_EMAILS
        
        if not self.user or not self.password:
            logger.warning("EmailService initialized in MOCK MODE (No SMTP credentials). Emails will be logged but not sent.")
        else:
            logger.info(f"EmailService initialized in PRODUCTION MODE. Using SMTP host {self.host}:{self.port}")

    async def send_candidate_password_email(self, candidate_email: str, candidate_name: str, username: str, password: str, resume_path: str = None):
        """
        Sends password email to candidate and forwards a notification (with optional resume) to developers.
        """
        subject = "Welcome to Interview Automation Platform - Your Login Credentials"
        body = (
            f"Dear {candidate_name},\n\n"
            f"Welcome to the Interview Automation Platform. Your account has been created successfully.\n\n"
            f"Login Credentials:\n"
            f"------------------\n"
            f"Username: {username}\n"
            f"Password: {password}\n\n"
            f"Please use these credentials to login and complete your technical assessment at:\n"
            f"{settings.FRONTEND_URL}\n\n"
            f"Best regards\n"
        )
        
        # 1. Send to candidate
        candidate_success = await self._send_email(candidate_email, subject, body)
        
        # 2. Forward to developers if configured
        if self.developer_emails:
            dev_subject = f"[Candidate Registration] {candidate_name} ({candidate_email})"
            dev_body = (
                f"A new candidate has been registered in the system.\n\n"
                f"Name: {candidate_name}\n"
                f"Email: {candidate_email}\n"
                f"Password Generated: {password}\n\n"
                f"This is an automated notification."
            )
            
            # Resolve absolute path for resume if provided
            abs_resume_path = None
            if resume_path:
                abs_resume_path = os.path.normpath(os.path.join(settings.BASE_DIR, resume_path))
                if not os.path.exists(abs_resume_path):
                    logger.warning(f"Resume file not found at {abs_resume_path}, skipping attachment.")
                    abs_resume_path = None

            # Forward to all developers
            tasks = []
            for dev_email in self.developer_emails:
                tasks.append(self._send_email(dev_email, dev_subject, dev_body, attachment_path=abs_resume_path))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        return candidate_success

    async def _send_email(self, recipient: str, subject: str, message_body: str, attachment_path: str = None):
        """
        Internal helper to send a single email with optional attachment. 
        Falls back to logging if credentials are missing or in case of error.
        """
        # If no credentials, just log it (Mock behavior)
        if not self.user or not self.password:
            logger.debug(f"\n" + "="*50)
            logger.debug(f" [MOCK EMAIL] To: {recipient}")
            logger.debug(f" Subject: {subject}")
            logger.debug(f" Body: {message_body}")
            if attachment_path:
                logger.debug(f" Attachment: {attachment_path}")
            logger.debug("="*50 + "\n")
            return True

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.mail_from or self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(message_body, 'plain'))

            # Attach file if provided
            if attachment_path and os.path.exists(attachment_path):
                from email.mime.application import MIMEApplication
                import os
                filename = os.path.basename(attachment_path)
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)

            # Send via SMTP
            def _send():
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.send_message(msg)

            await asyncio.to_thread(_send)
            logger.info(f"Successfully sent email to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False

email_service = EmailService()
