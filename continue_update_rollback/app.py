import boto3
import argparse
import sys


failed_nested_stacks = []
failed_resources = []
skippable_resources = []
skippable_nested_stacks = []
update_failed_nested_stacks = []
update_failed_nested_stacks_name = []
nested_stack_arn_map = {}
cancelled_status = 'Resource update cancelled'


def get_stack_events(stack_arn, cfn):
    """
    Retrieve stack events for a given stack ARN.
    
    Args:
        stack_arn (str): The ARN of the CloudFormation stack
        cfn: The boto3 CloudFormation client
        
    Returns:
        list: Stack events
    """
    response = cfn.describe_stack_events(
        StackName=stack_arn
    )
    return response['StackEvents']


def parse_stack_events(stack_events, is_root_stack, cfn):
    """
    Parse stack events to identify failed resources.
    
    Args:
        stack_events (list): List of stack events
        is_root_stack (bool): Whether this is the root stack
        cfn: The boto3 CloudFormation client
    """
    global skippable_resources
    global update_failed_nested_stacks
    start_event = "UPDATE_ROLLBACK_FAILED"
    end_event = "UPDATE_ROLLBACK_IN_PROGRESS"
    events_in = []
    if stack_events[0]['ResourceStatus'] == start_event and stack_events[1]['ResourceStatus'] != end_event:
        running = True
        n = 1
        while running:
            if stack_events[n]['ResourceStatus'] != end_event:
                events_in.append(stack_events[n])
            if stack_events[n]['ResourceStatus'] == end_event:
                running = False
            n += 1

        if is_root_stack:
            resource_events = [x
                               for x in events_in if x['ResourceType'] != 'AWS::CloudFormation::Stack']
            nested_stack_events = [x
                                   for x in events_in if x['ResourceType'] == 'AWS::CloudFormation::Stack']
            skippable_resources.extend([x['LogicalResourceId']
                                        for x in resource_events if x['ResourceStatus'] == 'UPDATE_FAILED' and
                                        x['ResourceStatusReason'] != cancelled_status])
            update_failed_nested_stacks.extend([x['PhysicalResourceId']
                                               for x in nested_stack_events if x['ResourceStatus'] == 'UPDATE_FAILED' and
                                               x['ResourceStatusReason'] != cancelled_status])
        else:
            resource_events = [x
                               for x in events_in if x['ResourceType'] != 'AWS::CloudFormation::Stack']
            nested_stack_events = [x
                                   for x in events_in if x['ResourceType'] == 'AWS::CloudFormation::Stack']
            skippable_resources.extend([x['StackName']+"."+x['LogicalResourceId']
                                       for x in resource_events if x['ResourceStatus'] == 'UPDATE_FAILED' and
                                       x['ResourceStatusReason'] != cancelled_status])
            update_failed_nested_stacks.extend([x['PhysicalResourceId']
                                               for x in nested_stack_events if x['ResourceStatus'] == 'UPDATE_FAILED' and
                                               x['ResourceStatusReason'] != cancelled_status])


def check_resource_status(status):
    """
    Check if resource status is not cancelled.
    
    Args:
        status (str): Resource status reason
        
    Returns:
        bool: True if status is not cancelled
    """
    return not status.startswith(cancelled_status)


def find_failed_resources(summary):
    """
    Find resources with UPDATE_FAILED status.
    
    Args:
        summary (list): List of resources
        
    Returns:
        list: Failed resources
    """
    return [i for i in summary if i['ResourceStatus'] == 'UPDATE_FAILED']


def find_failed_resources_in_nested_stacks(stack_arn, cfn):
    """
    Find failed resources in nested stacks.
    
    Args:
        stack_arn (str): The ARN of the CloudFormation stack
        cfn: The boto3 CloudFormation client
        
    Returns:
        list: Failed resources
    """
    global failed_nested_stacks
    resources = []
    summary = describe_stack_resources(stack_arn, cfn)
    for i in summary:
        if i['ResourceStatus'] == 'UPDATE_FAILED':
            if i['ResourceType'] == 'AWS::CloudFormation::Stack':
                failed_nested_stacks.append(i)
            else:
                if check_resource_status(i['ResourceStatusReason']):
                    resources.append(i['StackName']+"."+i['LogicalResourceId'])
    return resources


