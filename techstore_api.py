import json
import os
import datetime
import re
import requests
import pymysql
import pandas as pd
from typing import List, Dict, Any, Optional, Union

# Cấu hình kết nối
def load_config():
    """Tải cấu hình từ file config.json"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(