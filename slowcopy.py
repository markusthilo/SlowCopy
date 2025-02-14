#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.6.1_2025-02-13'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Copy to import folder and generate trigger file'
__distribution__ = 'Test_THI'	# for testrunns
__destination__ = 'P:/test_import/'	# path for testruns
__logging__ = 'P:/test_logs/'	# path for testruns
__update__ = 'P:/SlowCopy/dist/'	# path for testrunns

### standard libs ###
import logging
from sys import executable as __executable__
from pathlib import Path
from argparse import ArgumentParser
from re import search, sub
from subprocess import Popen, PIPE, STDOUT, STARTUPINFO, STARTF_USESHOWWINDOW
from threading import Thread
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import file_digest
from multiprocessing import Pool, cpu_count
from time import strftime, sleep, perf_counter
from datetime import timedelta
### tk libs ###
from tkinter import Tk, PhotoImage
from tkinter.font import nametofont
from tkinter.ttk import Frame, Label, Button
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import askyesno, showerror
from tkinter.filedialog import askdirectory
from idlelib.tooltip import Hovertip

class RoboCopy(Popen):
	'''Use Popen to run tools on Windows'''

	def __init__(self, src, dst, *args, files=()):
		'''Create robocopy process'''
		cmd = ['Robocopy.exe', src, dst]
		if files:
			cmd.extend(files)
		if args:
			cmd.extend(args)
		cmd.extend(['/fp', '/ns', '/njh', '/njs', '/nc', '/unicode'])
		self.startupinfo = STARTUPINFO()
		self.startupinfo.dwFlags |= STARTF_USESHOWWINDOW
		super().__init__(cmd,
			stdout = PIPE,
			stderr = STDOUT,
			encoding = 'utf-8',
			errors = 'ignore',
			universal_newlines = True,
			startupinfo = self.startupinfo
		)

	def run(self):
		'''Run process'''
		for line in self.stdout:
			if stripped := line.strip():
				yield stripped

class RoboCopyDir(RoboCopy):
	'''Run robocopy to copy dir tree'''

	def __init__(self, src, dst):
		'''Create robocopy process'''
		super().__init__(src, dst, '/e', '/compress', '/mt')

class RoboCopyFiles(RoboCopy):
	'''Run robocopy to copy files'''

	def __init__(self, src, dst, file_paths):
		'''Create robocopy process'''
		super().__init__(src, dst, '/compress', '/mt', '/nc', files=file_paths)

class HashThread(Thread):
	'''Calculate hashes'''

	@staticmethod
	def md5(path):
		'''Calculate md5 hash of file'''
		with path.open('rb') as fh:
			return file_digest(fh, 'md5').hexdigest()

	def __init__(self, root_path, dst_path, zip_paths, file_paths):
		'''Generate object to zip and calculate hashes'''
		super().__init__()
		self.root_path = root_path
		self.dst_path = dst_path
		self.zip_paths = zip_paths
		self.file_paths = file_paths

	def run(self):
		'''Calculate hashes'''
		logging.info(f'Starte Berechnung von {len(self.zip_paths) + len(self.file_paths)} Hash-Werten')
		self.hashes = [(path.with_suffix('.zip'), self.md5(self.dst_path.parent / path.with_suffix('.zip'))) for path in self.zip_paths]
		self.hashes.extend([(path, self.md5(self.root_path.parent / path)) for path in self.file_paths])
		logging.info('Hash-Wert-Berechnung ist abgeschlossen')

	def get_hashes(self):
		'''Return relative paths and hashes'''
		for path, md5 in self.hashes:
			yield path, md5

