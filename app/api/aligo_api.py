import os.path
from pathlib import Path

from aligo import Aligo


class AligoAPI:
    """阿里云盘 API 封装"""

    def __init__(self, username: str):
        self.base_path = "horpt"
        self.home_path = f"{self.base_path}/{username}"
        try:
            self.aligo = Aligo(name="aligo", port=8080, re_login=False)
            if not self._get_file_by_path(remote_folder_path=self.home_path):
                self.aligo.create_folder(name=self.home_path)
        except Exception as e:
            print(e)

    def _get_file_by_path(self, remote_folder_path):
        try:
            file = self.aligo.get_file_by_path(remote_folder_path)
            if file is None:
                return False
            else:
                return True
        except Exception as e:
            print(e)
            return False

    def get_file_list(self, remote_folder_path):
        try:
            remote_folder = self.aligo.get_folder_by_path(remote_folder_path)
            file_list = self.aligo.get_file_list(parent_file_id=remote_folder.file_id)  # 获取网盘根目录文件列表
            file_list = [(file.file_id, file.name, file.type) for file in file_list]
            return file_list
        except Exception as e:
            print(e)
            return []

    def upload_file(self, local_path: str, remote_folder_path=None, parent_file_id=None, is_create_folder=False):
        '''
        上传文件/文件夹到指定网盘目录/位置
        :param local_path: 本地文件/文件夹路径
        :param remote_folder_path: 网盘目标目录路径
        :param parent_file_id: 网盘目标位置的父级文件ID
        :return:
        '''
        try:
            if os.path.exists(local_path):
                local_path = os.path.abspath(local_path)
            if parent_file_id:
                self.aligo.upload_folder(local_path, parent_file_id=parent_file_id)
            elif remote_folder_path:
                if is_create_folder:  # 创建文件夹
                    if not self._get_file_by_path(remote_folder_path):
                        self.aligo.create_folder(name=remote_folder_path)
                remote_folder = self.aligo.get_folder_by_path(remote_folder_path)  # 获取网盘目标文件夹
                if remote_folder is None:
                    raise RuntimeError('指定的网盘文件夹不存在')
                self.aligo.upload_folder(local_path, parent_file_id=remote_folder.file_id)
            else:
                raise RuntimeError('请指定上传目标文件夹')
            return True
        except Exception as e:
            print(e)
            return False

    def download_file(self, remote_file_path: str, local_path: str):
        try:
            if not os.path.isdir(local_path):
                raise RuntimeError('请指定正确的下载目标文件夹')
            config_dir = Path(local_path)
            config_dir.mkdir(parents=True, exist_ok=True)
            file = self.aligo.get_folder_by_path(remote_file_path)
            if file is None:
                raise RuntimeError('指定的网盘文件夹不存在')
            self.aligo.download_folder(folder_file_id=file.file_id, local_folder=local_path)
        except Exception as e:
            print(e)
            return False


if __name__ == '__main__':
    # ali = Aligo(name="hwb", port=8080, re_login=False)
    # user = ali.get_user()  # 获取用户信息
    # print(user.user_name, user.nick_name, user.phone)  # 打印用户信息
    username = os.getlogin()
    aligo_api = AligoAPI(username=username)
    ## 上传文件夹
    # aligo_api.upload_file(local_path="../api", remote_folder_path=f"{aligo_api.home_path}/a/b/v", is_create_folder=True)
