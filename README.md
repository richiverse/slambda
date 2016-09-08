# slambda
Exploring Slack integration apps with AWS Lambda

Since AWS requires python 2.7, I used yyuu's pyenv to install local version of python 2.7.12

```bash
pyenv install 2.7.12
```

and then running

```bash
pyenv local 2.7.12
```

This sets the python interpreter to 2.7.12 for this project only.

Let's now upgrade pip and install virtualenv

```bash
pip install -U pip
pip install virtualenv
```

Read the instructions at http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-set-up.html#cli-signup to help with the next step

Assuming you have your credentials, run:

```bash
aws configure
```

For now, we can practice with the cardbot example, found here: http://pertinentserpent.tumblr.com/post/147568685382/deploying-a-slack-bot-on-amazon-lambda-with

```bash
chalice new-project cardbot && cd cardbot
chalice deploy
```

After a number of trial and error deploys, I was able to find the minimum set of policies for deploy. Make sure to add this policy to your account.
I saved the json of the policy in chalice_policies.json. You will need to apply this policy to the user you configured previously.

For my deploy, I used .env files to store secrets locally and used them in deploy.sh. I ran this instead of chalice deploy where I wanted to store secrets.

A better way would be to use AWS KMS.
