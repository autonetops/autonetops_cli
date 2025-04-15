from setuptools import setup, find_packages

setup(
    name='autonetops',
    version='0.1.5',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click==8.1.7',
        'PyYAML==6.0.2',
        'netmiko==4.4.0',
    ],
    entry_points='''
        [console_scripts]
        autonetops=autonetops.autonetops:cli
    ''',
)
