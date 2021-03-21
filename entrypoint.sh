#!/bin/bash --login
set -e

conda activate photo_gallery
exec "$@"