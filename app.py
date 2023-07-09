import boto3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-s',
                    '--stack_arn', required=True,
                    help='Specify the full stack arn of stack which is in UPDATE_ROLLBACK_FAILED')

cfn = boto3.client('cloudformation')

args = parser.parse_args()

failed_nested_stacks = []
failed_resources = []
cancelled_status = 'Resource update cancelled'


def check_resource_status(status):
    return not status.startswith(cancelled_status)


def find_failed_resources(summary):
    return [i for i in summary if i['ResourceStatus'] == 'UPDATE_FAILED']


def find_failed_resources_in_nested_stacks(stack_arn):
    global failed_nested_stacks
    resources = []
    summary = describe_stack_resources(stack_arn)
    for i in summary:
        if i['ResourceStatus'] == 'UPDATE_FAILED':
            if i['ResourceType'] == 'AWS::CloudFormation::Stack':
                failed_nested_stacks.append(i)
            else:
                if check_resource_status(i['ResourceStatusReason']):
                    resources.append(i['StackName']+"."+i['LogicalResourceId'])
    return resources


def describe_stack_status(stack_arn):
    response = cfn.describe_stacks(
        StackName=stack_arn,
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return response['Stacks'][0]
    else:
        print(response['ResponseMetadata'])
        return -1


def describe_stack_resources(stack_arn):
    response = cfn.describe_stack_resources(
        StackName=stack_arn,
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return response['StackResources']
    else:
        print(response['ResponseMetadata'])
        return -1


root_stack = name = args.stack_arn

root_stack_summary = describe_stack_status(root_stack)

if root_stack_summary['StackStatus'] != 'UPDATE_ROLLBACK_FAILED':
    print("cannot continue update rollback on stack that is not in UPDATE_ROLLBACK_FAILED state")
else:
    resources = describe_stack_resources(root_stack)
    failed_resources += find_failed_resources(resources)

    for i in failed_resources:
        if i['ResourceType'] == 'AWS::CloudFormation::Stack':
            failed_nested_stacks.append(i)

    failed_resources = [
        x for x in failed_resources if x not in failed_nested_stacks]

    failed_resources = [
        x['LogicalResourceId'] for x in failed_resources]

    while failed_nested_stacks:
        popped_stack = failed_nested_stacks.pop(0)
        failed_resources += find_failed_resources_in_nested_stacks(
            popped_stack['PhysicalResourceId'])

    if not failed_resources:
        print("No update failed resources")
        cli_command = "aws cloudformation continue-update-rollback --stack-name " + \
            root_stack_summary['StackName']
        print(cli_command)
    else:
        cli_command = "aws cloudformation continue-update-rollback --stack-name " + \
            root_stack_summary['StackName']
        cli_command += " --resources-to-skip "
        cli_command += ' '.join(failed_resources)
        print(cli_command)
