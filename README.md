# aws-serverless-web-chat
A scalable, cheap, easy-to-deploy web chat platform.

Still in development.

## How to use

Make sure you have Python 2.7 and [pip installed](https://pip.pypa.io/en/stable/installing/).

```
# Ensure your AWS credentials are set. Use the AWS CLI docs for example setup.
# http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html

# Install boa-nimbus.
pip install git+git://github.com/moduspwnens/boa-nimbus.git

# Clone this repo.
git clone https://github.com/moduspwnens/aws-serverless-web-chat.git

# Change working directory to repository root.
cd aws-serverless-web-chat

# Package and upload Lambda function.
boa-nimbus deploy --stack-name webchat-lambda-src
```

After the command completes successfully: 

 * Go to [CloudFormation in the AWS web console](https://console.aws.amazon.com/cloudformation/home).
 * Click the **Create Stack** button and choose to upload the **serverless-web-api-html.yaml** template from this directory.
 * Click through the wizard to launch the stack. Adjust any settings you'd like.

Wait until this final stack reaches the **CREATE_COMPLETE** status, select it and click the **Outputs** tab. There should be one called **StaticContentBucket**. That's the bucket that needs the static web content.

For the static content, we just need to fetch the dependencies and upload the resulting files to the S3 bucket.

```
# Download and install node.js (if it's not installed already).
# https://nodejs.org/en/download/

# Change working directory to web-static under repository root.
cd web-static

# Install deployment tools.
sudo npm install -g grunt grunt-cli gulp bower

# Get all dependencies.
npm install

# Build all third party packages and put them in the lib directory.
gulp install

# Upload resources to S3 bucket.
aws s3 sync www/ s3://s3-bucket-name
```

Be sure to replace **s3-bucket-name** with the name of the bucket from the outputs.

...and now you should be good to go. Go to [CloudFormation in the AWS web console](https://console.aws.amazon.com/cloudformation/home), select the stack, then click the "Outputs" tab. There should be one called **WebChatApiHome**. Click the link to open the home page to your very own serverless web chat interface.