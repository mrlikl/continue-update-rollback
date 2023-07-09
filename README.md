# continue-update-rollback

Generate CLI command to continue-update-rollback a stack that is stuck in UPDATE_ROLLBACK_FAILED state

Required parameters -

`--stack_arn` or `-s` - The full arn of the stack that is stuck in UPDATE_ROLLBACK_FAILED state

Pre-requisites -

```
pip3 install -r requirements.txt
```

Usage -

1. Clone the repo -

```
git clone https://github.com/mrlikl/continue-update-rollback.git
```

2. Open the folder in a terminal

```
cd continue-update-rollback
```

3. Exceute the file be passing the stack arn -

```
python3 app.py -s <stack-full-arn>
```

or

```
python3 app.py --stack_arn <stack-full-arn>
```
