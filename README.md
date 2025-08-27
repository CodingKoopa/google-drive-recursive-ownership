# Fork Notes

This fork incorporates a couple of fixes:
- The ["Consent is required to transfer ownership of a file to another user." error](https://github.com/davidstrauss/google-drive-recursive-ownership/issues/44), fixed by @svaponi in his fork (which this is based on).
- The ["Error 400: invalid_request", "The out-of-band (OOB) flow has been blocked in order to keep users secure." error](https://github.com/davidstrauss/google-drive-recursive-ownership/issues/42), fixed by @wildintellect in [his fork](https://github.com/wildintellect/google-drive-recursive-ownership/tree/fix/oob). This change has been pulled in.

Still, you may encounter the following error after confirming in your browser:

```
Traceback (most recent call last):
  File "/home/koopa/code/python/google-drive-recursive-ownership/transfer.py", line 197, in <module>
    main()
    ~~~~^^
  File "/home/koopa/code/python/google-drive-recursive-ownership/transfer.py", line 181, in main
    service = get_drive_service()
  File "/home/koopa/code/python/google-drive-recursive-ownership/transfer.py", line 20, in get_drive_service
    credentials = flow.run_local_server()
  File "/home/koopa/code/python/google-drive-recursive-ownership/.venv/lib/python3.13/site-packages/google_auth_oauthlib/flow.py", line 464, in run_local_server
    authorization_response = wsgi_app.last_request_uri.replace("http", "https")
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'replace'
```

This appears to be a [race condition within google_auth_oauthlib](https://github.com/googleapis/google-auth-library-python-oauthlib/issues/69). I worked around this with a pretty silly change to [`.venv/lib/python3.13/site-packages/google_auth_oauthlib/flow.py`](https://github.com/googleapis/google-auth-library-python-oauthlib/blob/4b1a5f33f282af79999d7ed80d11a246a7e301a2/google_auth_oauthlib/flow.py#L453C13-L453C42) (yes, you should use a virtualenv!):

```diff
-            local_server.handle_request()
+            try:
+                local_server.serve_forever()
+            except KeyboardInterrupt:
+                pass
```

With this applied, once you go through the flow in your browser, you can tab back to your terminal and issue an interrupt with Ctrl+C. This gives enough time for the callback to run.

# Google Drive Recursive Ownership Tool

### Supported Files

G Suite for Government and G Suite for Education accounts can change ownership of any file owned by the current user, including uploaded/synced files suchs as PDFs.

Other Google Accounts such as G Suite for Business or Personal Google Accounts can only transfer ownership of Google files (Docs, Sheets, Sildes, Forms, Drawings, My Maps, and folders).

NOTE: Ownership can only be transferred to members of the same G Suite or Google domain. Ex. @gmail.com can only transfer to other @gmail.com addresses.

NOTE: The Google Drive API does not allow suppressing notifications for change of ownership if the _if_ the new owner does not already have access to the file. However, if the new owner _already_ has access to the file, upgrading their permissions to ownership will _not_ generate a notification.

### Setup

```shell
git clone https://github.com/svaponi/google-drive-recursive-ownership
cd google-drive-recursive-ownership
pip install -r requirements.txt
```

Alternatively, if you have [poetry](https://python-poetry.org/docs/) installed, run:

```shell
git clone https://github.com/svaponi/google-drive-recursive-ownership
cd google-drive-recursive-ownership
poetry install
```

To update the `requirements.txt`, run:

```commandline
poetry export -f requirements.txt --output requirements.txt --without-hashes
```


### Usage

First, replace the [sample](https://github.com/gsuitedevs/python-samples/blob/d4fa75401e9b637f67da6fe021801d8b4cbd8cd0/drive/driveapp/client_secrets.json) `client_secrets.json` with your own [client secrets](https://github.com/googleapis/google-api-python-client/blob/master/docs/client-secrets.md). Otherwise, authorizations you create will be usable by anyone with access to the sample key (the entire internet).

Next, if `transfer.py` is contained in a folder listed in your system's `PATH` this can be run from anywhere. Otherwise it needs to be run from the directory where `transfer.py` is located.

    python  transfer.py  PATH-PREFIX  NEW-OWNER-EMAIL  SHOW-ALREADY-OWNER
    
 - `PATH-PREFIX` assumes use of "/" or "\" as appropriate for your operating system.

   * The `PATH-PREFIX` folder must be in **My Drive** section. For shared folders right click and select _Add to My Drive_.

 - `SHOW-ALREADY-OWNER` "`true`"|"`false`" (default `true`) to hide feedback for files already set correctly.
    
Windows Example:

    python transfer.py "Folder 1\Folder 2\Folder 3" new_owner@example.com true

Mac/Linux Example:

    python transfer.py "Folder 1/Folder 2/Folder 3" new_owner@example.com false
