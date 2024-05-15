import subprocess
cfn_command = subprocess.run(['cfn-cur', '-s', 'arn:aws:cloudformation:us-east-1:072179961767:stack/testcase1/6cf33240-12b6-11ef-a33a-0e8d2fdecbdb'], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
print(cfn_command.stderr)
print(cfn_command.returncode)
print(cfn_command.stdout)
if cfn_command.returncode == 0:
    print("Got CLI Command")
    print("executing")
    print(cfn_command.stdout.strip())
    result = subprocess.run(cfn_command.stdout.strip().split(), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    print(result.returncode)
