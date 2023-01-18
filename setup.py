from setuptools import setup, find_packages

setup(
    name='aeries-importer',
    version='0.1.0',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'aeries-importer=main:run_aeries_importer'
        ],
    },
)