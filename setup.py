from setuptools import setup
from achilterm.achilterm import __version__ as version
import os

setup(name='Achilterm',
      version=version,
      description='A lightweight UTF-8 web based terminal',
      author='Florent Gallaire',
      author_email='fgallaire@gmail.com',
      url='http://fgallaire.github.io/achilterm',
      license='GNU AGPLv3+',
      keywords='sh shell bash',
      classifiers=[
          "Development Status :: 6 - Mature",
          "Environment :: Web Environment",
          "Intended Audience :: Developers",
          "Intended Audience :: System Administrators",
          "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
          "Topic :: System :: Shells",
          "Topic :: Terminals :: Terminal Emulators/X Terminals",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.5",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.2",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
      ],
      packages=['achilterm'],
      package_data={
          'achilterm': ['*.js', '*.html', '*.css']
      },
      entry_points={
          "console_scripts": ['achilterm = achilterm.achilterm:main']
      },
      data_files=[
          (os.path.join('share','man','man1'), ['achilterm.1'])
      ],
      include_package_data=True,
      zip_safe=False,
      install_requires=['webob>=1.0'],
      )
