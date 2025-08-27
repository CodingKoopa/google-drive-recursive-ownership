#!/usr/bin/python

import os
import pprint
import sys

import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
from google_auth_oauthlib.flow import InstalledAppFlow
import six

OAUTH2_SCOPE = "https://www.googleapis.com/auth/drive"
CLIENT_SECRETS = "client_secrets.json"
CLIENT_CREDENTIALS = "cred.json"


def get_drive_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, scopes=[OAUTH2_SCOPE])
    credentials = flow.run_local_server()

    drive_service = googleapiclient.discovery.build('drive', 'v2', credentials=credentials)
    return drive_service


def get_permission_id_for_email(service, email):
    try:
        id_resp = service.permissions().getIdForEmail(email=email).execute()
        return id_resp["id"]
    except googleapiclient.errors.HttpError as e:
        print("An error occured: {}".format(e))


def show_info(service, drive_item, prefix, permission_id):
    try:
        print(os.path.join(prefix, drive_item["title"]))
        print("Would set new owner to {}.".format(permission_id))
    except KeyError:
        print("No title for this item:")
        pprint.pprint(drive_item)


def grant_ownership(service, drive_item, prefix, permission_id, show_already_owned):
    full_path = os.path.join(os.path.sep.join(prefix), drive_item["title"]).encode(
        "utf-8", "replace"
    )

    # pprint.pprint(drive_item)

    current_user_owns = False
    for owner in drive_item["owners"]:
        if owner["permissionId"] == permission_id:
            if show_already_owned:
                print("Item {} already has the right owner.".format(full_path))
            return
        elif owner["isAuthenticatedUser"]:
            current_user_owns = True

    print("Item {} needs ownership granted.".format(full_path))

    if not current_user_owns:
        print("    But, current user does not own the item.".format(full_path))
        return

    try:
        permission = (
            service.permissions()
            .get(fileId=drive_item["id"], permissionId=permission_id)
            .execute()
        )
        permission["role"] = "writer"
        permission["pendingOwner"] = "true"
        print("    Upgrading existing permissions to ownership.")
        return (
            service.permissions()
            .update(
                fileId=drive_item["id"],
                permissionId=permission_id,
                body=permission,
                transferOwnership=True,
            )
            .execute()
        )
    except googleapiclient.errors.HttpError as e:
        if e.resp.status != 404:
            print("An error occurred updating ownership permissions: {}".format(e))
            return

    print("    Creating new ownership permissions.")
    permission = {"role": "owner", "type": "user", "id": permission_id}
    try:
        service.permissions().insert(
            fileId=drive_item["id"],
            body=permission,
            emailMessage="Automated recursive transfer of ownership.",
        ).execute()
    except googleapiclient.errors.HttpError as e:
        print("An error occurred inserting ownership permissions: {}".format(e))


def process_all_files(
    service,
    callback=None,
    callback_args=None,
    minimum_prefix=None,
    current_prefix=None,
    folder_id="root",
):
    if minimum_prefix is None:
        minimum_prefix = []
    if current_prefix is None:
        current_prefix = []
    if callback_args is None:
        callback_args = []

    print("Listing: {} ...".format(os.path.sep.join(current_prefix)))

    page_token = None
    while True:
        try:
            param = {}
            if page_token:
                param["pageToken"] = page_token
            children = service.children().list(folderId=folder_id, **param).execute()
            for child in children.get("items", []):
                item = service.files().get(fileId=child["id"]).execute()
                # pprint.pprint(item)
                if item["kind"] == "drive#file":
                    if current_prefix[: len(minimum_prefix)] == minimum_prefix:
                        _segments = current_prefix + [item["title"]]
                        print(
                            "File: {} ({})".format(
                                os.path.sep.join(_segments), item["id"]
                            )
                        )
                        callback(service, item, current_prefix, **callback_args)
                    if item["mimeType"] == "application/vnd.google-apps.folder":
                        next_prefix = current_prefix + [item["title"]]
                        comparison_length = min(len(next_prefix), len(minimum_prefix))
                        if (
                            minimum_prefix[:comparison_length]
                            == next_prefix[:comparison_length]
                        ):
                            process_all_files(
                                service,
                                callback,
                                callback_args,
                                minimum_prefix,
                                next_prefix,
                                item["id"],
                            )
                        else:
                            _segments = current_prefix + [item["title"]]
                            print(
                                "Ignore folder: {} ({})".format(
                                    os.path.sep.join(_segments), item["id"]
                                )
                            )

            page_token = children.get("nextPageToken")
            if not page_token:
                break
        except googleapiclient.errors.HttpError as e:
            print("An error occurred: {}".format(e))
            break


def main():
    if len(sys.argv) < 3:
        raise ValueError(
            "Missing args, see https://github.com/svaponi/google-drive-recursive-ownership?tab=readme-ov-file#usage"
        )
    minimum_prefix = six.text_type(sys.argv[1])
    new_owner = six.text_type(sys.argv[2])
    show_already_owned = (
        False if len(sys.argv) > 3 and six.text_type(sys.argv[3]) == "false" else True
    )
    print(f'Changing all files at path "{minimum_prefix}" to owner "{new_owner}"')
    minimum_prefix_split = minimum_prefix.split(os.path.sep)
    print(f"Prefix: {minimum_prefix}")
    service = get_drive_service()
    permission_id = get_permission_id_for_email(service, new_owner)
    print(f"User {new_owner} is permission ID {permission_id}.")
    process_all_files(
        service,
        grant_ownership,
        {"permission_id": permission_id, "show_already_owned": show_already_owned},
        minimum_prefix_split,
    )
    print(
        f"Go to https://drive.google.com/drive/search?q=pendingowner:me (as {new_owner}), select all files, click 'Share' and accept ownership."
    )
    # print(files)


if __name__ == "__main__":
    main()
