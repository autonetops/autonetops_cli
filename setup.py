from setuptools import setup, find_packages

setup(
    name='autonetops',
    version='0.1.13',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click>=8.1.7',
        'PyYAML>=6.0',
        'scrapli[asyncssh]>=2024.1.30',
        'rich>=13.4.0',
    ],
    entry_points={
        'console_scripts': [
            'autonetops=autonetops.autonetops:cli',
        ],
    },
    author='Pedro C Damasceno',
    description='Autonetops CLI for labs and exercises',
    url='https://github.com/autonetops/autonetops_cli',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