class Copy:
	'''Copy functionality'''

	### hard coded configuration ###
	LOGLEVEL = logging.INFO				# set log level
	DISTRIBUTION = __distribution__		# name of the targeted user/department
	DST_PATH = Path(__destination__)	# root directory to copy
	LOG_PATH = Path(__logging__)		# directory to write logs that trigger surveillance
	LOG_NAME = 'log.txt' 				# log file name
	TSV_NAME = 'fertig.txt'				# file name for csv output textfile - file is generaten when all is done
	UPDATE_PATH = Path(__update__)		# directory where updates can be found
	UPDATE_NAME = 'version.txt'			# trigger filename for updates (textfile with version number)
	MAX_PATH_LEN = 230					# throw error when paths have more chars
	BLACKLIST = (						# prohibited at path depth 1
		'fertig.txt',
		'verarbeitet.txt',
		'fehler.txt',
		'start.txt',
		'zu_loeschen.txt'
	)
	ZIP_DEPTH = 2						# path depth where subdirs will be zipped
	ZIP_FILE_QUANTITY = 500				# minimal quantity of files in subdir to zip
	PREVENT_ZIP = r'PortableCase'		# do not zip if path contains this
	TOPDIR_REG = r'^[0-9]{6}-([0-9]{4}|[0-9]{6})-[iSZ0-9][0-9]{5}$'	# how the top dir has to look

	@staticmethod
	def check_update():
		'''Check if there is a new version'''
		def _int(string):
			return int(sub(r'[^0-9]', '', string))	
		try:
			new_version = Copy.UPDATE_PATH.joinpath(Copy.UPDATE_NAME).read_text(encoding='utf-8')
		except:
			return
		if _int(new_version) > _int(__version__):
			return new_version

	@staticmethod
	def download_update(version, dir_path):
		'''Download updatet version'''
		filename = f"slowcopy-{Copy.DISTRIBUTION.lower().replace(' ', '')}_v{version}.exe"
		dir_path.joinpath(filename).write_bytes(Copy.UPDATE_PATH.joinpath(filename).read_bytes())

	@staticmethod
	def bad_source(root_path):
		'''Check if source directory is ok'''
		if not root_path.is_dir():
			return f'{root_path} ist ein kein Verzeichnis'
		if not search(Copy.TOPDIR_REG, root_path.name):
			return f'{root_path} hat nicht das korrekte Namensformat (POLIKS-Vorgansnummer)'
		if (Copy.DST_PATH / root_path.name / Copy.TSV_NAME).is_file():
			return f'{root_path} befindet sich bereits im Ziel- bzw. Importverzeichnis'
		for path in root_path.rglob('*'):
			if path.is_dir() and path.name in Copy.BLACKLIST:
				return f'Ein Verzeichnis {path} darf sich nicht im Quellverzeichnis befinden.'
			if len(f'{path.absolute()}') > Copy.MAX_PATH_LEN:
				return f'Der Pfad {path.absolute()} hat mehr als {Copy.MAX_PATH_LEN} Zeichen'
			if path.is_file() and path.name in Copy.BLACKLIST:
				return f'Eine Datei {path} darf sich nicht im Quellverzeichnis befinden.'

	def __init__(self, root_path, echo=print):
		'''Generate object to copy and to zip'''
		self.echo = echo
		self.root_path = root_path.resolve()
		start_time = perf_counter()
		if ex := self.bad_source(root_path):
			echo(f'ERROR: {ex}')
			raise ValueError(ex)
		dst_path = self.DST_PATH / root_path.name
		try:
			dst_path.mkdir(exist_ok=True)
		except Exception as ex:
			echo(f'ERROR: kann das Zielverzeichnis {dst_path} nicht erstellen:\n{ex}')
			raise OSError(ex)
		log_path = self.LOG_PATH / root_path.name
		try:
			log_path.mkdir(exist_ok=True)
		except Exception as ex:
			echo(f'ERROR: kann das Log-Verzeichnis {log_path} nicht erstellen:\n{ex}')
			raise OSError(ex)
		try:
			logging.basicConfig(	# start logging
				level = self.LOGLEVEL,
				filename = log_path / f'{strftime('%y%m%d-%H%M')}-{self.LOG_NAME}',
				format = '%(asctime)s %(levelname)s: %(message)s',
				datefmt = '%Y-%m-%d %H:%M:%S'
			)
		except Exception as ex:
			echo(f'ERROR: kann das Loggen nicht starten:\n{ex}')
			raise RuntimeError(ex)
		msg = f'Das Kopieren von {root_path} nach {dst_path} wird vorbereitet'
		logging.info(msg)
		echo(msg)
		try:
			dirs = {Path(self.root_path.name): {'depth': 0, 'size': 0, 'files': 0}}
			for path in self.root_path.rglob('*'):
				if path.is_dir():
					rel_path = path.relative_to(self.root_path.parent)
					dirs[rel_path] = {'depth': len(list(rel_path.parents)) - 1, 'size': 0, 'files': 0}
			files = dict()
			for path in self.root_path.rglob('*'):	# analyze root structure
				if path.is_file():
					rel_path = path.relative_to(self.root_path.parent)
					depth = len(list(rel_path.parents)) - 1
					size = path.stat().st_size
					files[rel_path] = {'depth': depth, 'size': size}
					for parent in rel_path.parents[:-1]:
						dirs[parent]['size'] += size
						dirs[parent]['files'] += 1
			dir_paths2zip = [	# look for dirs with to much files for normal copy
				path for path, infos in dirs.items()
				if infos['depth'] == self.ZIP_DEPTH	# logic to choose what to zip
					and infos['files'] >= self.ZIP_FILE_QUANTITY
					and not search(self.PREVENT_ZIP, f'{path}')
			]
			dir_paths2robocopy = [	# dirs that will copied entirely by robocopy
				path for path, infos in dirs.items()
				if infos['depth'] == self.ZIP_DEPTH and not path in dir_paths2zip
			]
			dir_paths2make = [	# dirs that have to be created
				path for path, infos in dirs.items() if infos['depth'] < self.ZIP_DEPTH
			]
			files2robocopy = dict()	# files that will copied by robocopy
			for this_dir in dir_paths2make:
				files_in_dir = [path.name for path in files if path.parent == this_dir]
				if files_in_dir:
					files2robocopy[this_dir] = files_in_dir
			file_paths2hash = list()	# all files that will not be zipped
			for path in files:
				parents = list(path.parents)
				zip_index = len(parents) - self.ZIP_DEPTH - 2
				if parents[zip_index] not in dir_paths2zip:
					file_paths2hash.append(path)
			total_size = next(iter(dirs.values()))['size']
		except Exception as ex:
			logging.error(ex)
			echo(f'ERROR: {ex}')
			raise RuntimeError(ex)
		msg = f'Starte das Kopieren von {root_path} nach {dst_path}, insgesamt {self._bytes(total_size)}'
		logging.info(msg)
		echo(msg)
		for rel_path in dir_paths2make:	# make dirs at destination
			path = dst_path.parent / rel_path
			try:
				path.mkdir(parents=True, exist_ok=True)
			except Exception as ex:
				msg = f'Konnte Verzeichnis {path} nicht erzeugen:\n{ex}'
				logging.error(msg)
				echo(f'ERROR: {msg}')
				raise OSError(ex)
		for dir_path in dir_paths2zip:
			src_path = root_path.parent / dir_path
			zip_path = self.DST_PATH / dir_path.with_suffix('.zip')
			files2zip = [path for path in src_path.rglob('*') if path.is_file()]
			total = len(files2zip)
			echo(f'Komprimiere {total} Datei(en) von {src_path} in Archivdatei {zip_path}')
			with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zf:
				for cnt, path in enumerate(files2zip, start=1):
					echo(f'{int(100*cnt/total)}%', end='\r')
					try:
						zf.write(path, path.relative_to(src_path))
					except Exception as ex:
						msg = f'Konnte {path} nicht zum Archiv {zip_path} hinzufügen:\n{ex}'
						logging.error(msg)
						echo(f'ERROR: {msg}')
						raise RuntimeError(ex)
			echo('100%')
		try:
			hash_thread = HashThread(root_path, dst_path, dir_paths2zip, file_paths2hash)
			echo(f'Starte Berechnung von {len(dir_paths2zip) + len(file_paths2hash)} MD5-Hashes')
			hash_thread.start()
		except Exception as ex:
			msg = f'Konnte Thread, der Hash-Werte bilden soll, nicht starten:\n{ex}'
			logging.error(msg)
			echo(f'ERROR: {msg}')
		for path, file_names in files2robocopy.items():
			src_path = root_path.parent / path
			cp_path = self.DST_PATH / path
			echo(f'Kopiere {len(file_names)} Datei(en) von {src_path} nach {cp_path}')
			self._run_robocopy(RoboCopyFiles(src_path, cp_path, file_names))
		for path in dir_paths2robocopy:
			src_path = root_path.parent / path
			cp_path = self.DST_PATH / path
			echo(f'Kopiere {src_path}) nach {cp_path}')
			self._run_robocopy(RoboCopyDir(src_path, cp_path))
		msg = 'Robocopy.exe ist fertig, starte Überprüfung anhand Dateigröße'
		logging.info(msg)
		echo(msg)
		errors = 0
		mismatches = 0
		total = len(file_paths2hash)
		for cnt, path in enumerate(file_paths2hash, start=1):
			echo(f'{int(100*cnt/total)}%', end='\r')
			abs_path = self.DST_PATH / path
			try:
				size = abs_path.stat().st_size
			except Exception as ex:
				msg = f'Dateigröße von {abs_path} konnte nicht ermittelt werden:\n{ex}'
				logging.warning(msg)
				echo(f'WARNING: {msg}')
				errors += 1
			else:
				if size != files[path]['size']:
					msg = f'Dateigrößenabweichung: {root_path.parent / path} => {self._bytes(files[path]['size'])}, {dst_path} => {self._bytes(size)}'
					logging.warning(msg)
					echo(f'WARNING: {msg}')
					mismatches += 1
		if hash_thread.is_alive():
			msg = 'Führe die Hash-Wert-Berechnung fort'
			logging.info(msg)
			echo(msg)
			index = 0
			while hash_thread.is_alive():
				echo(f'{"|/-\\"[index]}  ', end='\r')
				index += 1
				if index > 3:
					index = 0
				sleep(.25)
			echo('MD5-Hashes-Berechnung ist abgeschlossen')
		hash_thread.join()
		tsv = 'Pfad\tMD5-Hash'
		for path, md5 in hash_thread.get_hashes():
			tsv += f'\n{path}\t{md5}'
		log_tsv_path = log_path / f'{strftime('%y%m%d-%H%M')}-{self.TSV_NAME}'
		try:
			log_tsv_path.write_text(tsv, encoding='utf-8')
		except Exception as ex:
			msg = f'Konnte Log-Datei {log_tsv_path} nicht erzeugen:\n{ex}'
			logging.error(msg)
			echo(f'ERROR: {msg}')
			raise OSError(ex)
		if errors:
			msg = f'Die Grö0e von {errors} Datei(en) konnte nicht ermittelt werden'
			logging.error(msg)
			echo(f'ERROR: {msg}')
			if not mismatches:
				raise OSError(msg)
		if mismatches:
			msg = f'Bei {mismatches} Datei(en) stimmt die Größe der Zieldatei nicht mit der Ausgangsdatei überein'
			logging.error(msg)
			echo(f'ERROR: {msg}')
			raise RuntimeError(msg)
		dst_tsv_path = dst_path / self.TSV_NAME
		try:
			dst_tsv_path.write_text(tsv, encoding='utf-8')
		except Exception as ex:
			msg = f'Konnte {dst_tsv_path} nicht erzeugen:\n{ex}'
			logging.error(msg)
			echo(f'ERROR: {msg}')
			raise OSError(ex)
		end_time = perf_counter()
		delta = end_time - start_time
		msg = f'Fertig. Das Kopieren dauerte {timedelta(seconds=delta)} (Stunden, Minuten, Sekunden).'
		logging.info(msg)
		echo(msg)
		logging.shutdown()

	def _bytes(self, size, format_k='{iec} / {si}', format_b='{b} byte(s)'):
		'''Genereate readable size string,
			format_k: "{iec} / {si} / {b} bytes" gives e.g. 9.54 MiB / 10.0 MB / 10000000 bytes
			format_b will be returned if size < 5 bytes
		'''
		def _round(*base):	# intern function to calculate human readable
			for prefix, b in base:
				rnd = round(size/b, 2)
				if rnd >= 1:
					break
			if rnd >= 10:
				rnd = round(rnd, 1)
			if rnd >= 100:
				rnd = round(rnd)
			return f'{rnd} {prefix}', rnd
		try:	# start method here
			size = int(size)
		except (TypeError, ValueError):
			return 'undetected'
		iec = None
		rnd_iec = 0
		si = None
		rnd_si = 0
		if '{iec}' in format_k:
			iec, rnd_iec = _round(('PiB', 2**50), ('TiB', 2**40), ('GiB', 2**30), ('MiB', 2**20), ('kiB', 2**10))
		if '{si}' in format_k:
			si, rnd_si = _round(('PB', 10**15), ('TB', 10**12), ('GB', 10**9), ('MB', 10**6), ('kB', 10**3))
		if not '{b}' in format_k and rnd_iec == 0 and rnd_si == 0:
			return format_b.format(b=size)
		return format_k.format(iec=iec, si=si, b=size)

	def	_run_robocopy(self, robocopy):
		'''Run Robocopy.exe and handle output'''
		for line in robocopy.run():
			if line.endswith('%'):
				self.echo(line, end='\r')
			else:
				self.echo(line)
		returncode = robocopy.wait()
		if returncode > 3:
			msg = f'Robocopy.exe hatte ein Problem beim kopieren von Dateien aus {src_path} nach {dst_path}, Rückgabewert: {returncode}'
			logging.error(msg)
			self.echo(f'ERROR: {msg}')
			raise ChildProcessError(ex)

