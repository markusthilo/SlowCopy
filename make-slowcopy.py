#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.0.4_2025-01-18'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Use PyInstaller to build SlowCopy executables'

COPYTARGET_BASEPATH = 'C:/Users/User/SlowCopy/Import'
UPDATE_PATH = 'C:/Users/User/SlowCopy/dist'

BUILDS = (
	# Tool-Nutzer,	Zielpfad im Import-Ordner,	Zielpfad für Log-Datei
	('THI',			'C:/Users/User/Desktop/SlowCopy_v0.0.4/test_dst',	'C:/Users/User/Desktop/SlowCopy_v0.0.4/test_log'),
)

from pathlib import Path
from shutil import rmtree
import PyInstaller.__main__

if __name__ == '__main__':	# start here
	cwd_path = Path.cwd()
	icon_path = cwd_path / 'appicon.ico'
	build_path = cwd_path / 'build'
	build_path.mkdir(exist_ok=True)
	tmp_path = build_path / 'slowcopy_tmp.py'
	slowcopy_version = __version__
	for user, dst, log in BUILDS:
		print(f'\nBulding executable for {user}\n')
		with tmp_path.open(mode='w', encoding='utf-8') as f:
			for line in cwd_path.joinpath('slowcopy.py').read_text(encoding='utf-8').split('\n'):
				if line.startswith('__distribution__ ='):
					print(f"__distribution__ = '{user}'", file=f)
				elif line.startswith('__destination__ ='):
					print(f"__destination__ = '{dst}'", file=f)
				elif line.startswith('__logging__ ='):
					print(f"__logging__ = '{log}'", file=f)
				elif line.startswith('__update__ ='):
					print(f"__update__ = '{UPDATE_PATH}'", file=f)
				else:
					print(line, file=f)
					if line.startswith('__version__ ='):
						slowcopy_version = line.split('=')[1].strip().strip('"\'')
		slowcopy_name = f"slowcopy-{user.lower().replace(' ', '')}_v{slowcopy_version}"
		PyInstaller.__main__.run([
			'--onefile',
			'--noconsole',
			'--name', slowcopy_name,
			'--icon', f'{icon_path}',
			f'{tmp_path}'
		])
		cwd_path.joinpath(f'{slowcopy_name}.spec').unlink(missing_ok=True)
	rmtree(build_path)
	cwd_path.joinpath('dist', 'version.txt').write_text(slowcopy_version, encoding='utf-8')
	print(f"\nAll done, check {cwd_path/'dist'} for new build executables.\n")
