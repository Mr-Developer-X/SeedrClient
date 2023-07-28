import os
import re
import json
import aria2p
import requests
import tempfile
import subprocess
from time import sleep
from random import randrange
from torrentool.api import Torrent
from .errors import (
    InvalidLogin,
    InvalidToken,
    LoginRequired,
    InvalidTorrent,
    DriveLimit,
    BadLeeching
)


class SeedrHandler:
    def __init__(self, email=None, password=None, access_token=None, aria2c_secret=None, download_directory="."):
        self.rate_limit = 1
        self.email = email
        self.password = password
        self.access_token = access_token
        self.base_folder_url = "https://www.seedr.cc/api/folder"
        self.base_oauth_url = "https://www.seedr.cc/oauth_test"
        # This is the list of file types Seedr client is not allowed to download,
        # alter this to your requirements, or leave blank if you want Seedr clients
        # should download all files types
        # TODO Replace this argument from environment instead
        self.exclude_file_type = ["jpg", "png", "txt", "exe"]
        self.get_token()
        self.magnet_regex = re.compile(r"magnet:\?xt=urn:[a-z0-9]+:[a-zA-Z0-9]{32}")
        self.torrent_regex = re.compile(r".*torrent$")
        self.drive_size = 0
        self.get_drive()  # This finishes init of the Seedr client, by setting up the drive size
        sleep(self.rate_limit)
        self.aria2 = None
        self.aria2c_secret = aria2c_secret
        self.seedr_download_options = {"user_agent": "Mozilla/5.0"}
        self.download_directory = download_directory

    @staticmethod
    def contains_bad_token(response_text):
        return any(fail_resp in response_text for fail_resp in ["invalid_token", "expired_token"])

    @staticmethod
    def bytes_to_mb_gb(byte):
        """
        A simple function that converts Bytes to Megabytes if value
        is less than 1 Gigabyte else returns value in Gigabytes

        :param byte: The value in Bytes to be converted
        :type byte: int
        :return: The converted value in MB or GB based on logic
        :rtype: str
        """
        mb = byte / (1024 ** 2)
        if mb >= 1024:
            gb = mb / 1024
            return f"{round(gb, 2)} GB"
        return f"{round(mb, 2)} MB"

    def list_contents(self, response_json):
        """
        This method takes the response provided by the api request and sanitizes it,
        to only returns the relevant details pertaining to the folder structure
        :param response_json: The response from the api requests passed in json format
        :type response_json: dict
        :return: The folder structure of the folder pertaining to the api response
        :rtype: dict
        """
        content = {
            "folders": [
                {
                    "folder_id": folder["id"],
                    "folder_name": folder["name"],
                    "size": self.bytes_to_mb_gb(folder["size"])
                } for folder in response_json["folders"]
            ],
            "files": [
                {
                    "folder_file_id": file["folder_file_id"],
                    "file_name": file["name"],
                    "size": self.bytes_to_mb_gb(file["size"]),
                    "folder_path": response_json["fullname"]
                } for file in response_json["files"]
            ]
        }
        return content

    @staticmethod
    def is_op_success(response_text):
        """
        Checks if there is a success code in the response provided by the api call and returns the appropriate boolean
        :param response_text: The response from the api call in text format
        :type response_text: str
        :return: Returns true if success, false otherwise
        :rtype: bool
        """
        if json.loads(response_text)["result"]:
            return True
        else:
            return False

    def is_login_success(self):
        """
        Checks if the access token is valid

        :return: Returns True if the token is valid, False if it isn't
        :rtype: bool
        """
        response = requests.get(f"{self.base_folder_url}?access_token={self.access_token}")
        if self.contains_bad_token(response_text=response.text):
            return False
        else:
            return True

    def is_request_failed(self, response_text, requested_on):
        """
        Checks for any failed codes in the response and if there is any, then it raises
        the appropriate error code with detail, else returns false

        :param response_text: The text response received by Seedr api to the request made by the previous method
        :type response_text: str
        :param requested_on: A string that is either "file" or "folder" based on what kinda file system operations was
        going on in the previous method
        :type requested_on: str
        :return: Returns False if no fail code
        :rtype: bool
        """
        if "access_denied" in response_text:
            # TODO add a way to notify when this happens
            raise FileNotFoundError(f"{requested_on.title()} not found in drive")
        elif self.contains_bad_token(response_text=response_text):
            # TODO add a way to notify when this happens
            raise InvalidToken("Invalid/Expired access token.")
        else:
            return False

    def get_token(self):
        """
        Gets the access token if email and password is passed during init, else if token itself was provided instead
        verifies that the access token is valid and if an error occurs during the previous process or if none of the
        required details are passed during init of client raises an error.
        """
        if self.email and self.password:
            data = {
                "grant_type": "password",
                "client_id": "seedr_chrome",
                "type": "login",
                "username": self.email,
                "password": self.password
            }
            response = requests.post(f"{self.base_oauth_url}/token.php", data=data)
            if "access_token" in response.text:
                self.access_token = json.loads(response.text)["access_token"]
            else:
                # TODO add a way to notify when this happens
                raise InvalidLogin("Invalid username and password combination.")
        elif self.access_token:
            if not self.is_login_success():
                # TODO add a way to notify when this happens
                raise InvalidToken("Invalid/Expired access token.")
        else:
            # TODO add a way to notify when this happens
            raise LoginRequired("Account login or token is required.")

    def get_drive(self):
        """
        Gets details about the drive's space, active torrents, and all downloaded files and folders
        Note: This is the same as the get_folder method except seedr api does not ask for a folder id,
        additionally we are able top display a few additional details, including active torrents

        :return: A dictionary containing, available and used drive space, active torrents and its details, downloaded
        folders and files and their details
        :rtype: dict
        """
        response = requests.get(f"{self.base_folder_url}?access_token={self.access_token}")
        if self.contains_bad_token(response_text=response.text):
            # TODO add a way to notify when this happens
            raise InvalidToken("Invalid/Expired access token.")
        else:
            response_json = json.loads(response.text)
            drive = {
                "space": {
                    "total": self.bytes_to_mb_gb(response_json["space_max"]),
                    "used": self.bytes_to_mb_gb(response_json["space_used"])
                },
                "parent_folder_id": response_json["folder_id"] if response_json["parent"] == -1 else None,
                "torrents": [
                    {
                        "name": torrent["name"],
                        "torrent_id": torrent["id"],
                        "progress": torrent["progress"],
                        "progress_url": torrent["progress_url"]
                    } for torrent in response_json["torrents"]
                ]
            }
            drive = drive | self.list_contents(response_json=response_json)
            self.drive_size = response_json["space_max"]
            return drive

    def get_folder(self, folder_id):
        """
        This method lists all the content of the folder as a dictionary associated with
        the folder id that is passed if it exists

        :param folder_id: The unique id associated with the folder that you need the info about
        :type folder_id: int
        :return: A dictionary contains a list of all files and folders in the associated folder
        :rtype: dict
        """
        response = requests.get(f"{self.base_folder_url}/{str(folder_id)}?access_token={self.access_token}")
        response_text = response.text
        if not self.is_request_failed(response_text=response_text, requested_on="folder"):
            response_json = json.loads(response_text)
            if folder_id == response_json["folder_id"]:
                folder = {
                    "folder_name": response_json["fullname"]
                }
                folder = folder | self.list_contents(response_json=response_json)
                return folder
            else:
                # TODO add a way to notify when this happens
                raise LookupError("Provided folder id does not match the received folder id")

    def get_file(self, folder_file_id):
        """
        This method returns the name and the download url associated with the file id that is passed

        :param folder_file_id: The unique id associated with the file you need the info about
        :type folder_file_id: int
        :return: A dictionary containing file name and download url
        :rtype: dict
        """
        data = {"access_token": self.access_token, "func": "fetch_file", "folder_file_id": str(folder_file_id)}
        response = requests.post(f"{self.base_oauth_url}/resource.php", data=data)
        response_text = response.text
        if not self.is_request_failed(response_text=response_text, requested_on="file"):
            response_json = json.loads(response_text)
            file = {
                "name": response_json["name"],
                "download_url": response_json["url"]
            }
            return file

    def add_torrent(self, torrent=None, wishlist_id=None, folder_id=-1):
        """
        This function allows you to pass either torrent file or magnet uri or a wishlist id, to start downloading
        by Seedr. It returns the name and ID of the torrent on success.

        Note: If magnet uri is passed instead of a torrent file which is the preferred method, and if the peers in the
        torrent is lower than 3 or if the torrent is completely dead then this function might not be able to add the
        torrent due to the underlying logic which requires the meta info of the torrent. This is a drawback of this
        approach as this helps avoid wasting time checking if there is enough storage space, but can't use the Seedr's
        cache, which works even if there is no seeders. If there is enough requests to correct this approach I will add
        a timeout logic to the method in next iteration. For now try supplying torrents file instead of the magnet uri.

        :param torrent: The torrent file or magnet uri that you want to add to be leeched/downloaded
        :type torrent: str
        :param wishlist_id: The wishlist id that you want to add from your Seedr wishlist
        :type wishlist_id: int
        :param folder_id: The folder you want the torrent to be downloaded to. Defaults to parent.
        :type folder_id: int
        :return:
        :rtype:
        """
        if torrent:
            if self.torrent_regex.match(torrent):
                pass
            elif self.magnet_regex.match(torrent):
                # TODO Add a timeout wrapper, which will jump right to adding the torrent instead
                temp_torrent_file_path = os.path.join(tempfile.gettempdir(), f"temp{randrange(1, 10**4):04}.torrent")
                subprocess.run(["ih2torrent", "--file", temp_torrent_file_path, torrent])
                torrent = temp_torrent_file_path
            else:
                raise InvalidTorrent(
                    f"The torrent passed is invalid, please verify it fix it.\nTorrent/Magnet: {torrent}"
                )
            torrent_info = Torrent.from_file(torrent)
            if self.drive_size >= torrent_info.total_size:
                torrent_magnet_uri = torrent_info.magnet_link
            else:
                print(self.drive_size, torrent_info.total_size)
                raise DriveLimit("The torrent is larger than the total available space in the drive")
        elif wishlist_id:
            torrent_magnet_uri = None
        else:
            raise TypeError("add_torrent() is missing an argument. At least one argument needs to be passed")

        data = {
            'access_token': self.access_token,
            'func': 'add_torrent',
            'torrent_magnet': torrent_magnet_uri,
            'wishlist_id': wishlist_id,
            'folder_id': folder_id
        }

        response = requests.post(f"{self.base_oauth_url}/resource.php", data=data)
        response_json = json.loads(response.text)
        if response_json["result"]:
            return {
                "torrent_id": response_json["user_torrent_id"],
                "file_name": response_json["title"]
            }
        else:
            raise BadLeeching(f"The provided Torrent couldn't be leeched/downloaded to the drive.\n {data=}")

    def download_folder(self, folder_id, builtin_downloader=True):
        content = self.get_folder(folder_id=folder_id)
        sleep(self.rate_limit)
        download_list = content["files"]
        next_list_folders = content["folders"]
        while True:
            if next_list_folders:
                temp_list_folders = []
                for folder in next_list_folders:
                    subfolder_content = self.get_folder(folder_id=folder["folder_id"])
                    sleep(self.rate_limit)
                    temp_list_folders += subfolder_content["folders"]
                    download_list += subfolder_content["files"]
                next_list_folders = temp_list_folders
            else:
                break
        # This loop checks if there is any file that matches the list of extensions that are to be excluded and if
        # present will remove them from the list
        temp_download_list = []
        for item in download_list:
            temp_item_ext = item["file_name"].split(".")[-1]
            if temp_item_ext not in self.exclude_file_type:
                item["folder_path"] = os.path.join(self.download_directory, *item["folder_path"].split("/"), "")
                temp_download_list.append(item)
        download_list = temp_download_list
        for i in range(len(download_list)):
            download_list[i]["download_url"] = self.get_file(download_list[i]["folder_file_id"])["download_url"]
            sleep(self.rate_limit)
        if not builtin_downloader:
            return download_list
        download_list = sorted(download_list, key=lambda d: d["size"])
        # Only runs if aria2p client hasn't already been initiated
        if not self.aria2:
            self.aria2 = aria2p.API(
                aria2p.Client(
                    host="http://localhost",
                    port=6800,
                    secret=self.aria2c_secret
                )
            )
        download_queue = []
        # Adds each url obtained from previous steps one by one with priorities given for smallest files first
        for i in range(len(download_list)):
            download_adder = self.aria2.add(
                uri=download_list[i]["download_url"],
                # TODO make the directory data dynamic, such that each file is downloaded to the appropriate folder
                options={"dir": download_list[i]["folder_path"]},
                position=i
            )
            download_queue.append(download_adder[0].gid)
        while True:
            # TODO FUTURE show progress real time
            temp_download_queue = []
            for gid in download_queue:
                download_info = self.aria2.get_download(gid=gid)
                if not download_info.is_complete:
                    temp_download_queue.append(gid)
            download_queue = temp_download_queue
            if len(download_queue) == 0:
                break
            sleep(5)
        # TODO return parent directory instead
        return True

    def delete_folder(self, folder_id):
        """
        This method deletes the folder associated with the id that is passed and returns True on success

        :param folder_id: The id of the folder you wish to delete
        :type folder_id: int
        :return: Returns True or False based on success
        :rtype: bool
        """
        data = {
            "access_token": self.access_token,
            "func": "delete",
            "delete_arr": '[{"type":"folder","id":"' + str(folder_id) + '"}]'
        }
        # TODO Correct this stub to follow DRY
        # TODO add a conditional statement to prevent deletion of parent folder
        response = requests.post(f"{self.base_oauth_url}/resource.php", data=data)
        response_text = response.text
        if not self.is_request_failed(response_text=response_text, requested_on="folder"):
            return self.is_op_success(response_text=response_text)

    def delete_file(self, folder_file_id):
        """
        This method deletes the file associated with the id that is passed and returns True on success

        :param folder_file_id: The id of the file you wish to delete
        :type folder_file_id: int
        :return: Returns True or False based on success
        :rtype: bool
        """
        data = {
            "access_token": self.access_token,
            "func": "delete",
            "delete_arr": '[{"type":"file","id":"' + str(folder_file_id) + '"}]'
        }
        # TODO Correct this stub to follow DRY
        response = requests.post(f"{self.base_oauth_url}/resource.php", data=data)
        response_text = response.text
        if not self.is_request_failed(response_text=response_text, requested_on="file"):
            return self.is_op_success(response_text=response_text)

    def delete_torrent(self, torrent_id):
        """
        This method deletes any active torrent associated with the id that is passed and returns True on success

        :param torrent_id: The id of the active torrent you wish to delete
        :type torrent_id: int
        :return: Returns True or False based on success
        :rtype: bool
        """
        data = {
            'access_token': self.access_token,
            'func': 'delete',
            'delete_arr': f'[{{"type":"torrent","id":{torrent_id}}}]'
        }
        response = requests.post(f"{self.base_oauth_url}/resource.php", data=data)
        response_text = response.text
        if not self.is_request_failed(response_text=response_text, requested_on="torrent"):
            return self.is_op_success(response_text=response_text)

    def delete_all(self):
        """
        This method deletes all the content within the drive, whether it downloaded
        to the drive or being downloaded.

        :return: Returns True if the method clears the whole drive successfully, False otherwise.
        :rtype: bool
        """
        content = self.get_drive()
        for folder in content["folders"]:
            self.delete_folder(folder["folder_id"])
            sleep(self.rate_limit)
        for file in content["files"]:
            self.delete_file(file["folder_file_id"])
            sleep(self.rate_limit)
        for torrent in content["torrents"]:
            self.delete_torrent(torrent["torrent_id"])
            sleep(self.rate_limit)
        content = self.get_drive()
        if content["space"]["used"] == "0.0 GB":
            return True
        return False
