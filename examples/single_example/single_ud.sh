#!/bin/bash

set -x

echo "$(cat /root/.ssh/authorized_keys | sed 's/^.*ssh-rsa/ssh-rsa/')" > /root/.ssh/authorized_keys

yum update -y
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user
chkconfig docker on