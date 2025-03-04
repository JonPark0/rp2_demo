# boot.py - runs on boot-up
import os
import gc
import machine

# Perform memory cleanup
gc.collect()
