#!/bin/bash
source "../helper.sh"
check_build && check_no_work && check_run "./build/hello"
