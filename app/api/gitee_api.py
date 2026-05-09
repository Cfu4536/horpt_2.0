import json
import logging
import base64
from typing import Dict, Optional, Union, Any
import requests


class GiteeAPI:
    """Gitee API v5 仓库文件操作封装"""

    BASE_URL = "https://gitee.com/api/v5/repos"

    def __init__(self, access_token: str, owner: str, repo: str):
        """
        初始化 Gitee API 客户端

        :param access_token: Gitee 私人令牌
        :param owner: 仓库所属空间地址 (企业或用户名)
        :param repo: 仓库路径
        """
        self.access_token = access_token
        self.owner = owner
        self.repo = repo
        self._base_repo_url = f"{self.BASE_URL}/{self.owner}/{self.repo}"

    def _get_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """构造通用请求头"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if extra:
            headers.update(extra)
        return headers

    def _handle_response(self, response: requests.Response) -> Union[Dict, str, None]:
        """统一处理响应，返回解析后的内容或状态码"""
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return response.json()
            return response.text
        logging.warning(f"请求失败: {response.status_code} - {response.url}")
        return None

    def get_file_content(self, file_path: str, format: str = "json") -> Union[str, Dict, bool]:
        """
        获取文件内容，支持返回 JSON 对象或原始字符串

        :param file_path: 仓库内文件路径
        :param format: 返回格式，可选 "json" 或 "str"
        :return: 格式化后的内容，失败返回 False
        """
        url = f"{self._base_repo_url}/contents/{file_path}"
        headers = self._get_headers({"Accept": "application/vnd.github.v3.raw"})
        try:
            logging.info(f"获取 Gitee 文件内容: {file_path}")
            response = requests.get(url, headers=headers, timeout=10)
            content_obj = response.json()
            decoded = base64.b64decode(content_obj["content"]).decode("utf-8")

            if format == "str":
                return decoded
            if format == "json":
                return json.loads(decoded)
            raise ValueError(f"不支持的格式: {format}")
        except Exception as e:
            logging.error(f"获取文件内容失败: {file_path}, 错误: {e}")
            return False

    def get_file_raw(self, file_path: str) -> Optional[bytes]:
        """
        获取文件的原始内容（Raw）

        :param file_path: 仓库内文件路径
        :return: 文件原始文本，失败返回 None
        """
        url = f"{self._base_repo_url}/raw/{file_path}"
        headers = self._get_headers({"Accept": "application/vnd.github.v3.raw"})
        try:
            logging.info(f"获取 Gitee 文件原始内容: {file_path}")
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.content
            logging.warning(f"获取原始内容失败: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"获取原始内容请求异常: {e}")
        return None

    def update_file_content(self, file_path: str, content: Dict[str, Any]) -> Union[int, bool]:
        """
        更新仓库文件内容

        :param file_path: 仓库内文件路径
        :param content: 要写入的字典内容（将被序列化为 JSON）
        :return: 成功返回 HTTP 状态码（通常200或201），失败返回 False
        """
        # 获取当前文件的 sha
        url = f"{self._base_repo_url}/contents/{file_path}"
        headers = self._get_headers()
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logging.error(f"获取文件信息失败: {resp.status_code}")
                return False
            current_info = resp.json()
            sha = current_info["sha"]
        except (requests.RequestException, KeyError) as e:
            logging.error(f"获取文件 sha 失败: {e}")
            return False

        # 准备更新数据
        try:
            json_str = json.dumps(content, ensure_ascii=False, indent=4)
            base64_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        except (TypeError, ValueError) as e:
            logging.error(f"序列化内容失败: {e}")
            return False

        payload = {
            "message": "Update file",
            "content": base64_content,
            "sha": sha
        }
        headers = self._get_headers({
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json"
        })

        try:
            logging.info(f"更新 Gitee 文件: {file_path}")
            response = requests.put(url, headers=headers, json=payload, timeout=10)
            return response.status_code
        except requests.RequestException as e:
            logging.error(f"更新文件请求异常: {e}")
            return False

    def create_file(self, file_path: str, content: str, message: str = "新建文件") -> Union[int, bool]:
        """
        创建新文件

        :param file_path: 仓库内目标路径
        :param content: 文件内容字符串
        :param message: 提交信息
        :return: 成功返回 HTTP 状态码（通常201），失败返回 False
        """
        url = f"{self._base_repo_url}/contents/{file_path}"
        try:
            base64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logging.error(f"编码文件内容失败: {e}")
            return False

        payload = {
            "access_token": self.access_token,
            "content": base64_content,
            "message": message
        }
        try:
            logging.info(f"创建 Gitee 文件: {file_path}")
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code
        except requests.RequestException as e:
            logging.error(f"创建文件请求异常: {e}")
            return False

    def delete_file(self, file_path: str, message: str = "删除文件") -> Union[int, bool]:
        """
        删除仓库文件

        :param file_path: 仓库内文件路径
        :param message: 提交信息
        :return: 成功返回 HTTP 状态码，失败返回 False
        """
        # 获取文件 sha
        url = f"{self._base_repo_url}/contents/{file_path}"
        headers = self._get_headers()
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logging.error(f"获取待删除文件信息失败: {resp.status_code}")
                return False
            sha = resp.json()["sha"]
        except (requests.RequestException, KeyError) as e:
            logging.error(f"获取文件 sha 失败: {e}")
            return False

        payload = {
            "access_token": self.access_token,
            "message": message,
            "sha": sha
        }
        try:
            logging.info(f"删除 Gitee 文件: {file_path}")
            response = requests.delete(url, json=payload, timeout=10)
            return response.status_code
        except requests.RequestException as e:
            logging.error(f"删除文件请求异常: {e}")
            return False

    def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """
        获取仓库指定路径的目录列表或单个文件元信息

        :param path: 仓库内路径
        :return: 返回 API 原始响应（目录列表或文件元信息字典），失败返回 None
        """
        url = f"{self._base_repo_url}/contents/{path}"
        params = {"ref": "master"}
        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            logging.warning(f"获取文件信息失败: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"获取文件信息请求异常: {e}")
        return None


if __name__ == '__main__':
    ACCESS_TOCKEN = '7549f1e670db235f86af619937141f2a'  # gitee
    OWNER = 'cfu4536'
    ROPE = 'horpt'
    gitee = GiteeAPI(ACCESS_TOCKEN, OWNER, ROPE)

    ## 1. 创建文件
    print(gitee.create_file(file_path="test/test.html",
                            content="""\n<!DOCTYPE html>\n    <html>\n    <head>\n        <title>Hello shit</title>\n    </head>\n    <body>\n        <h1>Hello</h1>\n    </body>\n    </html>""",
                            message="新建文件"))
    ## 2. 获取文件列表
    print(gitee.get_file_info("test"))
    ## 3. 获取文本内容
    # content = gitee.get_file_content(file_path="test/test.html", format="str")
    # print(content)
    ## 4. 获取文件 raw
    # content = gitee.get_file_raw(file_path="test/test.html")
    # if content:
    #     with open("test.txt", "wb") as f:
    #         f.write(content)
    ## 5. 删除文件
    # print(gitee.delete_file(file_path="test/test.html", message="删除文件"))
