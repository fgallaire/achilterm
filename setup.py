from setuptools import setup, find_packages

version = '0.11'

setup(name='Achilterm',
      version=version,
      author='Florent Gallaire',
      author_email='fgallaire@gmail.com',
      url='http://fgallaire.github.io/achilterm',
      license='GNU AGPL',
      keywords='sh shell bash',
      packages=find_packages(exclude=['docs', 'examples', 'tests']),
      py_modules=['achilterm'],
      include_package_data=True,
      zip_safe=False,
      install_requires=['webob<1.0'],
      )