class Worker(Thread):
	'''Thread that does the work while Tk is running the GUI'''

	def __init__(self, gui):
		'''Get all attributes from GUI and run Copy'''
		super().__init__()
		self.gui = gui
		self.errors = False

	def run(self):
		'''Run thread'''
		for source_path in self.gui.source_paths:
			try:
				copy = Copy(source_path, echo=self.gui.echo)
			except:
				self.errors = True
		self.gui.finished(self.errors)

class Gui(Tk):
	'''GUI look and feel'''

	PAD = 4
	X_FACTOR = 60
	Y_FACTOR = 40
	LABEL = f'Distribution {__distribution__}'
	GREEN_FG = 'black'
	GREEN_BG = 'pale green'
	RED_FG = 'black'
	RED_BG = 'coral'

	def __init__(self, dir_path, icon_base64):
		'''Open application window'''
		super().__init__()
		self.worker = None
		self.title(f'SlowCopy v{__version__}')
		self.rowconfigure(1, weight=1)
		self.columnconfigure(1, weight=1)
		self.rowconfigure(3, weight=1)
		self.wm_iconphoto(True, PhotoImage(data=icon_base64))
		self.protocol('WM_DELETE_WINDOW', self._quit_app)
		font = nametofont('TkTextFont').actual()
		self.font_family = font['family']
		self.font_size = font['size']
		self.min_size_x = self.font_size * self.X_FACTOR
		self.min_size_y = self.font_size * self.Y_FACTOR
		self.minsize(self.min_size_x , self.min_size_y)
		self.geometry(f'{self.min_size_x}x{self.min_size_y}')
		self.resizable(True, True)
		self.padding = int(self.font_size / self.PAD)
		frame = Frame(self)
		frame.grid(row=0, column=0, columnspan=2, sticky='news',
			ipadx=self.padding, ipady=self.padding, padx=self.padding, pady=self.padding)
		Label(frame, text=self.LABEL).pack(padx=self.padding, pady=self.padding)
		frame = Frame(self)
		frame.grid(row=1, column=0,	sticky='n')
		self.source_button = Button(frame, text='Quellverzeichnis', command=self._select_dir)
		self.source_button.pack(padx=self.padding, pady=self.padding, fill='x', expand=True)
		Hovertip(self.source_button, 'Füge das zu kopierende Verzeichnis hinzu (POLIKS-Vorgangsnummer).')
		self.source_text = ScrolledText(self, font=(self.font_family, self.font_size),
			padx = self.padding, pady = self.padding)
		self.source_text.grid(row=1, column=1, sticky='news',
			ipadx=self.padding, ipady=self.padding, padx=self.padding, pady=self.padding)
		frame = Frame(self)
		frame.grid(row=2, column=1, sticky='news', padx=self.padding, pady=self.padding)
		Label(frame, text='Kopiere ins MSD-Importverzeichnis').pack(padx=self.padding, pady=self.padding, side='left')
		self.exec_button = Button(frame, text='Start', command=self._execute)
		self.exec_button.pack(padx=self.padding, pady=self.padding, side='right')
		Hovertip(self.exec_button, 'Starte den Kopiervorgang')
		self.info_text = ScrolledText(self, font=(self.font_family, self.font_size),
			padx = self.padding, pady = self.padding)
		self.info_text.grid(row=3, column=0, columnspan=2, sticky='news',
			ipadx=self.padding, ipady=self.padding, padx=self.padding, pady=self.padding)
		self.info_text.bind('<Key>', lambda dummy: 'break')
		self.info_text.configure(state='disabled')
		self.info_fg = self.info_text.cget('foreground')
		self.info_bg = self.info_text.cget('background')
		self.info_newline = True
		frame = Frame(self)
		frame.grid(row=4, column=1, sticky='news', padx=self.padding, pady=self.padding)
		self.info_label = Label(frame)
		self.info_label.pack(padx=self.padding, pady=self.padding, side='left')
		self.label_fg = self.info_label.cget('foreground')
		self.label_bg = self.info_label.cget('background')
		self.quit_button = Button(frame, text='Verlassen', command=self._quit_app)
		self.quit_button.pack(padx=self.padding, pady=self.padding, side='right')
		new_version = Copy.check_update()
		if new_version and askyesno(
			title = f'Eine neuere Version steht bereit ({new_version}!',
			message = 'Neu Version herunterladen und diese Anwendung verlassen?'
		):
			directory = askdirectory(title='Wähle das Zielverzeichnis für die neue Slowcopy-Version', mustexist=True)
			if directory:
				try:
					Copy.download_update(new_version, Path(directory))
				except Exception as ex:
					showerror(
						title = 'Fehler',
						message= f'Die neue Version von SlowCopy konnte nicht nach {directory} kopiert werden:\n{ex}'
					)
				self.destroy()
		else:
			self._init_warning()
			self._add_dir(dir_path)

	def _add_dir(self, directory):
		'''Add directory into field'''
		if not directory:
			return
		dir_path = Path(directory).absolute()
		old_paths = self._get_source_paths()
		if old_paths and dir_path in old_paths:
			return
		error = Copy.bad_source(dir_path)
		if error:
			showerror(title='Fehler', message=error)
			return
		self.source_text.insert('end', f'{dir_path}\n')

	def _select_dir(self):
		'''Select directory to add into field'''
		directory = askdirectory(title='Wähle das Quellverzeichnis aus', mustexist=True)
		if directory:
			self._add_dir(directory)

	def echo(self, *arg, end=None):
		'''Write message to info field (ScrolledText)'''
		msg = ' '.join(arg)
		self.info_text.configure(state='normal')
		if not self.info_newline:
			self.info_text.delete('end-2l', 'end-1l')
		self.info_text.insert('end', f'{msg}\n')
		self.info_text.configure(state='disabled')
		if self.info_newline:
			self.info_text.yview('end')
		self.info_newline = end != '\r'

	def _clear_info(self):
		'''Clear info text'''
		self.info_text.configure(state='normal')
		self.info_text.delete('1.0', 'end')
		self.info_text.configure(state='disabled')
		self.info_text.configure(foreground=self.info_fg, background=self.info_bg)
		self._warning_state = 'stop'

	def _get_source_paths(self):
		'''Start copy process / worker'''
		text = self.source_text.get('1.0', 'end').strip()
		if text:
			return [Path(source_dir.strip()).absolute() for source_dir in text.split('\n')]
		
	def _execute(self):
		'''Start copy process / worker'''
		self.source_paths = self._get_source_paths()
		if not self.source_paths:
			return
		self.source_button.configure(state='disabled')
		self.source_text.configure(state='disabled')
		self.exec_button.configure(state='disabled')
		self._clear_info()
		self.worker = Worker(self)
		self.worker.start()

	def _init_warning(self):
		'''Init warning functionality'''
		self._warning_state = 'disabled'
		self._warning()

	def _warning(self):
		'''Show flashing warning'''
		if self._warning_state == 'enable':
			self.info_label.configure(text='ACHTUNG!')
			self._warning_state = '1'
		if self._warning_state == '1':
			self.info_label.configure(foreground=self.RED_FG, background=self.RED_BG)
			self._warning_state = '2'
		elif self._warning_state == '2':
			self.info_label.configure(foreground=self.label_fg, background=self.label_bg)
			self._warning_state = '1'
		elif self._warning_state != 'disabled':
			self.info_label.configure(text= '', foreground=self.label_fg, background=self.label_bg)
			self._warning_state = 'disabled'
		self.after(500, self._warning)

	def finished(self, errors):
		'''Run this when Worker has finished'''
		self.source_text.configure(state='normal')
		self.source_text.delete('1.0', 'end')
		self.source_button.configure(state='normal')
		self.exec_button.configure(state='normal')
		self.quit_button.configure(state='normal')
		self.worker = None
		if errors:
			self.info_text.configure(foreground=self.RED_FG, background=self.RED_BG)
			self._warning_state = 'enable'
			showerror(
				title = 'Achtung',
				message= 'Es traten Fehler auf'
			)
		else:
			self.info_text.configure(foreground=self.GREEN_FG, background=self.GREEN_BG)

	def _quit_app(self):
		'''Quit app, ask when copy processs is running'''
		if self.worker and not askyesno(
			title='Kopiervorgang läuft!',
			message='Wirklich die Anwendung verlassen und den Kopiervorgang abbrechen?'
		):
			return
		self.destroy()

