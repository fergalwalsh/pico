from setuptools import setup

version = '2.0.4'

setup(
    name='pico',
    version=version,
    description='Pico HTTP API Framework',
    author='Fergal Walsh',
    url='http://github.com/fergalwalsh/pico',
    download_url='https://github.com/fergalwalsh/pico/tarball/%s' % version,
    packages=['pico', 'pico.extras'],
    test_suite='nose2.collector.collector',
    install_requires=['wrapt >= 1.8.0', 'Werkzeug >= 0.12.1', 'requests >= 2.9.1'],
    include_package_data=True,
    classifiers=(
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    )
)
