import os.path
from pathlib import Path

from aligo import Aligo


class AligoAPI:
    """阿里云盘 API 封装"""

    def __init__(self, home_path: str):
        try:
            self.aligo = Aligo(name="aligo", port=8080, re_login=False)
        except Exception as e:
            print(e)
        self.home_path = home_path

    def get_file_list(self):
        file_list = ali.get_file_list()  # 获取网盘根目录文件列表
        for file in file_list:  # 遍历文件列表
            # 注意：print(file) 默认只显示部分信息，但是实际上file有很多的属性
            print(file.file_id, file.name, file.type)  # 打印文件信息

    def upload_file(self, local_path: str, remote_folder_path=None, parent_file_id=None):
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
                remote_folder = self.aligo.get_folder_by_path(remote_folder_path)
                if remote_folder is None:
                    raise RuntimeError('指定的网盘文件夹不存在')
                ali.upload_folder(local_path, parent_file_id=remote_folder.file_id)
            else:
                raise RuntimeError('请指定上传目标文件夹')
            return True
        except Exception as e:
            print(e)
            return False

    def download_file(self, remote_file_path: str, local_path=None, parent_file_id=None):
        try:
            if not os.path.isdir(local_path):
                raise RuntimeError('请指定正确的下载目标文件夹')
            config_dir = Path(local_path)
            config_dir.mkdir(parents=True, exist_ok=True)
            file = ali.get_folder_by_path(remote_file_path)
            if file is None:
                raise RuntimeError('指定的网盘文件夹不存在')
            ali.download_folder(folder_file_id=file.file_id, local_folder=local_path)
        except Exception as e:
            print(e)
            return False


if __name__ == '__main__':
    ali = Aligo(name="hwb", port=8080, re_login=False)
    user = ali.get_user()  # 获取用户信息
    print(user.user_name, user.nick_name, user.phone)  # 打印用户信息
