#!/bin/bash

coverage run -m pytest --durations=10

coverage report -m