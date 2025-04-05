# cfn-cur

A tool to generate AWS CLI command to continue-update-rollback a stack that is stuck in UPDATE_ROLLBACK_FAILED state. The resources to skip are essentially identified using a set of [DescribeStackResources](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStackResources.html), [DescribeStacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStacks.html) and [DescribeStackEvents](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStackEvents.html) API Calls. 

Works for stacks with nested stacks. Always pass the root stack ARN and the root stack must be in `UPDATE_ROLLBACK_FAILED` state. If your root stack is in a different state [ i.e, the nested stack was updated directly ], the stack is ideally in a stuck situation and would need AWS intervention to recover.

## Features

- Automatically identifies resources that need to be skipped during continue-update-rollback
- Works with nested stacks
- Generates ready-to-use AWS CLI commands
- Handles complex stack hierarchies

## Installation

### From PyPI (Recommended)

```bash
pip install cfn-cur
```

### From Source

```bash
git clone https://github.com/mrlikl/continue-update-rollback.git
cd continue-update-rollback
pip install -e .
```

## Usage

```bash
cfn-cur -s <stack-full-arn>
```

or

```bash
cfn-cur --stack_arn <stack-full-arn>
```

### Required Parameters

`--stack_arn` or `-s` - The full ARN of the root stack that is stuck in UPDATE_ROLLBACK_FAILED state

## How It Works

The tool analyzes the CloudFormation stack events to identify resources that failed during the update process. It then generates an AWS CLI command with the appropriate `--resources-to-skip` parameter to help you successfully roll back your stack.

## Requirements

- Python 3.9 or higher
- AWS credentials configured (via environment variables, AWS profile, or IAM role)
- Boto3

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
