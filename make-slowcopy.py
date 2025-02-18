#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Markus Thilo'
__version__ = '0.7.0.2025-02-18'
__license__ = 'GPL-3'
__email__ = 'markus.thilo@gmail.com'
__status__ = 'Testing'
__description__ = 'Use PyInstaller to build SlowCopy executables'

COPYTARGET_BASEPATH = '//192.168.128.150/UrkSp/Import'
UPDATE_PATH = '//192.168.128.150/UrkSp/Import/_dist'

BUILDS = (
	# user (for label),	target path in import directory,	path to log directory
	('LKA 711',			f'{COPYTARGET_BASEPATH}/LKA 711',	f'{COPYTARGET_BASEPATH}/_logs/LKA 711'),
	('LKA 712',			f'{COPYTARGET_BASEPATH}/LKA 712',	f'{COPYTARGET_BASEPATH}/_logs/LKA 712'),
	('LKA 713',			f'{COPYTARGET_BASEPATH}/LKA 713',	f'{COPYTARGET_BASEPATH}/_logs/LKA 713'),
	('LKA 714',			f'{COPYTARGET_BASEPATH}/LKA 714',	f'{COPYTARGET_BASEPATH}/_logs/LKA 714'),
	('LKA 724',			f'{COPYTARGET_BASEPATH}/LKA 724',	f'{COPYTARGET_BASEPATH}/_logs/LKA 724'),
	('DIR 3 IuK',		f'{COPYTARGET_BASEPATH}/DIR 3',		f'{COPYTARGET_BASEPATH}/_logs/DIR 3'),
	('DIR 4 IuK',		f'{COPYTARGET_BASEPATH}/DIR 4',		f'{COPYTARGET_BASEPATH}/_logs/DIR 4'),
	('DIR 5 IuK',		f'{COPYTARGET_BASEPATH}/DIR 5',		f'{COPYTARGET_BASEPATH}/_logs/DIR 5'),
	('LKA 1 IuK',		f'{COPYTARGET_BASEPATH}/LKA 1',		f'{COPYTARGET_BASEPATH}/_logs/LKA 1'),
	('LKA 2 IuK',		f'{COPYTARGET_BASEPATH}/LKA 2',		f'{COPYTARGET_BASEPATH}/_logs/LKA 2'),
	('LKA 3 IuK',		f'{COPYTARGET_BASEPATH}/LKA 3',		f'{COPYTARGET_BASEPATH}/_logs/LKA 3'),
	('LKA 4 IuK',		f'{COPYTARGET_BASEPATH}/LKA 4',		f'{COPYTARGET_BASEPATH}/_logs/LKA 4'),
	('LKA 5 IuK',		f'{COPYTARGET_BASEPATH}/LKA 5',		f'{COPYTARGET_BASEPATH}/_logs/LKA 5'),
	('LKA 8 IuK',		f'{COPYTARGET_BASEPATH}/LKA 8',		f'{COPYTARGET_BASEPATH}/_logs/LKA 8'),
	('LKA KoSt ST 2',		f'{COPYTARGET_BASEPATH}/LKA KoSt ST 2',		f'{COPYTARGET_BASEPATH}/_logs/LKA KoSt ST 2'),
	#### for test version of executable ####
	('Test THI',		'//192.168.128.150/UrkSp/Import/LKA71/SlowCopy_Test_THI',	'//192.168.128.150/UrkSp/Import/LKA71/SlowCopy_Test_THI/_logs')
)

from pathlib import Path
from shutil import rmtree
import PyInstaller.__main__

if __name__ == '__main__':	# start here
	cwd_path = Path.cwd()
	dist_path = cwd_path / 'dist'
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
	dist_path.joinpath('version.txt').write_text(slowcopy_version, encoding='utf-8')
	print(f'\nAll done, check {dist_path} for new build executables.\n')

