#!/bin/sh

env >> /etc/environment

# execute CMD
exec "$@"