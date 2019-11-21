#!/usr/bin/env python3
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import io
import os
import re
from configparser import ConfigParser
from setuptools import setup, find_packages


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    if minor_version % 2:
        require = '%s >= %s.%s.dev0, < %s.%s'
    else:
        require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


config = ConfigParser()
config.read_file(open(os.path.join(os.path.dirname(__file__), 'tryton.cfg')))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
version = info.get('version', '0.0.1')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)
name = 'trytonar_payment_collect_mipago'

download_url = 'https://github.com/tryton-ar/payment_collect_mipago/tree/%s.%s' % (
    major_version, minor_version)

requires = []
for dep in info.get('depends', []):
    if dep == 'payment_collect':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif dep == 'payment_collect_afip':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif dep == 'account_ar':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif dep == 'account_invoice_ar':
        requires.append(get_require_version('trytonar_%s' % dep))
    elif not re.match(r'(ir|res)(\W|$)', dep):
        requires.append(get_require_version('trytond_%s' % dep))
requires.append(get_require_version('trytond'))

tests_require = [get_require_version('proteus'), 'pytz']
dependency_links = [
    'https://github.com/tryton-ar/bank_ar/tarball/%s.%s#egg=trytonar_bank_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/party_ar/tarball/%s.%s#egg=trytonar_party_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/payment_collect/tarball/%s.%s#egg=trytonar_payment_collect-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/payment_collect_afip/tarball/%s.%s#egg=trytonar_payment_collect_afip-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/account_ar/tarball/%s.%s#egg=trytonar_account_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/tryton-ar/account_invoice_ar/tarball/%s.%s#egg=trytonar_account_invoice_ar-%s.%s' \
        % (major_version, minor_version, major_version, minor_version),
    'https://github.com/reingart/pyafipws/tarball/py3k#egg=pyafipws',
    'https://github.com/pysimplesoap/pysimplesoap/tarball/stable_py3k#egg=pysimplesoap',
    ]
if minor_version % 2:
    dependency_links.append('https://trydevpi.tryton.org/')

setup(name=name,
    version=version,
    description='Payment collect integrates with MiPago',
    long_description=read('README'),
    author='tryton-ar',
    url='https://github.com/tryton-ar/payment_collect_mipago',
    download_url=download_url,
    project_urls={
        "Bug Tracker": 'https://github.com/tryton-ar/payment_collect_mipago/issues',
        "Documentation": 'https://docs.tryton.org/',
        "Forum": 'https://www.tryton.org/forum',
        "Source Code": 'https://github.com/tryton-ar/payment_collect_mipago',
        },
    keywords='',
    package_dir={'trytond.modules.payment_collect_mipago': '.'},
    packages=(
        ['trytond.modules.payment_collect_mipago'] +
        ['trytond.modules.payment_collect_mipago.%s' % p for p in find_packages()]
        ),
    package_data={
        'trytond.modules.payment_collect_mipago': (info.get('xml', [])
            + ['tryton.cfg', 'view/*.xml', 'locale/*.po', '*.fodt',
                'icons/*.svg', 'tests/*.rst']),
        },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: Bulgarian',
        'Natural Language :: Catalan',
        'Natural Language :: Chinese (Simplified)',
        'Natural Language :: Czech',
        'Natural Language :: Dutch',
        'Natural Language :: English',
        'Natural Language :: French',
        'Natural Language :: German',
        'Natural Language :: Hungarian',
        'Natural Language :: Italian',
        'Natural Language :: Persian',
        'Natural Language :: Polish',
        'Natural Language :: Portuguese (Brazilian)',
        'Natural Language :: Russian',
        'Natural Language :: Slovenian',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        ],
    license='GPL-3',
    python_requires='>=3.5',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    payment_collect_mipago = trytond.modules.payment_collect_mipago
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    )
