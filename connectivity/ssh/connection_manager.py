#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для управления SSH-соединениями с принтером
"""

import paramiko
import os
import logging
from typing import Tuple, Optional, Dict, List


class SSHConnectionManager:
    """Класс для управления SSH-соединениями"""
    
    def __init__(self, host: str = '', username: str = '', password: str = '', timeout: int = 10):
        """
        Инициализация менеджера соединений
        
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
        self.client = None
    
    def connect(self) -> bool:
        """
        Устанавливает SSH соединение
        
        Returns:
            bool: True если соединение успешно установлено
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.host,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            return True
        except Exception as e:
            logging.error(f"SSH connection error: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Закрывает соединение"""
        if self.client:
            self.client.close()
            self.client = None
    
    def execute_command(self, command: str) -> Tuple[int, str, str]:
        """
        Выполняет команду на удаленном сервере
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Tuple[int, str, str]: Код возврата, stdout, stderr
        """
        if not self.client:
            if not self.connect():
                return -1, "", "Failed to establish SSH connection"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            
            return exit_code, stdout_text, stderr_text
        except Exception as e:
            logging.error(f"Command execution error: {str(e)}")
            return -1, "", str(e)
    
    def get_file(self, remote_path: str, local_path: str) -> bool:
        """
        Загружает файл с удаленного сервера
        
        Args:
            remote_path: Путь к файлу на удаленном сервере
            local_path: Локальный путь для сохранения файла
            
        Returns:
            bool: True если файл успешно загружен
        """
        if not self.client:
            if not self.connect():
                return False
        
        try:
            from scp import SCPClient
            scp = SCPClient(self.client.get_transport())
            scp.get(remote_path, local_path)
            scp.close()
            return True
        except Exception as e:
            logging.error(f"File download error: {str(e)}")
            return False
    
    def find_files(self, remote_dir: str, pattern: str) -> List[str]:
        """
        Ищет файлы по шаблону в удаленной директории
        
        Args:
            remote_dir: Директория для поиска
            pattern: Шаблон имени файла (поддерживается glob)
            
        Returns:
            List[str]: Список полных путей к найденным файлам
        """
        command = f"find {remote_dir} -name '{pattern}' -type f"
        exit_code, stdout, _ = self.execute_command(command)
        
        if exit_code == 0:
            return [line.strip() for line in stdout.split('\n') if line.strip()]
        return []
    
    def get_printer_config(self, remote_config_path: str, local_dir: str) -> Optional[str]:
        """
        Загружает файл конфигурации принтера
        
        Args:
            remote_config_path: Путь к файлу конфигурации на принтере
            local_dir: Локальная директория для сохранения
            
        Returns:
            Optional[str]: Полный путь к загруженному файлу или None в случае ошибки
        """
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        local_path = os.path.join(local_dir, os.path.basename(remote_config_path))
        
        if self.get_file(remote_config_path, local_path):
            return local_path
        return None
    
    def get_shaper_data(self, local_dir: str) -> List[str]:
        """
        Загружает файлы данных акселерометра для input shaper
        
        Args:
            local_dir: Локальная директория для сохранения
            
        Returns:
            List[str]: Список полных путей к загруженным файлам
        """
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        # Поиск файлов с данными акселерометра
        remote_files = self.find_files("/tmp", "calibration_data_*.csv")
        
        downloaded_files = []
        for remote_file in remote_files:
            local_path = os.path.join(local_dir, os.path.basename(remote_file))
            if self.get_file(remote_file, local_path):
                downloaded_files.append(local_path)
        
        return downloaded_files