A very simple program that forwards a given email to another address.
No MIME handling will be done, so forwarded mail may be just unreadable :-P

    > sudo ./autoforward.py smtp.example.com yourname@example.com
    (all emails coming to this server will be forwarded to the specified server
    with the new recipient address)
