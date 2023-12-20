# -*- coding: utf-8 -*-
import random
import shutil
import tempfile
import time

from smb.SMBConnection import SMBConnection
import logging
import os


class SMBUtils:
    __version = '1.0.4'

    LOCAL_TO_SERVER = 1  # 操作对象是本地到服务端
    SERVER_TO_LOCAL = 2  # 操作对象是服务端到本地
    SERVER_TO_SERVER = 3  # 操作对象是服务端到服务端

    def __init__(self, service_name, sub_working, host, port=139, username="", password="", log_target='SMBUtils'):
        """
        创建一个SMBUtils对象

        :param service_name:    SMB上共享的目录
        :param sub_working:     在共享目录上操作的子目录（把SMB上的所有操作都限定在这个目录里面 保证不会影响到其它目录）
                                后续所有服务端的路径都基于这个工作目录
        :param host:            SMB服务地址
        :param port:            SMB服务端口
        :param username:        共享目录账户名（服务端无限制下 允许匿名访问）
        :param password:        共享目录账户密码（服务端无限制下允许匿名访问）
        :param log_target:      日志target
        """
        # 日志对象
        self.logger = logging.getLogger(log_target)
        # 排除特殊文件夹
        self.special_array = [
            '.',
            '..'
        ]
        # 排除一些常见的系统文件/文件夹
        self.exclude_array = [
            '.deleted',
            'Thumbs.db',
            '__MACOSX',
            '.DS_Store',
            '._.DS_Store',
            'desktop.ini'
        ]
        # 搜索文件属性筛选
        self.search_bits = 0x10031
        # 状态
        self.status = False
        # 连接状态
        self.connect_status = False
        # smb共享文件夹状态
        self.service_status = False
        # 工作目录状态
        self.working_status = False
        self.host = host
        self.port = port
        # smb共享文件夹名称
        self.service_name = service_name
        # 工作目录
        self.sub_working = sub_working
        self.username = username
        self.password = password
        self.anonymous = False

        self.__check_connect()
        self.__check_service()
        self.__check_working()

        if self.connect_status and self.service_status and self.working_status:
            self.status = True
        if self.username == '' or self.password == '':
            self.anonymous = True

    def __del__(self):
        self.connection.close()

    @staticmethod
    def get_version():
        """
        获取SMBUtils版本

        :return:    版本号字符串
        """
        return SMBUtils.__version

    def connected(self):
        """
        SMBUtils是否连接状态
        未连接状态下所有接口都将返回失败

        :return:    是否连接状态
        """
        return self.status

    # base working
    def is_exists(self, any_path):
        """
        路径是否存在（可能是文件/文件夹）

        :param any_path:    路径
        :return:            是否存在
        """
        if self.connected():
            return self.__is_exists_any(self.__real_path(any_path))
        return False

    # base working
    def is_dir(self, dir_path):
        """
        路径是否为目录（不存在也返回False）

        :param dir_path:    路径
        :return:            是否为目录
        """
        if self.connected() and self.is_exists(dir_path):
            return self.__is_dir(self.__real_path(dir_path))
        else:
            return False

    # base working
    def is_file(self, file_path):
        """
        路径是否为文件（不存在也返回False）

        :param file_path:   路径
        :return:            是否为文件
        """
        if self.connected() and self.is_exists(file_path):
            return self.__is_file(self.__real_path(file_path))
        else:
            return False

    # base working
    def list_dir(self, dir_path):
        """
        获取目录层级下所有文件/文件夹名称 （ls）

        :param dir_path:    目录路径
        :return:            文件/文件夹名称数组
        """
        ls_list = []
        if self.connected() and self.is_dir(dir_path):
            ls_list = self.__list_dir(self.__real_path(dir_path))
        return ls_list

    # base working
    def tree_dir(self, dir_path, depth=0):
        """
        获取目录下的所有文件/文件夹路径（tree）

        :param dir_path:    目录路径
        :param depth:       遍历深度
        :return:            文件/文件夹路径数组
        """
        tree_list = []
        if self.connected() and self.is_dir(dir_path):
            self.__tree_dir(self.__real_path(dir_path), '', tree_list, 1, depth)
        return tree_list

    # base working
    def make_dir(self, dir_path):
        """
        创建文件夹（mkdir -p）
        允许重复创建以及一次性创建多层目录

        :param dir_path:    文件夹路径
        :return:            创建是否成功
        """
        if self.connected():
            if self.anonymous:
                self.logger.warning("is anonymous !")
                return False
            full = self.__real_path(dir_path)
            if self.is_exists(dir_path):
                if self.is_file(dir_path):
                    self.logger.warning("%s is file !", full)
                    return False
                if self.is_dir(dir_path):
                    return True
                raise Exception("%s is unknown file type !", full)
            else:
                if self.__create_enable(full):
                    return self.__traversal_make_dir(full)
                else:
                    self.logger.error("Disable create %s , please check path !", full)
                    return False
        return False

    # base working
    def remove_dir(self, dir_path):
        """
        删除文件夹（rm -rf）
        允许文件夹不为空

        :param dir_path:    目录路径
        :return:            是否删除成功
        """
        if self.connected():
            if self.anonymous:
                self.logger.warning("is anonymous !")
                return False
            full = self.__real_path(dir_path)
            if self.is_exists(dir_path):
                if self.is_file(dir_path):
                    self.logger.warning("%s is file !", full)
                    return False
                if self.is_dir(dir_path):
                    self.__traversal_remove_dir_and_file(full)
                    return True
                raise Exception("%s is unknown file type !", full)
            else:
                return True
        return False

    # base working
    def create_file(self, file_path):
        """
        创建一个文件（用于测试 实际上没什么用）
        允许一次性创建多层级目录

        :param file_path:   文件路径
        :return:            创建结果
        """
        if self.connected():
            if self.anonymous:
                self.logger.warning("is anonymous !")
                return False
            full = self.__real_path(file_path)
            if self.is_exists(file_path):
                if self.is_dir(file_path):
                    self.logger.warning("%s is directory !", full)
                    return False
                if self.is_file(file_path):
                    self.logger.warning("file %s is exists !", full)
                    return True
                raise Exception("%s is unknown file type !", full)
            else:
                if self.__create_enable(full):
                    self.__traversal_make_dir(os.path.dirname(full))
                    self.__create_empty_file(full)
                    return True
                else:
                    self.logger.error("Disable create %s , please check path !", full)
                    return False
        return False

    # base working
    def delete_file(self, file_path):
        """
        删除文件

        :param file_path:   文件路径
        :return:            是否删除成功
        """
        if self.connected():
            if self.anonymous:
                self.logger.warning("is anonymous !")
                return False
            full = self.__real_path(file_path)
            if self.is_exists(file_path):
                if self.is_dir(file_path):
                    self.logger.warning("%s is directory !", full)
                    return False
                if self.is_file(file_path):
                    self.__remove_file(full)
                    return True
                raise Exception("%s is unknown file type !", full)
            else:
                return True
        return False

    # base working
    def copy_dir(self, src_dir, dst_dir, mode, overwrite=True):
        """
        拷贝文件夹（cp -R）
        需要确保src文件夹与dst文件夹均存在！！！
        避免拷贝层级引起歧义！！！

        :param src_dir:     源文件夹
        :param dst_dir:     目标文件夹
        :param mode:        拷贝模式
                            SMBUtils.LOCAL_TO_SERVER
                            SMBUtils.SERVER_TO_LOCAL
                            SMBUtils.SERVER_TO_SERVER
        :param overwrite:   已存在是否覆盖
        :return:            是否拷贝成功
        """
        if self.connected():
            if self.anonymous and (mode == SMBUtils.LOCAL_TO_SERVER or mode == SMBUtils.SERVER_TO_SERVER):
                self.logger.warning("is anonymous !")
                return False
            if mode == SMBUtils.LOCAL_TO_SERVER:
                if SMBUtils.__local_is_dir(src_dir) and self.is_dir(dst_dir):
                    return self.__dir_local_to_server(src_dir,
                                                      self.__real_path(dst_dir),
                                                      overwrite)
                else:
                    if not SMBUtils.__local_is_dir(src_dir):
                        self.logger.error("local %s is not exists !", src_dir)
                    else:
                        self.logger.error("server %s is not exists !", dst_dir)
                    return False
            elif mode == SMBUtils.SERVER_TO_LOCAL:
                if self.is_dir(src_dir) and SMBUtils.__local_is_dir(dst_dir):
                    return self.__dir_server_to_local(self.__real_path(src_dir),
                                                      dst_dir,
                                                      overwrite)
                else:
                    if not SMBUtils.__local_is_dir(dst_dir):
                        self.logger.error("local %s is not exists !", dst_dir)
                    else:
                        self.logger.error("server %s is not exists !", src_dir)
                    return False
            elif mode == SMBUtils.SERVER_TO_SERVER:
                if src_dir == dst_dir:
                    return False
                if self.is_dir(src_dir) and self.is_dir(dst_dir):
                    return self.__dir_server_to_server(self.__real_path(src_dir),
                                                       self.__real_path(dst_dir),
                                                       overwrite)
                else:
                    if not self.is_dir(src_dir):
                        self.logger.error("server %s is not exists !", src_dir)
                    else:
                        self.logger.error("server %s is not exists !", dst_dir)
                    return False
            else:
                self.logger.warning("%d is unknown type !", mode)
                return False
        return False

    # base working
    def move_dir(self, src_dir, dst_dir, mode, overwrite=True):
        """
        移动文件夹（mv）
        SMBUtils.LOCAL_TO_SERVER & SMBUtils.SERVER_TO_LOCAL 模式下
            需要确保src文件夹与dst文件夹存在！！！
        SMBUtils.SERVER_TO_SERVER 模式下
            允许dst文件夹不存在

        :param src_dir:     源文件夹
        :param dst_dir:     目标文件夹
        :param mode:        移动模式
                            SMBUtils.LOCAL_TO_SERVER
                            SMBUtils.SERVER_TO_LOCAL
                            SMBUtils.SERVER_TO_SERVER
        :param overwrite:   已存在是否覆盖
        :return:            是否移动成功
        """
        if self.connected():
            if self.anonymous and (mode == SMBUtils.LOCAL_TO_SERVER or mode == SMBUtils.SERVER_TO_SERVER):
                self.logger.warning("is anonymous !")
                return False
            if mode == SMBUtils.LOCAL_TO_SERVER:
                if SMBUtils.__local_is_dir(src_dir) and self.is_dir(dst_dir):
                    if self.__dir_local_to_server(src_dir,
                                                  self.__real_path(dst_dir),
                                                  overwrite):
                        shutil.rmtree(src_dir, ignore_errors=True)
                        return True
                    return False
                else:
                    if not SMBUtils.__local_is_dir(src_dir):
                        self.logger.error("local %s is not exists !", src_dir)
                    else:
                        self.logger.error("server %s is not exists !", dst_dir)
                    return False
            elif mode == SMBUtils.SERVER_TO_LOCAL:
                if self.is_dir(src_dir) and SMBUtils.__local_is_dir(dst_dir):
                    if self.__dir_server_to_local(self.__real_path(src_dir),
                                                  dst_dir,
                                                  overwrite):
                        self.__traversal_remove_dir_and_file(self.__real_path(src_dir))
                        return True
                    return False
                else:
                    if not SMBUtils.__local_is_dir(dst_dir):
                        self.logger.error("local %s is not exists !", dst_dir)
                    else:
                        self.logger.error("server %s is not exists !", src_dir)
                    return False
            elif mode == SMBUtils.SERVER_TO_SERVER:
                if src_dir == dst_dir:
                    return False
                if self.is_dir(src_dir):
                    if not self.is_exists(dst_dir) or self.is_dir(dst_dir):
                        if self.__create_enable(self.__real_path(dst_dir)):
                            temp_dir = os.path.dirname(self.__real_path(dst_dir))
                            if self.__is_exists_any(temp_dir) or self.__traversal_make_dir(temp_dir):
                                return self.__dir_move(self.__real_path(src_dir),
                                                       self.__real_path(dst_dir),
                                                       overwrite)
                            self.logger.error("server %s is create failed !", temp_dir)
                            return False
                        self.logger.error("server %s is disable to create !", dst_dir)
                        return False
                    else:
                        self.logger.error("server %s is not directory !", dst_dir)
                        return False
                else:
                    self.logger.error("server %s is not exists !", src_dir)
                    return False
            else:
                self.logger.warning("%d is unknown type !", mode)
                return False
        return False

    # base working
    def copy_file(self, src_file, dst_file, mode, overwrite=True):
        """
        拷贝文件（cp）
        需要确保src文件存在
        dst文件可以不存在

        :param src_file:    源文件
        :param dst_file:    目标文件
        :param mode:        拷贝模式
                            SMBUtils.LOCAL_TO_SERVER
                            SMBUtils.SERVER_TO_LOCAL
                            SMBUtils.SERVER_TO_SERVER
        :param overwrite:   已存在是否覆盖
        :return:            是否拷贝成功
        """
        if self.connected():
            if self.anonymous and (mode == SMBUtils.LOCAL_TO_SERVER or mode == SMBUtils.SERVER_TO_SERVER):
                self.logger.warning("is anonymous !")
                return False
            if mode == SMBUtils.LOCAL_TO_SERVER:
                if SMBUtils.__local_is_file(src_file):
                    if not self.is_exists(dst_file) or self.is_file(dst_file):
                        if self.__create_enable(self.__real_path(dst_file)):
                            temp_dir = os.path.dirname(self.__real_path(dst_file))
                            if self.__is_exists_any(temp_dir) or self.__traversal_make_dir(temp_dir):
                                return self.__file_local_to_server(src_file,
                                                                   self.__real_path(dst_file),
                                                                   overwrite)
                            self.logger.error("server %s is create failed !", temp_dir)
                            return False
                        self.logger.error("server %s is disable to create !", dst_file)
                        return False
                    self.logger.error("server %s is not file !", dst_file)
                    return False
                else:
                    self.logger.error("local %s is not exists !", src_file)
                    return False
            elif mode == SMBUtils.SERVER_TO_LOCAL:
                if self.is_file(src_file):
                    if not self.__local_is_exists_any(dst_file) or self.__local_is_file(dst_file):
                        if SMBUtils.__local_create_enable(dst_file):
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            return self.__file_server_to_local(self.__real_path(src_file),
                                                               dst_file,
                                                               overwrite)
                        self.logger.error("local %s is disable to create !", dst_file)
                        return False
                    self.logger.error("local %s is not file !", dst_file)
                    return False
                else:
                    self.logger.error("server %s is not exists !", src_file)
                    return False
            elif mode == SMBUtils.SERVER_TO_SERVER:
                if src_file == dst_file:
                    self.logger.error("cannot copy to itself ！", src_file)
                    return False
                if self.is_file(src_file):
                    if not self.is_exists(dst_file) or self.is_file(dst_file):
                        if self.__create_enable(self.__real_path(dst_file)):
                            temp_dir = os.path.dirname(self.__real_path(dst_file))
                            if self.__is_exists_any(temp_dir) or self.__traversal_make_dir(temp_dir):
                                return self.__file_server_to_server(self.__real_path(src_file),
                                                                    self.__real_path(dst_file),
                                                                    overwrite)
                            self.logger.error("server %s is create failed !", temp_dir)
                            return False
                        self.logger.error("server %s is disable to create !", dst_file)
                        return False
                    self.logger.error("server %s is not file !", dst_file)
                    return False
                else:
                    self.logger.error("server %s is not exists !", src_file)
                    return False
            else:
                self.logger.warning("%d is unknown type !", mode)
                return False
        return False

    # base working
    def move_file(self, src_file, dst_file, mode, overwrite=True):
        """
        移动文件（mv）

        :param src_file:    源文件
        :param dst_file:    目标文件
        :param mode:        移动模式
                            SMBUtils.LOCAL_TO_SERVER
                            SMBUtils.SERVER_TO_LOCAL
                            SMBUtils.SERVER_TO_SERVER
        :param overwrite:   已存在是否覆盖
        :return:            是否移动成功
        """
        if self.connected():
            if self.anonymous and (mode == SMBUtils.LOCAL_TO_SERVER or mode == SMBUtils.SERVER_TO_SERVER):
                self.logger.warning("is anonymous !")
                return False
            if mode == SMBUtils.LOCAL_TO_SERVER:
                if SMBUtils.__local_is_file(src_file):
                    if not self.is_exists(dst_file) or self.is_file(dst_file):
                        if self.__create_enable(self.__real_path(dst_file)):
                            temp_dir = os.path.dirname(self.__real_path(dst_file))
                            if self.__is_exists_any(temp_dir) or self.__traversal_make_dir(temp_dir):
                                if self.__file_local_to_server(src_file,
                                                               self.__real_path(dst_file),
                                                               overwrite):
                                    os.remove(src_file)
                                    return True
                                return False
                            self.logger.error("server %s is create failed !", temp_dir)
                            return False
                        self.logger.error("server %s is disable to create !", dst_file)
                        return False
                    self.logger.error("server %s is not file !", dst_file)
                    return False
                else:
                    self.logger.error("local %s is not exists !", src_file)
                    return False
            elif mode == SMBUtils.SERVER_TO_LOCAL:
                if self.is_file(src_file):
                    if not self.__local_is_exists_any(dst_file) or self.__local_is_file(dst_file):
                        if SMBUtils.__local_create_enable(dst_file):
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            if self.__file_server_to_local(self.__real_path(src_file),
                                                           dst_file,
                                                           overwrite):
                                self.__remove_file(self.__real_path(src_file))
                                return True
                            else:
                                return False
                        self.logger.error("local %s is disable to create !", dst_file)
                        return False
                    self.logger.error("local %s is not file !", dst_file)
                    return False
                else:
                    self.logger.error("server %s is not exists !", src_file)
                    return False
            elif mode == SMBUtils.SERVER_TO_SERVER:
                if src_file == dst_file:
                    self.logger.error("cannot move to itself ！", src_file)
                    return False
                if self.is_file(src_file):
                    if not self.is_exists(dst_file) or self.is_file(dst_file):
                        if self.__create_enable(self.__real_path(dst_file)):
                            temp_dir = os.path.dirname(self.__real_path(dst_file))
                            if self.__is_exists_any(temp_dir) or self.__traversal_make_dir(temp_dir):
                                return self.__file_move(self.__real_path(src_file),
                                                        self.__real_path(dst_file),
                                                        overwrite)
                            self.logger.error("server %s is create failed !", temp_dir)
                            return False
                        self.logger.error("server %s is disable to create !", dst_file)
                        return False
                    self.logger.error("server %s is not file !", dst_file)
                    return False
                else:
                    self.logger.error("server %s is not exists !", src_file)
                    return False
            else:
                self.logger.warning("%d is unknown type !", mode)
                return False
        return False

    #
    # Protected Methods
    # 内部模块
    #

    def __check_connect(self):
        """
        检查连接状态

        :return: None
        """
        self.connection = SMBConnection(self.username, self.password, "", "", use_ntlm_v2=True)
        if self.connection.connect(self.host, self.port):
            self.logger.info("connect success !")
            self.connect_status = True
        else:
            self.logger.error("connect failed !")

    def __check_service(self):
        """
        检查共享目录状态

        :return: None
        """
        if self.connect_status:
            shares = self.connection.listShares()
            for share in shares:
                if not share.isSpecial and share.name not in ['NETLOGON', 'SYSVOL'] and share.name == self.service_name:
                    self.service_status = True
                    return
            self.logger.error("server share name %s is not exists !", self.service_name)

    def __check_working(self):
        """
        检查工作目录状态

        :return: None
        """
        if self.connect_status and self.service_status:
            parent_dir = ''
            p_list = SMBUtils.__path_split(self.sub_working)
            for sub_dir in p_list:
                if self.__is_exists(sub_dir, parent_dir):
                    parent_dir = SMBUtils.__join_two_path(parent_dir, sub_dir)
                else:
                    self.logger.error("%s not in service %s !", self.sub_working, self.service_name)
                    return
            self.working_status = True

    @staticmethod
    def __path_split(path):
        """
        拆分路径层级

        例如 x1/x2/x3 返回 ['x1', 'x2', 'x3']

        :param path:    路径
        :return:        层级数组
        """
        p_list = []
        p_dir = path
        while not p_dir == '' and not p_dir == '/':
            p_list.append(os.path.basename(p_dir))
            p_dir = os.path.dirname(p_dir)
        return list(reversed(p_list))

    def __is_exists(self, sub_dir, parent_dir):
        """
        检查指定目录中是否存在文件/文件夹

        :param sub_dir:     文件/文件夹名称
        :param parent_dir:  指定目录
        :return:            是否存在
        """
        if sub_dir in self.exclude_array or sub_dir in self.special_array:
            return False
        flag = False
        if self.connect_status and self.service_status:
            shared_files = self.connection.listPath(self.service_name, parent_dir, search=self.search_bits)
            for shared_file in shared_files:
                if sub_dir == shared_file.filename:
                    flag = True
                    break
        return flag

    def __is_exists_any(self, any_path):
        """
        检查指定路径是否存在（可能是文件/文件夹）

        :param any_path:    指定路径
        :return:            是否存在
        """
        parent_dir = ''
        p_list = SMBUtils.__path_split(any_path)
        for sub_dir in p_list:
            if self.__is_exists(sub_dir, parent_dir):
                parent_dir = SMBUtils.__join_two_path(parent_dir, sub_dir)
            else:
                return False
        return True

    def __is_dir(self, any_path):
        """
        检查指定路径是否文件夹

        :param any_path:    指定路径
        :return:            是否文件夹
        """
        attrs = self.connection.getAttributes(self.service_name, any_path)
        return attrs.isDirectory

    def __is_file(self, any_path):
        """
        检查指定路径是否文件

        :param any_path:    指定路径
        :return:            是否文件
        """
        attrs = self.connection.getAttributes(self.service_name, any_path)
        return not attrs.isDirectory

    def __remove_file(self, file_path):
        """
        移除指定路径文件

        :param file_path:   指定路径文件
        :return:            None
        """
        self.connection.deleteFiles(self.service_name, file_path)

    def __traversal_make_dir(self, dir_path):
        """
        遍历创建指定目录

        :param dir_path:    指定目录
        :return:            None
        """
        p_list = SMBUtils.__path_split(dir_path)
        temp_dir = ''
        for sub_dir in p_list:
            temp_dir = SMBUtils.__join_two_path(temp_dir, sub_dir)
            if not self.__is_exists_any(temp_dir):
                try:
                    self.connection.createDirectory(self.service_name, temp_dir)
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(e)
                    return False
            else:
                if not self.__is_dir(temp_dir):
                    self.logger.error("%s is not directory !", temp_dir)
                    return False
        return True

    def __traversal_remove_dir_and_file(self, dir_path):
        """
        遍历删除指定文件夹中的所有子文件/子文件夹

        :param dir_path:    指定目录
        :return:            None
        """
        shared_files = self.connection.listPath(self.service_name, dir_path)
        for shared_file in shared_files:
            if shared_file.filename not in self.special_array:
                temp_path = SMBUtils.__join_two_path(dir_path, shared_file.filename)
                attrs = self.connection.getAttributes(self.service_name, temp_path)
                if attrs.isDirectory:
                    self.__traversal_remove_dir_and_file(temp_path)
                else:
                    self.connection.deleteFiles(self.service_name, temp_path)
        self.connection.deleteDirectory(self.service_name, dir_path)

    def __create_empty_file(self, file_path):
        """
        创建一个指定路径的空文件

        :param file_path:   指定路径文件
        :return:            None
        """
        temp_path = tempfile.gettempdir() + os.path.sep + SMBUtils.__random_string(24) + '.tmp'
        with open(temp_path, "wb+") as local_file:
            self.connection.storeFile(self.service_name, file_path, local_file)
        os.remove(temp_path)

    def __create_enable(self, any_path):
        """
        是否允许创建指定路径资源

        :param any_path:    指定路径
        :return:            是否允许创建
        """
        base_path = os.path.dirname(any_path)
        p_list = SMBUtils.__path_split(base_path)
        temp_dir = ''
        for sub_dir in p_list:
            temp_dir = SMBUtils.__join_two_path(temp_dir, sub_dir)
            if self.__is_exists_any(temp_dir):
                if not self.__is_dir(temp_dir):
                    return False
            else:
                break
        return True

    def __list_dir(self, dir_path):
        """
        获取指定目录下的子文件/子文件夹名称
        不会遍历子文件夹

        :param dir_path:    指定路径
        :return:            子文件/文件夹名称数组
        """
        ls_list = []
        shared_files = self.connection.listPath(self.service_name, dir_path, search=self.search_bits)
        for shared_file in shared_files:
            if shared_file.filename not in self.exclude_array and shared_file.filename not in self.special_array:
                ls_list.append(shared_file.filename)
        return ls_list

    def __tree_dir(self, base_dir, dir_path, tree_list: [], cur_depth, depth):
        """
        约束深度遍历文件夹

        :param base_dir:    起始目录
        :param dir_path:    相对起始目录的当前深度目录
        :param tree_list:   遍历结果存储
        :param cur_depth:   当前深度
        :param depth:       深度限制
        :return:            None
        """
        if dir_path != '':
            tree_list.append(os.path.join(dir_path, ''))
            ls_list = self.__list_dir(os.path.join(base_dir, dir_path))
        else:
            ls_list = self.__list_dir(base_dir)
        if depth != 0 and cur_depth > depth:
            return
        dir_list = []
        file_list = []
        for dir_or_file in ls_list:
            if dir_path != '':
                full_path = os.path.join(base_dir, dir_path, dir_or_file)
            else:
                full_path = os.path.join(base_dir, dir_or_file)
            if self.__is_dir(full_path):
                dir_list.append(dir_or_file)
            else:
                file_list.append(dir_or_file)
        dir_list.sort()
        file_list.sort()
        for file_name in file_list:
            if dir_path != '':
                tree_list.append(os.path.join(dir_path, file_name))
            else:
                tree_list.append(file_name)
        for dir_name in dir_list:
            if dir_path != '':
                self.__tree_dir(base_dir,
                                os.path.join(dir_path, dir_name),
                                tree_list,
                                cur_depth + 1,
                                depth)
            else:
                self.__tree_dir(base_dir,
                                dir_name,
                                tree_list,
                                cur_depth + 1,
                                depth)

    @staticmethod
    def __local_is_file(any_path):
        """
        检查指定路径是否本地文件

        :param any_path:    指定路径
        :return:            是否文件
        """
        return os.path.isfile(any_path)

    @staticmethod
    def __local_is_dir(any_path):
        """
        检查指定路径是否本地目录

        :param any_path:    指定路径
        :return:            是否目录
        """
        return os.path.isdir(any_path)

    @staticmethod
    def __local_is_exists_any(any_path):
        """
        检查指定路径本地是否存在

        :param any_path:    指定路径
        :return:            是否存在
        """
        return os.path.exists(any_path)

    @staticmethod
    def __local_create_enable(any_path):
        """
        检查指定本地路径是否允许创建

        :param any_path:    本地路径
        :return:            是否允许
        """
        base_path = os.path.dirname(any_path)
        p_list = SMBUtils.__path_split(base_path)
        temp_dir = ''
        for sub_dir in p_list:
            temp_dir = SMBUtils.__join_two_path(temp_dir, sub_dir)
            if SMBUtils.__local_is_exists_any(temp_dir) and not SMBUtils.__local_is_dir(temp_dir):
                return False
        return True

    def __dir_local_to_server(self, src_any_path, dst_any_path, overwrite):
        """
        从本地拷贝文件夹到服务端

        :param src_any_path:    本地文件夹
        :param dst_any_path:    服务端文件夹
        :param overwrite:       存在是否覆盖
        :return:                是否拷贝成功
        """
        dir_or_files = os.listdir(src_any_path)
        for dir_or_file in dir_or_files:
            if dir_or_file in self.special_array or dir_or_file in self.exclude_array:
                continue
            dir_file_path = os.path.join(src_any_path, dir_or_file)
            if SMBUtils.__local_is_dir(dir_file_path):
                src_dir_path = dir_file_path
                dst_dir_path = os.path.join(dst_any_path, dir_or_file)
                if self.__is_exists(dir_or_file, dst_any_path):
                    if not self.__is_dir(dst_dir_path):
                        self.logger.error("%s is not directory !", dst_dir_path)
                        return False
                else:
                    self.connection.createDirectory(self.service_name, dst_dir_path)
                    time.sleep(1)
                if not self.__dir_local_to_server(src_dir_path, dst_dir_path, overwrite):
                    return False
            elif SMBUtils.__local_is_file(dir_file_path):
                src_file_path = dir_file_path
                dst_file_path = os.path.join(dst_any_path, dir_or_file)
                if not self.__is_exists_any(dst_file_path) or self.__is_file(dst_file_path):
                    if not self.__file_local_to_server(src_file_path, dst_file_path, overwrite):
                        return False
                else:
                    logging.error("%s is not file !", dst_file_path)
                    return False
        return True

    def __dir_server_to_local(self, src_any_path, dst_any_path, overwrite):
        """
        从服务端拷贝文件夹到本地

        :param src_any_path:    服务端文件夹
        :param dst_any_path:    本地文件夹
        :param overwrite:       存在是否覆盖
        :return:                是否拷贝成功
        """
        dir_or_files = self.__list_dir(src_any_path)
        for dir_or_file in dir_or_files:
            dir_file_path = os.path.join(src_any_path, dir_or_file)
            if self.__is_dir(dir_file_path):
                src_dir_path = dir_file_path
                dst_dir_path = os.path.join(dst_any_path, dir_or_file)
                if self.__local_is_exists_any(dst_dir_path):
                    if not self.__local_is_dir(dst_dir_path):
                        self.logger.error("%s is not directory !", dst_dir_path)
                        return False
                else:
                    os.makedirs(dst_dir_path, exist_ok=True)
                if not self.__dir_server_to_local(src_dir_path, dst_dir_path, overwrite):
                    return False
            elif self.__is_file(dir_file_path):
                src_file_path = dir_file_path
                dst_file_path = os.path.join(dst_any_path, dir_or_file)
                if not self.__local_is_exists_any(dst_file_path) or self.__local_is_file(dst_file_path):
                    if not self.__file_server_to_local(src_file_path, dst_file_path, overwrite):
                        return False
                else:
                    self.logger.error("%s is not file !", dst_file_path)
                    return False
        return True

    def __dir_server_to_server(self, src_any_path, dst_any_path, overwrite):
        """
        从服务端拷贝文件夹到服务端

        :param src_any_path:    服务端文件夹
        :param dst_any_path:    服务端文件夹
        :param overwrite:       存在是否覆盖
        :return:                是否拷贝成功
        """
        dir_or_files = self.__list_dir(src_any_path)
        for dir_or_file in dir_or_files:
            dir_file_path = os.path.join(src_any_path, dir_or_file)
            if self.__is_dir(dir_file_path):
                src_dir_path = dir_file_path
                dst_dir_path = os.path.join(dst_any_path, dir_or_file)
                if self.__is_exists(dir_or_file, dst_any_path):
                    if not self.__is_dir(dst_dir_path):
                        self.logger.error("%s is not directory !", dst_dir_path)
                        return False
                else:
                    self.connection.createDirectory(self.service_name, dst_dir_path)
                    time.sleep(1)
                if not self.__dir_server_to_server(src_dir_path, dst_dir_path, overwrite):
                    return False
            elif self.__is_file(dir_file_path):
                src_file_path = dir_file_path
                dst_file_path = os.path.join(dst_any_path, dir_or_file)
                if not self.__is_exists_any(dst_file_path) or self.__is_file(dst_file_path):
                    if not self.__file_server_to_server(src_file_path, dst_file_path, overwrite):
                        return False
                else:
                    self.logger.error("%s is not file !", dst_file_path)
                    return False
        return True

    def __dir_move(self, src_any_path, dst_any_path, overwrite):
        """
        从服务端移动文件夹到服务端

        :param src_any_path:    服务端文件夹
        :param dst_any_path:    服务端文件夹
        :param overwrite:       存在是否覆盖
        :return:                是否移动成功
        """
        if not overwrite and self.__is_exists_any(dst_any_path):
            return True
        if self.__is_exists_any(dst_any_path):
            self.__traversal_remove_dir_and_file(dst_any_path)
        self.connection.rename(self.service_name, src_any_path, dst_any_path)
        return True

    def __file_local_to_server(self, src_any_path, dst_any_path, overwrite):
        """
        从本地拷贝文件到服务端

        :param src_any_path:    本地文件
        :param dst_any_path:    服务端文件
        :param overwrite:       存在是否覆盖
        :return:                是否拷贝成功
        """
        if not overwrite and self.__is_exists_any(dst_any_path):
            return True
        with open(src_any_path, "rb") as local_file:
            r_bytes = self.connection.storeFile(self.service_name, dst_any_path, local_file)
            return r_bytes > 0

    def __file_server_to_local(self, src_any_path, dst_any_path, overwrite):
        """
        从服务端拷贝文件到本地

        :param src_any_path:    服务端文件
        :param dst_any_path:    本地文件
        :param overwrite:       存在是否覆盖
        :return:                是否拷贝成功
        """
        if not overwrite and self.__local_is_exists_any(dst_any_path):
            return True
        temp_path = tempfile.gettempdir() + os.path.sep + SMBUtils.__random_string(24) + '.tmp'
        with open(temp_path, 'wb') as local_file:
            file_attributes, file_size = self.connection.retrieveFile(self.service_name, src_any_path, local_file)
        if file_size > 0:
            shutil.move(temp_path, dst_any_path)
            return True
        return False

    def __file_server_to_server(self, src_any_path, dst_any_path, overwrite):
        """
        从服务端拷贝文件到服务端

        :param src_any_path:    服务端文件
        :param dst_any_path:    服务端文件
        :param overwrite:       存在是否覆盖
        :return:                是否拷贝成功
        """
        if not overwrite and self.__is_exists_any(dst_any_path):
            return True
        temp_path = tempfile.gettempdir() + os.path.sep + SMBUtils.__random_string(24) + '.tmp'
        with open(temp_path, 'wb') as local_file:
            file_attributes, file_size = self.connection.retrieveFile(self.service_name, src_any_path, local_file)
        if not file_size > 0:
            os.remove(temp_path)
            return False
        with open(temp_path, "rb") as local_file:
            r_bytes = self.connection.storeFile(self.service_name, dst_any_path, local_file)
            return r_bytes > 0

    def __file_move(self, src_any_path, dst_any_path, overwrite):
        """
        从服务端移动文件到服务端

        :param src_any_path:    服务端文件
        :param dst_any_path:    服务端文件
        :param overwrite:       存在是否覆盖
        :return:                是否移动成功
        """
        if not overwrite and self.__is_exists_any(dst_any_path):
            return True
        if self.__is_exists_any(dst_any_path):
            self.__remove_file(dst_any_path)
        self.connection.rename(self.service_name, src_any_path, dst_any_path)
        return True

    @staticmethod
    def __random_string(num):
        """
        生成指定长度的随机字符串

        :param num:     指定长度
        :return:        随机字符串
        """
        char_pool = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        salt = ''
        for i in range(num):
            salt += random.choice(char_pool)
        return salt

    def __real_path(self, any_path):
        """
        拼接服务端完整路径

        :param any_path:    指定工作路径
        :return:            完整路径
        """
        if any_path != '':
            return os.path.join(self.sub_working, any_path)
        else:
            return self.sub_working

    @staticmethod
    def __join_two_path(parent_dir, sub_dir):
        if parent_dir != '':
            return os.path.join(parent_dir, sub_dir)
        else:
            return sub_dir
