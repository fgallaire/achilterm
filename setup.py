from setuptools import setup, find_packages

version = '0.1'

setup(name='achilterm',
      version=version,
      keywords='sh shell bash',
      packages=find_packages(exclude=['docs', 'examples', 'tests']),
      py_modules=['achilterm'],
      include_package_data=True,
      zip_safe=False,
      install_requires=['webob'],
      )
