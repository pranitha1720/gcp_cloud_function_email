import base64
import logging
import os
import random
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from kms_utils import decrypt_symmetric

log = logging.getLogger(__name__)
_class_name = ""


def generate_mail_content(message):
    email_content = """
    <br><br>
    """ + """<table border="1" cellspacing="0" cellpadding="3">
      <tr bgcolor="#99daff"><th>Class name/ Attributes </th><th>Failure log</th></tr>
      <tr ><td>""" + _class_name + """</td><td>""" + message + """</td></tr>
    </table>
    """ + """ 
    <br><br>
    Regards,<br>
    Pranitha </h5>
        """

    return email_content


def smtp_connection(host, port, user, password):
    s = smtplib.SMTP(host=host, port=port)
    s.starttls()
    s.login(user, password)
    return s

def smtp_send(host, port, user, password, msg):
    while True:
        try:
            s = smtp_connection(host, port, user, password)
            s.send_message(msg)
            s.quit()
            break
        except smtplib.SMTPDataError as err:
            # Office365 imposes a limit on simultaneous connections
            # https://stackoverflow.com/questions/56088272/432-4-3-2-storedrv-clientsubmit-sender-thread-limit-exceeded

            log.info("SMTP error %d, will retry sending email", err.smtp_code);

            # Wait randomly between 1 - 5 sec and retry
            time.sleep(random.randrange(1, 5))

def send_mail(event, context):
    global _class_name
    log.info(event)
    project = os.environ.get('project', 'Specified environment variable is not set. Project name is missing.')

    location = os.environ.get('location', 'Specified environment variable is not set. Location is missing,eg. global.')

    crypto_key_ring = os.environ.get('crypto_key_ring',
                                     'Specified environment variable is not set. Crypto key ring is missing.')
    crypto_key = os.environ.get('crypto_key', 'Specified environment variable is not set. Crypto key is missing.')

    email_credential = os.environ.get('email_credential',
                                      'Specified environment variable is not set. Encrypted email credential/passord '
                                      'encrypted is missing')
    user = os.environ.get('from',
                          'Specified environment variable is not set. User/email-id for source/sender is missing.')
    cc = os.environ.get('cc', 'Specified environment variable is not set. CC list is missing.')
    bcc = os.environ.get('bcc', 'Specified environment variable is not set. Bcc list is missing')
    subject = os.environ.get('subject', 'Specified environment variable is not set. Subject is missing')
    host = os.environ.get('smtp_host', 'Specified environment variable is not set. SMTP host is missing')
    port = os.environ.get('smtp_port', 'Specified environment variable is not set. SMTP port is missing')

    email_credential_encode = email_credential.encode()

    email_credential_bytes = base64.decodebytes(email_credential_encode)

    password = decrypt_symmetric(project, location, crypto_key_ring, crypto_key, email_credential_bytes).decode(
        'utf-8')
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    attributes = event['attributes']
    for key in attributes:
        log.info("key: %s , value: %s" % (key, attributes[key]))
        _class_name = key

    log.info("Pub Sub Message %s", pubsub_message)
    # Set up the SMTP server
    log.info('Sending emails...')

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = cc
    msg['Bcc'] = bcc
    msg['Subject'] = subject.format(_class_name)

    msg.attach(MIMEText(generate_mail_content(pubsub_message), 'html'))
    log.info((type(msg)))

    smtp_send(host, port, user, password, msg)
