#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для передачи файлов между компьютером и принтером по SCP
"""

import paramiko
import os
import logging
from typing import List, Dict, Optional
from scp import SCPClient


class SCPFileTransfer:
    """Класс для передачи файлов по SCP"""
    
    def __init__(self, host: str = '', username: str = '', password: str = '', timeout: int = 10):
        """
        Инициализация
        
        Args:
            host: Хост для подключения
            username: Имя пользователя
            password: Пароль
            timeout: Таймаут подключения в секундах
        """
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ssh_client = None
        self.scp_client = None
    
    def connect(self) -> bool:
        """
        Устанавливает соединение
        
        Returns:
            bool: True если соединение успешно установлено
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                self.host,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            self.scp_client = SCPClient(self.ssh_client.get_transport())
            return True
        except Exception as e:
            logging.error(f"SCP connection error: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Закрывает соединение"""
        if self.scp_client:
            self.scp_client.close()
            self.scp_client = None
        
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def get_file(self, remote_path: str, local_path: str) -> bool:
        """
        Загружает файл с удаленного сервера
        
        Args:
            remote_path: Путь к файлу на удаленном сервере
            local_path: Локальный путь для сохранения файла
            
        Returns:
            bool: True если файл успешно загружен
        """
        if not self.scp_client:
            if not self.connect():
                return False
        
        try:
            # Создаем директорию назначения, если она не существует
            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
            
            self.scp_client.get(remote_path, local_path)
            return True
        except Exception as e:
            logging.error(f"File download error: {str(e)}")
            return False
    
    def put_file(self, local_path: str, remote_path: str) -> bool:
        """
        Загружает файл на удаленный сервер
        
        Args:
            local_path: Локальный путь к файлу
            remote_path: Путь для сохранения на удаленном сервере
            
        Returns:
            bool: True если файл успешно загружен
        """
        if not self.scp_client:
            if not self.connect():
                return False
        
        try:
            self.scp_client.put(local_path, remote_path)
            return True
        except Exception as e:
            logging.error(f"File upload error: {str(e)}")
            return False
    
    def get_multiple_files(self, file_pairs: List[Dict[str, str]]) -> Dict[str, bool]:
        """
        Загружает несколько файлов с удаленного сервера
        
        Args:
            file_pairs: Список словарей вида {'remote_path': '/path/on/remote', 'local_path': '/path/on/local'}
            
        Returns:
            Dict[str, bool]: Словарь результатов загрузки {'/path/on/remote': True/False}
        """
        results = {}
        
        for file_pair in file_pairs:
            remote_path = file_pair.get('remote_path')
            local_path = file_pair.get('local_path')
            
            if not remote_path or not local_path:
                continue
                
            results[remote_path] = self.get_file(remote_path, local_path)
            
        return results
    
    def get_directory(self, remote_dir: str, local_dir: str, recursive: bool = True) -> int:
        """
        Загружает директорию с удаленного сервера
        
        Args:
            remote_dir: Путь к директории на удаленном сервере
            local_dir: Локальный путь для сохранения
            recursive: Рекурсивно загружать поддиректории
            
        Returns:
            int: Количество успешно загруженных файлов
        """
        if not self.scp_client:
            if not self.connect():
                return 0
        
        # Создаем локальную директорию, если она не существует
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        try:
            # Получаем список файлов в удаленной директории
            command = f"find {remote_dir} -type f" if recursive else f"find {remote_dir} -maxdepth 1 -type f"
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            remote_files = [line.strip() for line in stdout.readlines() if line.strip()]
            
            # Загружаем каждый файл
            downloaded_count = 0
            for remote_path in remote_files:
                # Создаем относительный путь для локального файла
                rel_path = os.path.relpath(remote_path, remote_dir)
                local_path = os.path.join(local_dir, rel_path)
                
                # Создаем локальную директорию, если нужно
                local_file_dir = os.path.dirname(local_path)
                if not os.path.exists(local_file_dir):
                    os.makedirs(local_file_dir, exist_ok=True)
                
                # Загружаем файл
                if self.get_file(remote_path, local_path):
                    downloaded_count += 1
                    
            return downloaded_count
        
        except Exception as e:
            logging.error(f"Directory download error: {str(e)}")
            return 0
    
    def find_and_get_files(self, remote_dir: str, pattern: str, local_dir: str) -> List[str]:
        """
        Ищет файлы по шаблону в удаленной директории и загружает их
        
        Args:
            remote_dir: Директория для поиска
            pattern: Шаблон имени файла (поддерживается glob)
            local_dir: Локальная директория для сохранения
            
        Returns:
            List[str]: Список полных путей к загруженным файлам
        """
        if not self.ssh_client:
            if not self.connect():
                return []
        
        try:
            # Создаем локальную директорию, если она не существует
            if not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
                
            # Ищем файлы по шаблону
            command = f"find {remote_dir} -name '{pattern}' -type f"
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            remote_files = [line.strip() for line in stdout.readlines() if line.strip()]
            
            # Загружаем каждый файл
            downloaded_files = []
            for remote_path in remote_files:
                local_path = os.path.join(local_dir, os.path.basename(remote_path))
                if self.get_file(remote_path, local_path):
                    downloaded_files.append(local_path)
                    
            return downloaded_files
        
        except Exception as e:
            logging.error(f"Find and get files error: {str(e)}")
            return []