def describe_stack_status(stack_arn, cfn):
    """
    Describe the status of a stack.
    
    Args:
        stack_arn (str): The ARN of the CloudFormation stack
        cfn: The boto3 CloudFormation client
        
    Returns:
        dict: Stack details or -1 if error
    """
    response = cfn.describe_stacks(
        StackName=stack_arn,
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return response['Stacks'][0]
    else:
        print(response['ResponseMetadata'])
        return -1


def describe_stack_resources(stack_arn, cfn):
    """
    Describe resources in a stack.
    
    Args:
        stack_arn (str): The ARN of the CloudFormation stack
        cfn: The boto3 CloudFormation client
        
    Returns:
        list: Stack resources or -1 if error
    """
    response = cfn.describe_stack_resources(
        StackName=stack_arn,
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return response['StackResources']
    else:
        print(response['ResponseMetadata'])
        return -1


def pre_checks(root_stack_summary):
    """
    Perform pre-checks on the stack.
    
    Args:
        root_stack_summary (dict): Stack summary
        
    Returns:
        bool: True if checks pass
    """
    if "ParentId" in root_stack_summary or "RootId" in root_stack_summary:
        print("Pass the root stack arn")
        return False
    if root_stack_summary['StackStatus'] != 'UPDATE_ROLLBACK_FAILED':
        print("cannot continue update rollback on stack that is not in UPDATE_ROLLBACK_FAILED state")
        return False
    return True


def main():
    """
    Main function to generate continue-update-rollback command.
    """
    parser = argparse.ArgumentParser(
        description='Generate AWS CLI command to continue update rollback of CloudFormation stacks'
    )
    parser.add_argument('-s',
                        '--stack_arn', required=True,
                        metavar='[Full Stack ARN]',
                        help='Specify the full stack ARN of stack which is in UPDATE_ROLLBACK_FAILED')
    
    # Add version argument
    parser.add_argument('-v', '--version', action='store_true',
                        help='Show version information and exit')
    
    args = parser.parse_args()
    
    # Handle version display
    if args.version:
        from continue_update_rollback import __version__
        print(f"cfn-cur version {__version__}")
        sys.exit(0)
    
    root_stack = args.stack_arn
    
    # Initialize boto3 client
    cfn = boto3.client('cloudformation')
    
    root_stack_summary = describe_stack_status(root_stack, cfn)
    global failed_nested_stacks
    global failed_resources
    global skippable_resources
    global skippable_nested_stacks
    global update_failed_nested_stacks
    global update_failed_nested_stacks_name
    global nested_stack_arn_map
    nested_skippable_statuses = ["DELETE_COMPLETE",
                             "DELETE_IN_PROGRESS", "DELETE_FAILED"]
    if pre_checks(root_stack_summary):
        resources = describe_stack_resources(root_stack, cfn)
        failed_resources += find_failed_resources(resources)

        for i in failed_resources:
            if i['ResourceType'] == 'AWS::CloudFormation::Stack':
                failed_nested_stacks.append(i)

        failed_resources = [
            x for x in failed_resources if x not in failed_nested_stacks]

        failed_resources = [
            x['LogicalResourceId'] for x in failed_resources]

        root_events = get_stack_events(root_stack, cfn)

        parse_stack_events(root_events, is_root_stack=True, cfn=cfn)

        while failed_nested_stacks:
            popped_stack = failed_nested_stacks.pop(0)
            nested_stack_summary = describe_stack_status(
                popped_stack['PhysicalResourceId'], cfn)
            if nested_stack_summary['StackStatus'] in nested_skippable_statuses:
                if popped_stack['StackId'] == root_stack:
                    nested_stack_arn_map[popped_stack['PhysicalResourceId']
                                        ] = popped_stack['LogicalResourceId']
                else:
                    nested_stack_arn_map[popped_stack['PhysicalResourceId']
                                        ] = popped_stack['StackName'] + "."+popped_stack['LogicalResourceId']
                skippable_nested_stacks.append(popped_stack['PhysicalResourceId'])
            else:
                nested_events = get_stack_events(
                    popped_stack['PhysicalResourceId'], cfn)
                parse_stack_events(nested_events, is_root_stack=False, cfn=cfn)
                failed_resources += find_failed_resources_in_nested_stacks(
                    popped_stack['PhysicalResourceId'], cfn)

        failed_resources = [
            value for value in failed_resources if value in skippable_resources]

        update_failed_nested_stacks_name.extend(
            nested_stack_arn_map[key] for key in update_failed_nested_stacks if key in nested_stack_arn_map
        )

        failed_resources.extend(x for x in update_failed_nested_stacks_name)

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


if __name__ == "__main__":
    main()