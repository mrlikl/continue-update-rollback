# cfn-cur

A tool to generate AWS CLI command to continue-update-rollback a stack that is stuck in UPDATE_ROLLBACK_FAILED state. The resources to skip are essentially identified using a set of [DescribeStackResources](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStackResources.html), [DescribeStacks](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStacks.html) and [DescribeStackEvents](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStackEvents.html) API Calls. 

Works for stacks with nested stacks. Always pass the root stack ARN and the root stack must be in `UPDATE_ROLLBACK_FAILED` state. If your root stack is in a different state [ i.e, the nested stack was updated directly ], the stack is ideally in a stuck situation and would need AWS intervention to recover.

Required parameters -

`--stack_arn` or `-s` - The full arn of the root stack that is stuck in UPDATE_ROLLBACK_FAILED state

Installation -

```
git clone https://github.com/mrlikl/continue-update-rollback.git
cd continue-update-rollback
pip3 install -r requirements.txt
pip3 install -e .
```

Usage -

```
cfn-cur -s <stack-full-arn>
```

or

```
cfn-cur --stack_arn <stack-full-arn>
```
