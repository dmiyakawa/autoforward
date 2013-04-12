#!/usr/bin/python
#
#   Copyright 2013 Daisuke Miyakawa
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
A very simple program that forwards a given email to another address.
No MIME handling will be done, so forwarded mail may not be readable :-P

Might be useful if you want to setup a mail server that just
needs to wait a simple email (confirmation, etc.) from someone else.

No production quality.

E.g.
> sudo ./autoforward.py smtp.example.com yourname@example.com
(all emails coming to this server will be forwarded to the specified server
with the new recipient address)
"""

import asyncore
import email.utils
from email.mime.text import MIMEText
from optparse import OptionParser
import os.path
import smtpd
import smtplib
import sys
import time
from threading import Timer

class CustomSMTPServer(smtpd.SMTPServer):
    def __init__(self, localaddr, remoteaddr,
                 smtp_server, to_addr, from_addr):
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        self._smtp_server = smtp_server
        self._to_addr = to_addr
        self._timer = None
        pass

    def send_forwarded_message(self, data, do_resend):
        if self._timer:
            self._timer = None
            pass
        msg = MIMEText(data, 'rfc2822')
        msg['To'] = email.utils.formataddr(('Auto Forward', to_addr))
        msg['From'] = email.utils.formataddr(('Auto Forward', from_addr))

        msg['Date'] = email.utils.formatdate(time.time(), True)
        msg['Subject'] = 'Automatically Forwarded Message'

        print 'Forwarding the message to %s' % self._smtp_server
        server = smtplib.SMTP(self._smtp_server)
        server.set_debuglevel(True)
        try:
            server.sendmail(from_addr, [to_addr],
                            msg.as_string())
        except smtplib.SMTPRecipientsRefused, e:
            print 'SMTPRecipientsRefused: ', e
            # may be greylisting. Try it again after a while.
            if e.recipients[to_addr][0] == 450 and do_resend:
                print 'Try resending it after 360 sec'
                f = (lambda data: self.send_forwarded_message(data, False))
                self._timer = Timer(360, f, [data])
                self._timer.start()
            else:
                print "Give up sending the data"
                pass
            pass
        finally:
            server.quit()
            pass
        pass

    def process_message(self, peer, mailfrom, rcpttos, data):
        print 'Receiving message from:', peer
        print 'Message addressed from:', mailfrom
        print 'Message addressed to  :', rcpttos
        # print 'Message length        :', len(data)
        print 'Message               :', data
        print
        print
        self.send_forwarded_message(data, True)
        return

    def cancel(self):
        if self._timer:
            print 'canceling timer..'
            self._timer.cancel()
            pass
        pass
    pass


if __name__ == '__main__':
    usage = 'usage: %prog [options] smtp_server to_addr'
    parser = OptionParser(usage)
    parser.add_option('-o', '--out', dest='out', metavar='FILE',
                      help='FILE will be used for stdout destination')
    parser.add_option('-e', '--err', dest='err', metavar='FILE',
                      help='FILE will be used for stderr destination')
    parser.add_option('-n', '--hostname', dest='hostname', metavar='HOST',
                      default='127.0.0.1',
                      help='listen to ADDR for incoming message')
    parser.add_option('-p', '--port', dest='port', metavar='PORT',
                      default='25',
                      help='listen to PORT for incoming message')
    parser.add_option('-f', '--from', dest='from_addr', metavar='FROM',
                      help=''.join(['forwarded email will be sent from FROM.'
                                    'If not set, to_addr will be used.']))

    (options, args) = parser.parse_args()

    if (options.out):
        sys.stdout = file(options.out, 'a')
        pass
    if (options.err):
        sys.stderr = file(options.err, 'a')
        pass

    print '%s started at %s' % (os.path.basename(sys.argv[0]),
                                email.utils.formatdate(time.time(), True))
    print 'options: %s' % str(options)

    if (len(args) < 2):
        parser.error("insufficient argument(s)")
        pass
    
    smtp_server = args[0]
    to_addr = args[1]
    if (options.from_addr):
        from_addr = options.from_addr
    else:
        from_addr = to_addr
        pass

    # nmap (from outside this program) causes an exception inside
    # asyncore.loop(). This code will relaunch it again.
    while True:
        try:
            server = CustomSMTPServer((options.hostname, int(options.port)),
                                      None,
                                      smtp_server, to_addr, from_addr)
            asyncore.loop()

            print "asyncore.loop() terminated. Will relaunch again."
        except KeyboardInterrupt:
            print "KeyboardInterrupt. Exitting"
            server.cancel()
            sys.exit(0)
        except Exception:
            raise
        pass
    pass
