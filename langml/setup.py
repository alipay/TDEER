# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


__version__ = '0.6.3'


long_description = open('README.md', encoding='utf-8').read()

with open('requirements.txt', encoding='utf-8') as f:
    requirements = [l for l in f.read().splitlines() if l]

with open('dev-requirements.txt', encoding='utf-8') as f:
    test_requirements = [l for l in f.read().splitlines() if l][1:]

setup(
    name='langml',
    version=__version__,
    description='keras language machine learning toolkit.',
    long_description=long_description,
    author='niming.lxm',
    author_email='niming.lxm@alipay.com',
    platforms=['all'],
    url='',
    packages=find_packages(exclude=('tests', 'tests.*')),
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Indexing',
        'Topic :: Text Processing :: Linguistic',
    ],
    entry_points={
        'console_scripts': [
            'langml-cli = langml.cli:main',
        ],
    },
    install_requires=requirements,
    tests_require=test_requirements,
    include_package_data=True,
)
