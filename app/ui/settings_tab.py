#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from app.ui.language import _
import paramiko
from scp import SCPClient

class SettingsTab(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main = main_window
        self.settings = {
            'hardware': {
                'screw_pitch': 0.7,
                'min_adjustment': 0.1,
                'max_adjustment': 2.0,
                'tape_thickness': 0.06,
                'belt_tooth_mm': 0.4
            },
            'thresholds': {
                'belt_threshold': 0.6,
                'screw_threshold': 0.4,
                'tape_threshold': 0.2
            },
            'ssh': {
                'host': '',
                'username': '',
                'password': ''
            },
            'visualization': {
                'interpolation_factor': 100,
                'show_minutes': True,
                'show_degrees': True
            },
            'environment': {
                'measurement_temp': 25.0,
                'target_temp': 25.0,
                'thermal_expansion_coeff': 0.0
            },
            'workflow': {
                'enable_belt': True,
                'enable_screws': True,
                'enable_tape': True
            }
        }
        
        self.printer_cfg_button = None
        self.shapers_button = None
        self.ssh_connected = False
        self.environment_entries = {}
        
        self.load_settings()
        self.create_layout()

    def get_settings(self):
        return self.settings

    def create_layout(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_hardware_tab()
        self.create_thresholds_tab()
        self.create_ssh_tab()
        self.create_visualization_tab()
        self.create_environment_tab()
        self.create_workflow_tab()
        self.create_control_buttons()
        
    def create_hardware_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=_('settings_tab.hardware'))
        
        entries = [
            (_('settings_tab.screw_pitch'), 'screw_pitch'),
            (_('settings_tab.min_adjustment'), 'min_adjustment'),
            (_('settings_tab.max_adjustment'), 'max_adjustment'),
            (_('settings_tab.tape_thickness'), 'tape_thickness'),
            (_('settings_tab.belt_tooth_mm'), 'belt_tooth_mm')
        ]
        
        self.hardware_entries = {}
        for i, (label, key) in enumerate(entries):
            ttk.Label(frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(self.settings['hardware'][key]))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.hardware_entries[key] = entry
            
        info_frame = ttk.LabelFrame(frame, text=_("Information"))
        info_frame.grid(row=len(entries), column=0, columnspan=2, padx=5, pady=10, sticky='ew')

        ttk.Label(info_frame, text=_("settings_tab.hardware_info"), justify='left', wraplength=350).pack(padx=5, pady=5)
            
    def create_thresholds_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=_('settings_tab.thresholds'))
        
        entries = [
            (_('settings_tab.belt_threshold'), 'belt_threshold'),
            (_('settings_tab.screw_threshold'), 'screw_threshold'),
            (_('settings_tab.tape_threshold'), 'tape_threshold')
        ]
        
        self.threshold_entries = {}
        for i, (label, key) in enumerate(entries):
            ttk.Label(frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(self.settings['thresholds'][key]))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.threshold_entries[key] = entry
            
        info_frame = ttk.LabelFrame(frame, text=_("Leveling Algorithm"))
        info_frame.grid(row=len(entries), column=0, columnspan=2, padx=5, pady=10, sticky='ew')
        
        ttk.Label(info_frame, text=_("settings_tab.thresholds_info"), justify='left', wraplength=400).pack(padx=5, pady=5)
            
    def create_ssh_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=_('settings_tab.ssh'))
        
        ttk.Label(frame, text=_('settings_tab.host')).pack(anchor='w', padx=5, pady=2)
        self.ssh_host = ttk.Entry(frame)
        self.ssh_host.insert(0, self.settings['ssh']['host'])
        self.ssh_host.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(frame, text=_('settings_tab.username')).pack(anchor='w', padx=5, pady=2)
        self.ssh_user = ttk.Entry(frame)
        self.ssh_user.insert(0, self.settings['ssh']['username'])
        self.ssh_user.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(frame, text=_('settings_tab.password')).pack(anchor='w', padx=5, pady=2)
        self.ssh_password = ttk.Entry(frame, show='*')
        self.ssh_password.insert(0, self.settings['ssh']['password'])
        self.ssh_password.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(frame, text=_('settings_tab.test_connection'), 
                  command=self.test_ssh_connection).pack(pady=10)
        
        self.printer_cfg_button = ttk.Button(frame, text=_("settings_tab.get_printer_cfg"), 
                                           command=self.get_printer_cfg, state='disabled')
        self.printer_cfg_button.pack(pady=5)
        
        self.shapers_button = ttk.Button(frame, text=_("settings_tab.get_shapers"), 
                                        command=self.get_shapers, state='disabled')
        self.shapers_button.pack(pady=5)
        
        info_frame = ttk.LabelFrame(frame, text=_("SSH Information"))
        info_frame.pack(fill='x', padx=5, pady=10)
        
        ttk.Label(info_frame, text=_("settings_tab.ssh_connection_desc") + "\n\n" + 
                  _("settings_tab.connection_requirements") + "\n" + 
                  "• " + _("settings_tab.ip_or_hostname") + "\n" + 
                  "• " + _("settings_tab.username_desc") + "\n" + 
                  "• " + _("settings_tab.password_desc"), justify='left').pack(padx=5, pady=5)
                  
    def create_visualization_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=_('settings_tab.visualization'))

        ttk.Label(frame, text=_('settings_tab.interpolation_factor')).pack(anchor='w', padx=5, pady=2)
        self.interpolation = ttk.Entry(frame)
        self.interpolation.insert(0, str(self.settings['visualization']['interpolation_factor']))
        self.interpolation.pack(fill='x', padx=5, pady=2)
        
        display_frame = ttk.LabelFrame(frame, text=_("Display Settings"))
        display_frame.pack(fill='x', padx=5, pady=10)
        
        self.show_minutes_var = tk.BooleanVar(value=self.settings['visualization']['show_minutes'])
        ttk.Checkbutton(display_frame, text=_('settings_tab.show_minutes'), 
                       variable=self.show_minutes_var).pack(anchor='w', padx=5, pady=2)
                       
        self.show_degrees_var = tk.BooleanVar(value=self.settings['visualization']['show_degrees'])
        ttk.Checkbutton(display_frame, text=_('settings_tab.show_degrees'), 
                       variable=self.show_degrees_var).pack(anchor='w', padx=5, pady=2)
        
        info_frame = ttk.LabelFrame(frame, text=_("Notes"))
        info_frame.pack(fill='x', padx=5, pady=10)

        ttk.Label(info_frame, text=_("settings_tab.visualization_info"), justify='left').pack(padx=5, pady=5)

    def create_environment_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=_('settings_tab.environment'))

        entries = [
            (_('settings_tab.measurement_temp'), 'measurement_temp'),
            (_('settings_tab.target_temp'), 'target_temp'),
            (_('settings_tab.thermal_coeff'), 'thermal_expansion_coeff')
        ]

        self.environment_entries = {}
        for i, (label, key) in enumerate(entries):
            ttk.Label(frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(self.settings['environment'][key]))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.environment_entries[key] = entry

        info_frame = ttk.LabelFrame(frame, text=_("Information"))
        info_frame.grid(row=len(entries), column=0, columnspan=2, padx=5, pady=10, sticky='ew')
        ttk.Label(info_frame, text=_("settings_tab.environment_info"), justify='left', wraplength=360).pack(padx=5, pady=5)

    def create_workflow_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=_('settings_tab.workflow'))

        self.workflow_vars = {}
        items = [
            (_('settings_tab.enable_belt'), 'enable_belt'),
            (_('settings_tab.enable_screws'), 'enable_screws'),
            (_('settings_tab.enable_tape'), 'enable_tape')
        ]

        for i, (label, key) in enumerate(items):
            var = tk.BooleanVar(value=self.settings['workflow'][key])
            chk = ttk.Checkbutton(frame, text=label, variable=var)
            chk.grid(row=i, column=0, sticky='w', padx=5, pady=5)
            self.workflow_vars[key] = var
        
    def create_control_buttons(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text=_('settings_tab.save'), 
                  command=self.save_settings).pack(side='right', padx=5)
        ttk.Button(button_frame, text=_('settings_tab.reset'), 
                  command=self.reset_settings).pack(side='right', padx=5)
                  
    def save_settings(self):
        try:
            for key, entry in self.hardware_entries.items():
                self.settings['hardware'][key] = float(entry.get())
                
            for key, entry in self.threshold_entries.items():
                self.settings['thresholds'][key] = float(entry.get())
                
            self.settings['ssh']['host'] = self.ssh_host.get()
            self.settings['ssh']['username'] = self.ssh_user.get()
            self.settings['ssh']['password'] = self.ssh_password.get()
            
            self.settings['visualization']['interpolation_factor'] = int(self.interpolation.get())
            self.settings['visualization']['show_minutes'] = self.show_minutes_var.get()
            self.settings['visualization']['show_degrees'] = self.show_degrees_var.get()

            for key, entry in self.environment_entries.items():
                self.settings['environment'][key] = float(entry.get())

            if hasattr(self, 'workflow_vars'):
                for key, var in self.workflow_vars.items():
                    self.settings['workflow'][key] = bool(var.get())

            self.save_settings_to_file()

            if not self.settings['visualization']['show_minutes'] and not self.settings['visualization']['show_degrees']:
                messagebox.showwarning(_("Warning"), 
                    _("settings_tab.display_options_error"))
                self.settings['visualization']['show_minutes'] = True
                self.settings['visualization']['show_degrees'] = True
                self.show_minutes_var.set(True)
                self.show_degrees_var.set(True)
                self.save_settings_to_file()

            if getattr(self.main.bed_tab, 'file_loaded', False):
                self.main.bed_tab.analyze_bed()

            if hasattr(self.main, 'invalidate_workflow'):
                self.main.invalidate_workflow()

            messagebox.showinfo(_("Success"), _("settings_tab.settings_saved"))
            
        except ValueError as e:
            messagebox.showerror(_("Error"), _("settings_tab.numeric_error"))
            
    def reset_settings(self):
        if messagebox.askyesno(_("Confirm"), _("Reset all settings to default values?")):
            self.settings = {
                'hardware': {
                    'screw_pitch': 0.7,
                    'min_adjustment': 0.1,
                    'max_adjustment': 2.0,
                    'tape_thickness': 0.06,
                    'belt_tooth_mm': 0.4
                },
                'thresholds': {
                    'belt_threshold': 0.6,
                    'screw_threshold': 0.4,
                    'tape_threshold': 0.2
                },
                'ssh': {
                    'host': '',
                    'username': '',
                    'password': ''
                },
                'visualization': {
                    'interpolation_factor': 100,
                    'show_minutes': True,
                    'show_degrees': True
                },
                'environment': {
                    'measurement_temp': 25.0,
                    'target_temp': 25.0,
                    'thermal_expansion_coeff': 0.0
                },
                'workflow': {
                    'enable_belt': True,
                    'enable_screws': True,
                    'enable_tape': True
                }
            }
            
            for key, entry in self.hardware_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(self.settings['hardware'][key]))
                
            for key, entry in self.threshold_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(self.settings['thresholds'][key]))
                
            self.ssh_host.delete(0, tk.END)
            self.ssh_host.insert(0, self.settings['ssh']['host'])
            self.ssh_user.delete(0, tk.END)
            self.ssh_user.insert(0, self.settings['ssh']['username'])
            self.ssh_password.delete(0, tk.END)
            self.ssh_password.insert(0, self.settings['ssh']['password'])
            
            self.interpolation.delete(0, tk.END)
            self.interpolation.insert(0, str(self.settings['visualization']['interpolation_factor']))

            self.show_minutes_var.set(self.settings['visualization']['show_minutes'])
            self.show_degrees_var.set(self.settings['visualization']['show_degrees'])

            for key, entry in self.environment_entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(self.settings['environment'][key]))

            if hasattr(self, 'workflow_vars'):
                for key, var in self.workflow_vars.items():
                    var.set(self.settings['workflow'][key])

            if hasattr(self, 'workflow_vars'):
                for key, var in self.workflow_vars.items():
                    var.set(self.settings['workflow'][key])

            self.save_settings_to_file()
            
            messagebox.showinfo(_("Success"), _("Settings reset to default values"))
        
    def load_settings(self):
        try:
            with open('config/settings.json', 'r') as f:
                loaded_settings = json.load(f)
                self.update_nested_dict(self.settings, loaded_settings)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
            
    def update_nested_dict(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d:
                self.update_nested_dict(d[k], v)
            else:
                d[k] = v
            
    def save_settings_to_file(self):
        os.makedirs('config', exist_ok=True)
        with open('config/settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
            
    def test_ssh_connection(self):
        host = self.ssh_host.get()
        user = self.ssh_user.get()
        password = self.ssh_password.get()
        
        if not all([host, user, password]):
            messagebox.showwarning(_("Warning"), _("settings_tab.fill_ssh"))
            return
            
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print(f"Testing connection to {host} as {user}...")
            ssh.connect(host, username=user, password=password, timeout=15)
            
            stdin, stdout, stderr = ssh.exec_command('echo "test"')
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error_output = stderr.read().decode().strip()
                raise Exception(f"{_('settings_tab.connection_error').format(error_output)}")
            
            ssh.close()
            
            messagebox.showinfo(_("Success"), _("settings_tab.connection_success"))
            self.ssh_connected = True
            
            if self.printer_cfg_button is not None:
                self.printer_cfg_button.config(state='normal')
            if self.shapers_button is not None:
                self.shapers_button.config(state='normal')
            
        except paramiko.AuthenticationException:
            messagebox.showerror(_("Error"), _("Authentication error. Check username and password."))
        except paramiko.SSHException as e:
            messagebox.showerror(_("Error"), _("settings_tab.connection_error").format(str(e)))
        except Exception as e:
            self.ssh_connected = False
            messagebox.showerror(_("Error"), _("settings_tab.connection_error").format(str(e)))
        finally:
            try:
                if 'ssh' in locals():
                    ssh.close()
            except:
                pass

    def get_printer_cfg(self):
        host = self.ssh_host.get()
        user = self.ssh_user.get()
        password = self.ssh_password.get()
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print(f"Connecting to {host} as {user}...")
            ssh.connect(host, username=user, password=password, timeout=15)
            
            scp = SCPClient(ssh.get_transport())
            
            remote_path = "/opt/config/printer.cfg"
            local_path = "config/printer.cfg"
            os.makedirs("config", exist_ok=True)
            print(f"Attempting to download {remote_path} to {local_path}...")
            
            scp.get(remote_path, local_path)
            
            scp.close()
            ssh.close()

            messagebox.showinfo(_("Success"), _("settings_tab.fill_printer_cfg").format(local_path))
            self.main.load_config(filepath=local_path)

        except paramiko.AuthenticationException:
            messagebox.showerror(_("Error"), _("Authentication error. Check username and password."))
        except paramiko.SSHException as e:
            messagebox.showerror(_("Error"), _("settings_tab.connection_error").format(str(e)))
        except FileNotFoundError:
            messagebox.showerror(_("Error"), _("File {remote_path} not found on the server."))
        except Exception as e:
            messagebox.showerror(_("Error"), _("settings_tab.connection_error").format(str(e)))
        finally:
            try:
                if 'scp' in locals():
                    scp.close()
                if 'ssh' in locals():
                    ssh.close()
            except:
                pass

    def get_shapers(self):
        host = self.ssh_host.get()
        user = self.ssh_user.get()
        password = self.ssh_password.get()
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print(f"Connecting to {host} as {user}...")
            ssh.connect(host, username=user, password=password, timeout=15)
            
            pattern = "/tmp/calibration_data_*.csv"
            print(f"Searching for shaper files with pattern: {pattern}")
            stdin, stdout, stderr = ssh.exec_command(f"ls {pattern}")
            shaper_files = stdout.read().decode().strip().split("\n")
            error_output = stderr.read().decode().strip()
            if error_output:
                print(f"Command error output: {error_output}")
            print(f"Found shaper files: {shaper_files}")
            
            if not shaper_files or shaper_files[0] == "":
                messagebox.showwarning(_("Warning"), _("settings_tab.no_shapers_found"))
                ssh.close()
                return
            
            scp = SCPClient(ssh.get_transport())
            
            os.makedirs("config/shapers", exist_ok=True)
            
            downloaded_files = []
            for remote_file in shaper_files:
                if remote_file and remote_file != "":
                    local_file = os.path.join("config/shapers", os.path.basename(remote_file))
                    print(f"Downloading {remote_file} to {local_file}...")
                    scp.get(remote_file, local_file)
                    downloaded_files.append(local_file)
            
            scp.close()
            ssh.close()
            
            if downloaded_files:
                messagebox.showinfo(
                    _("Success"),
                    _("settings_tab.fill_shapers").format('\n'.join(downloaded_files))
                )

                for path in downloaded_files:
                    axis_hint = self.main.shaper_tab.infer_axis_from_filename(path)
                    self.main.shaper_tab.load_data_from_file(path, axis_hint=axis_hint)
            else:
                messagebox.showwarning(_("Warning"), _("No shaper files downloaded"))
            
        except paramiko.AuthenticationException:
            messagebox.showerror(_("Error"), _("Authentication error. Check username and password."))
        except paramiko.SSHException as e:
            messagebox.showerror(_("Error"), _("settings_tab.connection_error").format(str(e)))
        except Exception as e:
            messagebox.showerror(_("Error"), _("settings_tab.connection_error").format(str(e)))
        finally:
            try:
                if 'scp' in locals():
                    scp.close()
                if 'ssh' in locals():
                    ssh.close()
            except:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = SettingsTab(root, None)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
