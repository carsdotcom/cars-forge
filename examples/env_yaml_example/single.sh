#!/bin/bash
echo "$(cat /root/.ssh/authorized_keys | sed 's/^.*ssh-rsa/ssh-rsa/')" > /root/.ssh/authorized_keys