#!/bin/bash
set -uxo pipefail
cd /testbed
: '>>>>> Start Test Output'
NODE_OPTIONS='--max-old-space-size=8192' pnpm test
: '>>>>> End Test Output'