if __name__ == '__main__':  # start here when run as application
	argparser = ArgumentParser(prog=f'SlowCopy Version {__version__}', description='Copy into MSD network')  
	argparser.add_argument('-g', '--gui', action='store_true',
		help='Use GUI with given root directory as command line parameters.')
	argparser.add_argument('source', nargs='?', help='Source directory', metavar='DIRECTORY')
	args = argparser.parse_args()
	root_path = Path(args.source.strip().strip('"')).absolute() if args.source else None
	if root_path and not args.gui and Path(__executable__).name == 'python.exe':	# run in terminal
		copy = Copy(root_path)
	else:	# open gui if no argument is given
		Gui(root_path, '''iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAACEFBMVEUAAAH7AfwVFf8WFv4XF/0Y
GPwZGfwaGvsaGvwbG/scHPodHfkeHvkfH/kgIPggIPkhIfciIvYjI/UkJPUlJfQnJ/IoKPEpKfAq
KvArK+4rK+8sLO4tLewtLe0uLusuLuwvL+swMOoxMegxMekyMuczM+UzM+Y0NOQ0NOU1NeM1NeQ1
NeU2NuE2NuI2NuM3N+A3N+E4ON85Od45Od86Otw6Ot07O9o7O9s8PNk8PNs9Pdg9Pdk+PtY+Ptc/
P9RAQNJAQNNAQNRBQdBBQdFBQdJCQs5CQs9CQtBDQ81DQ85ERMpERMtERMxFRclFRcpGRsZGRsdH
R8RHR8VHR8ZISMJISMNJScBJScFKSr1KSr5KSr9LS7tMTLhMTLlMTLpNTbdNTbhOTrROTrVPT7FP
T7JPT7NQUK1QUK5QUK9QULBRUapRUatRUaxSUqZSUqdSUqhSUqlSUqpTU6RTU6ZUVKFUVKJUVKNV
VZ1VVZ5VVZ9VVaFWVplWVppWVptWVpxXV5VXV5ZXV5dXV5hYWJFYWJJYWJNYWJRZWY5ZWY9ZWZBa
WohaWolaWopaWotbW4RbW4ZbW4dcXH5cXH9cXIBcXIFcXIJcXINdXXldXXpdXXtdXXxdXX1eXnNe
XnVeXnZeXndeXnhfX21fX25fX3BfX3FfX3JgYGVgYGZgYGdgYGlgYGpgYGtgYGxhYWFhYWJhYWRt
OtjpAAAAAXRSTlMAQObYZgAAAWlJREFUSMftlc9LAkEUx4e3KrqXWAg6hUEh4T0shQgKRArpEEUb
4pKS0TEMAulWrEF4yKOC5WFbD9/xX2xWwx/pLDtEdfF72n3f72fezJuFZWyhfxV+G1DMA4rYEIBC
HpI8hgqax1gzdTa7zmR+2p3f91t+wod0oxIiaH40+7kA0KuXKnZ3YLmNm1Ktzb8yEsBeJ6GVK+HU
k2HxaOQ5plpP59/jFEls6NoD8GyQtpY06BR+wCOR2e+/ljmcTYpUXP5mNQah+VcDVImKw3otRLsT
IRnQ1Ek/63j1E9LuxiHIAJ7XiJYLPWCfojbkQx6N2jlfEqNJudij2EsQAGjldO8ghxR+CgYA9zHa
RpHICgDYTXGxXYMyaMVotS18/uELXES3TCulURn8iChuWseJa1+g4H0YFEq7os9OaPBS8gEY2pVs
OpO9dT3HqebSmYPLji8QQEyVYIoEY4qE6o5+cgD8xYF9mcXPV12fPIIrXx13KAAAAAAASUVORK5C
YII=''').mainloop()	# give tk the icon as base64 and open main window
