import botocore.session
import typer
from typing import List, Dict, Set, Tuple, Optional
from importlib.metadata import version


def version_callback(value: bool):
    if value:
        try:
            pkg_version = version("cfn-cur")
        except Exception:
            pkg_version = "unknown"
        print(f"cfn-cur {pkg_version}")
        raise typer.Exit()


class StackAnalyzer:
    """Analyzes CloudFormation stacks to identify resources that need to be skipped during continue-update-rollback."""

    def __init__(self, cfn_client):
        self.cfn = cfn_client
        self.cancelled_status = 'Resource update cancelled'
        self.reset_state()

    def reset_state(self):
        """Reset all analysis state for fresh analysis."""
        self.failed_nested_stacks = []
        self.failed_resources = []
        self.skippable_resources = set()  # Use set for O(1) lookups
        self.skippable_nested_stacks = []
        self.update_failed_nested_stacks = []
        self.update_failed_nested_stacks_name = []
        self.nested_stack_arn_map = {}

    def describe_stack_status(self, stack_arn: str) -> Optional[Dict]:
        """Get stack status, return None on error."""
        try:
            response = self.cfn.describe_stacks(StackName=stack_arn)
            return response['Stacks'][0]
        except Exception as e:
            typer.echo(typer.style(
                f"Error describing stack: {e}", fg=typer.colors.RED))
            return None

    def describe_stack_resources(self, stack_arn: str) -> Optional[List[Dict]]:
        """Get stack resources, return None on error."""
        try:
            response = self.cfn.describe_stack_resources(StackName=stack_arn)
            return response['StackResources']
        except Exception as e:
            typer.echo(typer.style(
                f"Error describing stack resources: {e}", fg=typer.colors.RED))
            return None

    def get_stack_events(self, stack_arn: str) -> Optional[List[Dict]]:
        """Get stack events, return None on error."""
        try:
            response = self.cfn.describe_stack_events(StackName=stack_arn)
            return response['StackEvents']
        except Exception as e:
            typer.echo(typer.style(
                f"Error getting stack events: {e}", fg=typer.colors.RED))
            return None

    def pre_checks(self, root_stack_summary: Dict) -> bool:
        """Validate that this is a root stack in UPDATE_ROLLBACK_FAILED state."""
        if "ParentId" in root_stack_summary or "RootId" in root_stack_summary:
            typer.echo(typer.style("Error: Not a root stack. Pass the root stack ARN",
                                   fg=typer.colors.RED, bold=True))
            return False

        if root_stack_summary['StackStatus'] != 'UPDATE_ROLLBACK_FAILED':
            typer.echo(typer.style("Error: Stack is not in UPDATE_ROLLBACK_FAILED state",
                                   fg=typer.colors.RED, bold=True))
            return False
        return True

    def _extract_failed_resources_from_events(self, events: List[Dict], is_root_stack: bool) -> Tuple[List[str], List[str]]:
        """Extract failed resources and nested stacks from events."""
        if not events or len(events) < 2:
            return [], []

        # Find events between UPDATE_ROLLBACK_FAILED and UPDATE_ROLLBACK_IN_PROGRESS
        start_event = "UPDATE_ROLLBACK_FAILED"
        end_event = "UPDATE_ROLLBACK_IN_PROGRESS"

        if events[0]['ResourceStatus'] != start_event or events[1]['ResourceStatus'] == end_event:
            return [], []

        # Extract events between start and end
        relevant_events = []
        for i in range(1, len(events)):
            if events[i]['ResourceStatus'] == end_event:
                break
            relevant_events.append(events[i])

        # Separate and process events
        failed_resources = []
        failed_nested_stacks = []

        for event in relevant_events:
            if event['ResourceStatus'] != 'UPDATE_FAILED' or event['ResourceStatusReason'] == self.cancelled_status:
                continue

            if event['ResourceType'] == 'AWS::CloudFormation::Stack':
                failed_nested_stacks.append(event['PhysicalResourceId'])
            else:
                if is_root_stack:
                    failed_resources.append(event['LogicalResourceId'])
                else:
                    failed_resources.append(
                        f"{event['StackName']}.{event['LogicalResourceId']}")

        return failed_resources, failed_nested_stacks

    def analyze_stack(self, root_stack_arn: str) -> List[str]:
        """Analyze stack to identify resources that need to be skipped."""
        self.reset_state()

        # Get initial failed resources from stack resources
        resources = self.describe_stack_resources(root_stack_arn)
        if not resources:
            return []

        # Separate regular resources from nested stacks
        for resource in resources:
            if resource['ResourceStatus'] == 'UPDATE_FAILED':
                if resource['ResourceType'] == 'AWS::CloudFormation::Stack':
                    self.failed_nested_stacks.append(resource)
                else:
                    self.failed_resources.append(resource['LogicalResourceId'])

        # Analyze root stack events
        root_events = self.get_stack_events(root_stack_arn)
        if root_events:
            event_resources, event_nested_stacks = self._extract_failed_resources_from_events(
                root_events, is_root_stack=True)
            self.skippable_resources.update(event_resources)
            self.update_failed_nested_stacks.extend(event_nested_stacks)

        # Process nested stacks
        nested_skippable_statuses = {
            "DELETE_COMPLETE", "DELETE_IN_PROGRESS", "DELETE_FAILED"}

        while self.failed_nested_stacks:
            nested_stack = self.failed_nested_stacks.pop(0)
            nested_summary = self.describe_stack_status(
                nested_stack['PhysicalResourceId'])

            if not nested_summary:
                continue

            # Map nested stack for naming
            stack_key = nested_stack['PhysicalResourceId']
            if nested_stack['StackId'] == root_stack_arn:
                self.nested_stack_arn_map[stack_key] = nested_stack['LogicalResourceId']
            else:
                self.nested_stack_arn_map[stack_key] = f"{nested_stack['StackName']}.{nested_stack['LogicalResourceId']}"

            if nested_summary['StackStatus'] in nested_skippable_statuses:
                self.skippable_nested_stacks.append(stack_key)
            else:
                # Analyze nested stack events
                nested_events = self.get_stack_events(stack_key)
                if nested_events:
                    event_resources, event_nested_stacks = self._extract_failed_resources_from_events(
                        nested_events, is_root_stack=False)
                    self.skippable_resources.update(event_resources)
                    self.update_failed_nested_stacks.extend(
                        event_nested_stacks)

                # Check nested stack resources
                nested_resources = self.describe_stack_resources(stack_key)
                if nested_resources:
                    for resource in nested_resources:
                        if (resource['ResourceStatus'] == 'UPDATE_FAILED' and
                                not resource['ResourceStatusReason'].startswith(self.cancelled_status)):
                            if resource['ResourceType'] == 'AWS::CloudFormation::Stack':
                                self.failed_nested_stacks.append(resource)
                            else:
                                self.failed_resources.append(
                                    f"{resource['StackName']}.{resource['LogicalResourceId']}")

        # Combine all resources to skip
        resources_to_skip = [
            r for r in self.failed_resources if r in self.skippable_resources]

        # Add nested stack names
        nested_stack_names = [
            self.nested_stack_arn_map[arn] for arn in self.update_failed_nested_stacks
            if arn in self.nested_stack_arn_map
        ]

        return resources_to_skip + nested_stack_names


