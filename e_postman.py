# -*- coding: utf8 -*-
import smtplib
import os
import datetime
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate


def send_mail(send_from, send_to, subject, text, password, use_tls=True, files=None,
              server="smtp.126.com"):
    assert isinstance(send_to, list)

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    text = "<br><b>Hi,</b><br><br>&emsp;&emsp;" + text + "<br><br><b>From Joe</b><br>{}".format(
        (datetime.datetime.utcnow() + datetime.timedelta(hours=+8)).strftime("%a %Y-%m-%d %H:%M:%S %Z")
    )
    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    smtp = smtplib.SMTP(server)
    if use_tls:
        smtp.starttls()
    smtp.set_debuglevel(0)  # Set 1 for email log
    smtp.login(send_from, password)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


if __name__ == "__main__":
    send_from = os.environ.get("SEND_FROM")
    password = os.environ.get("SMTP_PASSWORD")
    send_to = os.environ.get("SEND_TO")
    print(send_to)
    send_to_list = send_to.split(",")
    GCR_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=+8)).strftime("%a %Y-%m-%d %H:%M:%S %Z")
    # text_list = [
    #     "Hi,",
    #     "    This is a email sending test.",
    #     f"    Time: {GCR_time}",
    #     f"\nFrom: {send_from}"
    # ]
    # text = "\n".join(text_list)
    # send_mail(send_from, send_to_list, "Email sending test", text, password)
    send_mail(send_from, send_to_list, "Email sending test", "This is a email sending test.", password)
