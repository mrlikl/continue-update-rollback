from setuptools import setup, find_packages

setup(
    name='continue_update_rollback',
    version='0.1',
    description='A tool to generate CLI Command for continue update rollback of CloudFormation stacks',
    author='Murali Krishnan',
    python_requires='>=3.9',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'cfn-cur = continue_update_rollback.app:main'
        ]
    }
)