def generate_cli_command(stack_name: str, resources_to_skip: List[str]) -> str:
    """Generate the AWS CLI command string."""
    base_command = f"aws cloudformation continue-update-rollback --stack-name {stack_name}"
    if resources_to_skip:
        return f"{base_command} --resources-to-skip {' '.join(resources_to_skip)}"
    return base_command


def main(
    root_stack_arn: Optional[str] = typer.Argument(
        None, help="Full Stack ARN of stack which is in UPDATE_ROLLBACK_FAILED"),
    version: bool = typer.Option(
        False, "--version", callback=version_callback, help="Show version information and exit")
):
    """Generate AWS CLI command to continue update rollback of CloudFormation stacks"""

    if not root_stack_arn:
        typer.echo(typer.style(
            "Error: Missing argument 'ROOT_STACK_ARN'", fg=typer.colors.RED))
        typer.echo("Try 'cfn-cur --help' for help.")
        return

    # Initialize
    session = botocore.session.get_session()
    cfn = session.create_client('cloudformation')
    analyzer = StackAnalyzer(cfn)

    # Validate stack
    root_stack_summary = analyzer.describe_stack_status(root_stack_arn)
    if not root_stack_summary or not analyzer.pre_checks(root_stack_summary):
        return

    # Generate CLI command
    resources_to_skip = analyzer.analyze_stack(root_stack_arn)
    cli_command = generate_cli_command(
        root_stack_summary['StackName'], resources_to_skip)

    if not resources_to_skip:
        typer.echo(typer.style("No update failed resources",
                   fg=typer.colors.YELLOW, bold=True))

    typer.echo(typer.style(cli_command, fg=typer.colors.GREEN, bold=True))

def cli():
    typer.run(main)


if __name__ == "__main__":
    cli()
