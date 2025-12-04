#!/bin/bash
set -uxo pipefail
cd /testbed
: '>>>>> Start Test Output'
npm test
: '>>>>> End Test Output'
