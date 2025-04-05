"""
This setup.py file is maintained for backwards compatibility.
For modern Python packaging, we use pyproject.toml.
"""

from setuptools import setup, find_packages

# This setup.py is kept for compatibility with older pip versions
# Most of the configuration is in pyproject.toml

setup(
    name='cfn-cur',
    version='0.1.3',
    description='A tool to generate CLI Command to continue update rollback of CloudFormation stacks',
    author='S Murali Krishnan',
    author_email="mrlikrsh@gmail.com",
    url="https://github.com/mrlikl/continue-update-rollback",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'cfn-cur = continue_update_rollback.app:main'
        ]
    },
    install_requires=[
        'boto3',
    ],
    python_requires='>=3.9',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)